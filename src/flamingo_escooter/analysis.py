import geopandas as gpd


def od_flows(
    trips_gdf: gpd.GeoDataFrame,
    zones_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Aggregate trips into an origin-destination matrix by spatial zone.

    Performs two spatial joins: first matching each trip's end point to a
    destination zone, then its start point to an origin zone. Trips that
    fall outside any zone boundary are dropped (inner join).

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Trip records from load_trips(), must have start_point and end_point
        columns in EPSG:2193.
    zones_gdf : GeoDataFrame
        Spatial zones (e.g. SA1 or SA2 boundaries) in EPSG:2193. The zone
        name column is inferred from column index 1.

    Returns
    -------
    GeoDataFrame
        trips_gdf with two additional columns:
        - origin: name of the zone containing the trip's start point
        - destination: name of the zone containing the trip's end point
    """
    gdf = trips_gdf.copy()
    column_name = zones_gdf.columns[1] 

    gdf.set_geometry('end_point', crs="EPSG:2193",inplace=True)
    gdf = gpd.sjoin(
        gdf,
        zones_gdf[[column_name, 'geometry']], 
        how='inner', 
        predicate='within'
    )
    gdf.rename(columns={column_name: 'destination'}, inplace=True)
    gdf.drop(columns=['index_right'], inplace=True)
    gdf.set_geometry('start_point', crs="EPSG:2193", inplace=True)

    gdf = gpd.sjoin(
        gdf, 
        zones_gdf[[column_name, 'geometry']], 
        how='inner', 
        predicate='within'
    )
    gdf.rename(columns={column_name: 'origin'}, inplace=True)
    gdf.drop(columns=['index_right'], inplace=True)

    return gdf

def geofence_violations(
    trips_gdf: gpd.GeoDataFrame,
    no_park_gdf: gpd.GeoDataFrame,
    location_type: str = "end",
) -> gpd.GeoDataFrame:
    """
    Flag trips that start or end inside a no-parking geofence zone.

    Adds two columns to trips_gdf in place:
    - is_violation : True if the trip endpoint falls inside a no-parking zone
    - violated_area: zone name if is_violation, else None

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Trip records from load_trips(), must have start_point and end_point
        columns in EPSG:2193.
    no_park_gdf : GeoDataFrame
        Geofence zones from load_geofence(). Must have a 'name' column
        and a 'ride_end_allowed' column.
    location_type : str, optional
        Which trip endpoint to check — 'end' (default) or 'start'.

    Returns
    -------
    GeoDataFrame
        trips_gdf with two additional columns:
        - is_violation : bool
        - violated_area: str or None
    """
    if location_type not in ("start", "end"):
        raise ValueError("location_type must be 'start' or 'end'")

    point_col = f"{location_type}_point"

    if point_col not in trips_gdf.columns:
        raise ValueError(f"{point_col} not found in trips_gdf columns")

    gdf = trips_gdf.copy().set_geometry(point_col, crs="EPSG:2193")
    no_park = no_park_gdf[no_park_gdf["ride_end_allowed"] == "False"].to_crs("EPSG:2193")

    joined = gpd.sjoin(
        gdf,
        no_park[["name", "geometry"]],
        how="left",
        predicate="within",
    )

    # keep first match per trip in case a point falls inside multiple zones
    joined = joined[~joined.index.duplicated(keep="first")]

    trips_gdf = trips_gdf.copy()
    trips_gdf["is_violation"] = joined["name"].notna()
    trips_gdf["violated_area"] = joined["name"].where(joined["name"].notna(), None)

    return trips_gdf


def violations_table_wide(
    trips_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Pivot violation records into a wide-format summary table.

    Aggregates trip-level violations into a zone-level summary with one row
    per violated zone and columns for total violations, unique trips, and
    share of all violations.

    Parameters
    ----------
    violations_gdf : GeoDataFrame
        Output of geofence_violations(), must have a 'area' column.

    Returns
    -------
    DataFrame
        Wide-format summary with columns:
        - area: name of the no-parking zone
        - total_violations: number of trips ending in that zone
    """
    return (
        trips_gdf[trips_gdf["is_violation"]]
        .groupby("violated_area")
        .size()
        .reset_index(name="total_violations")
        .sort_values("total_violations", ascending=False)
        .reset_index(drop=True)
    )

def transit_proximity(
    trips_gdf: gpd.GeoDataFrame,
    transit_gdf: gpd.GeoDataFrame,
    distance: int = 10,
) -> gpd.GeoDataFrame:
    """
    Identify scooter trips that start or end near public transport stops.

    For each trip, finds the nearest transit stop and flags whether it falls
    within the supplied distance threshold. Prints a summary of the share of
    trips starting and ending near transit.

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Trip records from load_trips(), must have start_point and end_point
        columns in EPSG:2193.
    transit_gdf : GeoDataFrame
        Transit stop locations from load_transit_stations(), in EPSG:2193.
    distance : int, optional
        Proximity threshold in metres. Defaults to 10.

    Returns
    -------
    GeoDataFrame
        trips_gdf with four additional columns:
        - start_distance_to_transit_m: distance from trip origin to nearest stop
        - end_distance_to_transit_m: distance from trip destination to nearest stop
        - start_near_transit: True if origin is within distance threshold
        - end_near_transit: True if destination is within distance threshold
    """
    trips_gdf = trips_gdf.to_crs(2193).reset_index(drop=True)
    transit_gdf = transit_gdf.to_crs(2193).reset_index(drop=True)

    trips = trips_gdf.copy()
    trips["trip_index"] = trips.index

    def nearest_distance(point_col, distance_col):
        nearest = gpd.sjoin_nearest(
            trips.set_geometry(point_col),
            transit_gdf,
            how="left",
            distance_col=distance_col,
        )
        nearest = (
            nearest
            .drop_duplicates(subset="trip_index", keep="first")
            .sort_values("trip_index")
            .set_index("trip_index")
        )
        return nearest[distance_col]

    trips["start_distance_to_transit_m"] = nearest_distance("start_point", "start_distance_to_transit_m")
    trips["end_distance_to_transit_m"] = nearest_distance("end_point", "end_distance_to_transit_m")
    trips["start_near_transit"] = trips["start_distance_to_transit_m"] <= distance
    trips["end_near_transit"] = trips["end_distance_to_transit_m"] <= distance

    return trips.drop(columns="trip_index")