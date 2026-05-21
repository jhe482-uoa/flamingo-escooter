import folium
from folium.plugins import HeatMap
from polyline import polyline


def path_heatmap(trips):    
    """
    Render a Folium heatmap of trip paths across the Auckland CBD.

    Decodes encoded polylines directly from the encodedPolyline column and
    plots point density as a heatmap layer over a dark CartoDB basemap.
    Hot spots indicate streets with high scooter traffic.

    Parameters
    ----------
    trips : GeoDataFrame
        Trip records from load_trips(), must have an 'encodedPolyline' column.

    Returns
    -------
    folium.Map
        Interactive heatmap centred on Auckland CBD, displayable inline
        in Jupyter via the returned map object.
    """
    points = []
    for encoded in trips['encodedPolyline']:
        if encoded:
            points.extend(polyline.decode(encoded))
    
    m = folium.Map(location=[-36.85, 174.76], zoom_start=14, tiles = "Cartodb dark_matter")
    HeatMap(points, radius=6, blur=8, min_opacity=0.25, gradient={0.2: "#ffb3d9", 0.4: "#ff66b3", 0.6: "#ff3399", 0.8: "#e60073", 1.0: "#fe1f68"}).add_to(m)
    return m

            
def violation_heatmap(violations_gdf, location_type="end"):
    """
    Render a Folium heatmap of geofence violation locations.

    Plots the density of trip endpoints that breached a no-parking zone,
    useful for identifying enforcement hotspots for Auckland Council reporting.

    Parameters
    ----------
    violations_gdf : GeoDataFrame
        Output of geofence_violations(), must have start_point or end_point
        columns in EPSG:2193.
    location_type : str, optional
        Which endpoint to map — 'end' (default) or 'start'.

    Returns
    -------
    folium.Map
        Interactive heatmap centred on Auckland CBD, displayable inline
        in Jupyter via the returned map object.

    Raises
    ------
    ValueError
        If location_type is not 'start' or 'end', or if the corresponding
        point column is missing from violations_gdf.
    """
    if location_type not in ("start", "end"):
        raise ValueError("location_type must be 'start' or 'end'")
    
    point_col = f"{location_type}_point"

    if point_col not in violations_gdf.columns:
        raise ValueError(f"{point_col} not found in violations_gdf columns")



    gdf = (violations_gdf.set_geometry(point_col).to_crs(4326))

    heat_data = [[point.y, point.x] for point in gdf.geometry if point is not None]

    m = folium.Map(location=[-36.85, 174.76],zoom_start=14, tiles = "Cartodb dark_matter")
    HeatMap(heat_data, radius=10, blur=15, min_opacity=0.2, gradient={0.2: "#ffb3d9", 0.4: "#ff66b3", 0.6: "#ff3399", 0.8: "#e60073", 1.0: "#fe1f68"}).add_to(m)
    return m

def transit_heatmap(trips_gdf, location_type="both"):
    """
    Render a Folium heatmap of trips that started or ended near a transit stop.

    Parameters
    ----------
    trips_gdf : GeoDataFrame
        Output of transit_proximity(), must have start_near_transit and
        end_near_transit boolean columns, and start_point/end_point geometry
        columns in EPSG:2193.
    location_type : str, optional
        Which endpoint to map — 'end' (default), 'start', or 'both'.

    Returns
    -------
    folium.Map
        Interactive heatmap centred on Auckland CBD.

    Raises
    ------
    ValueError
        If location_type is not 'start', 'end', or 'both'.
    """
    if location_type not in ("start", "end", "both"):
        raise ValueError("location_type must be 'start', 'end', or 'both'")

    m = folium.Map(location=[-36.85, 174.76], zoom_start=14, tiles="CartoDB dark_matter")

    def add_layer(point_col, flag_col, name):
        gdf = trips_gdf[trips_gdf[flag_col]].copy()
        gdf = gdf.set_geometry(point_col).to_crs(4326)
        points = [[p.y, p.x] for p in gdf.geometry if p is not None]
        HeatMap(points, name=name, radius=10, blur=15, min_opacity=0.2, gradient={0.2: "#ffb3d9", 0.4: "#ff66b3", 0.6: "#ff3399", 0.8: "#e60073", 1.0: "#fe1f68"}).add_to(m)




    if location_type in ("start", "both"):
        add_layer("start_point", "start_near_transit", "Near transit (start)")
    if location_type in ("end", "both"):
        add_layer("end_point", "end_near_transit", "Near transit (end)")

    folium.LayerControl().add_to(m)
    return m


