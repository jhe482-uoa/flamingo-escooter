import geopandas as gpd


def od_flows(trips_gdf, zones_gdf):
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

def geofence_violations(trips_gdf, no_park_gdf, location_type="end"):
    """
    Identify trips that start or end inside a no-parking geofence zone.

    Filters no_park_gdf to zones where ride_end_allowed is False, then
    spatially joins trip points against those polygons. Only trips that
    fall within a prohibited zone are returned.

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Trip records from load_trips(), must have start_point and end_point
        columns in EPSG:2193.
    no_park_gdf : GeoDataFrame
        Geofence zones from geofence_json_to_gdf(). Must have a 'name' column
        and a 'ride_end_allowed' column.
    location_type : str, optional
        Which trip endpoint to check — 'end' (default) or 'start'.

    Returns
    -------
    GeoDataFrame
        Subset of trips_gdf where the relevant endpoint falls inside a
        no-parking zone, with an additional 'area' column giving
        the name of the breached polygon.

    Raises
    ------
    ValueError
        If location_type is not 'start' or 'end', or if the corresponding
        point column is missing from trips_gdf.
    """
    if location_type not in ("start", "end"):
        raise ValueError("location_type must be 'start' or 'end'")
    
    point_col = f"{location_type}_point"

    if point_col not in trips_gdf.columns:
        raise ValueError(f"{point_col} not found in trips_gdf columns")

    gdf = trips_gdf.copy().set_geometry(point_col, crs="EPSG:2193")
    no_park_gdf = no_park_gdf[no_park_gdf['ride_end_allowed'] == "False"].to_crs("EPSG:2193")

    gdf = gpd.sjoin(
        gdf,
        no_park_gdf[["name", "geometry"]],
        how="inner",
        predicate="within",
    )
    gdf.rename(columns={"name": "area"}, inplace=True)
    gdf.drop(columns=["index_right"], inplace=True)
    return gdf


def violations_table_wide(violations_gdf):
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

    return (violations_gdf.groupby("area").size().reset_index(name="total_violations").sort_values("total_violations", ascending=False)).reset_index(drop=True)

def transit_proximity(trips_gdf, transit_gdf, distance=10):
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

    total = len(trips)
    start_pct = trips["start_near_transit"].sum() / total * 100
    end_pct = trips["end_near_transit"].sum() / total * 100
    either_pct = trips[trips["start_near_transit"] | trips["end_near_transit"]].shape[0] / total * 100

    print(f"Transit proximity summary (within {distance}m):")
    print(f"  Started near transit : {trips['start_near_transit'].sum():>4d} / {total}  ({start_pct:.1f}%)")
    print(f"  Ended near transit   : {trips['end_near_transit'].sum():>4d} / {total}  ({end_pct:.1f}%)")
    print(f"  Either end near      : {trips[trips['start_near_transit'] | trips['end_near_transit']].shape[0]:>4d} / {total}  ({either_pct:.1f}%)")

    return trips.drop(columns="trip_index")