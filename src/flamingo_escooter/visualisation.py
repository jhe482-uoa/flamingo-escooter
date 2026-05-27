import folium
from folium.plugins import HeatMap
from polyline import polyline

GRADIENT = {0.2: "#ffb3d9", 0.4: "#ff66b3", 0.6: "#ff3399", 0.8: "#e60073", 1.0: "#fe1f68"}


def path_heatmap(trips):
    """
    Render a Folium heatmap of trip paths across the Auckland CBD.

    Parameters
    ----------
    trips : GeoDataFrame
        Trip records from load_trips() or run(), must have an 'encodedPolyline' column.

    Returns
    -------
    folium.Map
    """
    points = []
    for encoded in trips['encodedPolyline']:
        if encoded:
            points.extend(polyline.decode(encoded))

    m = folium.Map(location=[-36.85, 174.76], zoom_start=14, tiles="CartoDB dark_matter")
    HeatMap(points, radius=6, blur=8, min_opacity=0.25, gradient=GRADIENT).add_to(m)
    return m


def violation_heatmap(trips_gdf, location_type="end"):
    """
    Render a Folium heatmap of geofence violation locations.

    Filters to trips where is_violation is True before plotting.

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Output of geofence_violations() or run(), must have is_violation,
        and start_point/end_point columns in EPSG:2193.
    location_type : str, optional
        Which endpoint to map — 'end' (default) or 'start'.

    Returns
    -------
    folium.Map

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

    if "is_violation" not in trips_gdf.columns:
        raise ValueError("trips_gdf must have an 'is_violation' column — run geofence_violations() first")

    gdf = trips_gdf[trips_gdf["is_violation"]].set_geometry(point_col).to_crs(4326)
    heat_data = [[p.y, p.x] for p in gdf.geometry if p is not None]

    m = folium.Map(location=[-36.85, 174.76], zoom_start=14, tiles="CartoDB dark_matter")
    HeatMap(heat_data, radius=10, blur=15, min_opacity=0.2, gradient=GRADIENT).add_to(m)
    return m


def first_and_last_mile_heatmap(trips_gdf, location_type="both"):
    """
    Render a Folium heatmap of trips that started or ended near a transit stop.

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Output of transit_proximity() or run(), must have start_near_transit,
        end_near_transit, and start_point/end_point columns in EPSG:2193.
    location_type : str, optional
        Which endpoint to map — 'end' (default), 'start', or 'both'.

    Returns
    -------
    folium.Map

    Raises
    ------
    ValueError
        If location_type is not 'start', 'end', or 'both'.
    """
    if location_type not in ("start", "end", "both"):
        raise ValueError("location_type must be 'start', 'end', or 'both'")

    if "start_near_transit" not in trips_gdf.columns:
        raise ValueError("trips_gdf must have start_near_transit column — run transit_proximity() first")

    m = folium.Map(location=[-36.85, 174.76], zoom_start=14, tiles="CartoDB dark_matter")

    def add_layer(point_col, flag_col, name):
        gdf = trips_gdf[trips_gdf[flag_col]].set_geometry(point_col).to_crs(4326)
        points = [[p.y, p.x] for p in gdf.geometry if p is not None]
        HeatMap(points, name=name, radius=10, blur=15, min_opacity=0.2, gradient=GRADIENT).add_to(m)

    if location_type in ("start", "both"):
        add_layer("start_point", "start_near_transit", "Near transit (start)")
    if location_type in ("end", "both"):
        add_layer("end_point", "end_near_transit", "Near transit (end)")

    folium.LayerControl().add_to(m)
    return m