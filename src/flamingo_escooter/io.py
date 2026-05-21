from dotenv import load_dotenv
import pandas as pd
import geopandas as gpd
from shapely import LineString
from polyline import polyline
from importlib import resources
import os
from io import BytesIO
import requests
from pathlib import Path


CACHE_DIR = Path.home() / ".cache" / "flamingo_escooter"
WFS_URL = (
    "https://datafinder.stats.govt.nz/services;"
    "key={key}/wfs"
)
DATA_DIR = Path(__file__).parent / "data"

def load_trips(data_file=None):
    """
    Load Flamingo Auckland CBD trip data from the bundled CSV.

    Parses start/end timestamps, decodes encoded polylines into LineString
    geometries, and reprojects everything to EPSG:2193 (NZTM).

    Returns
    -------
    GeoDataFrame
        One row per trip with columns:
        - geometry (path_line): LineString of the full route in EPSG:2193
        - start_point: Point geometry of trip origin in EPSG:2193
        - end_point: Point geometry of trip destination in EPSG:2193
        - all original CSV columns (tripId, startTime, endTime, distance, etc.)
    """
    if data_file is None:
        df = pd.read_csv(resources.files("flamingo_escooter") / "data" / "flamingo_trip_dataset_sample.csv")
    elif isinstance(data_file, pd.DataFrame):
        df = data_file
    else:
        df = pd.read_csv(data_file)
    df['startTime'] = pd.to_datetime(df['startTime'])
    df['endTime'] = pd.to_datetime(df['endTime'])

    start_point = gpd.points_from_xy(df.startLongitude, df.startLatitude, crs="EPSG:4326").to_crs("EPSG:2193")
    end_point = gpd.points_from_xy(df.endLongitude, df.endLatitude, crs="EPSG:4326").to_crs("EPSG:2193")
    
    def decode_to_line(encoded_str):
        try:
            coords = polyline.decode(encoded_str)
            flipped_coords = [(c[1], c[0]) for c in coords]
            return LineString(flipped_coords)
        except:
            return None
    
    df['path_line'] = df['encodedPolyline'].apply(decode_to_line)
    
    gdf = gpd.GeoDataFrame(df, geometry='path_line', crs="EPSG:4326").to_crs("EPSG:2193")

    gdf['start_point'] = start_point
    gdf['end_point'] = end_point
    # gdf_lines.to_file("auckland_rides.gpkg", driver="GPKG")
    return gdf

    
def load_geofence(json_file=None):
    """
    Parse a GBFS geofencing_zones JSON response into a GeoDataFrame.

    Extracts zone geometries and flattens the nested rules array into
    separate columns. Reprojects from WGS84 (EPSG:4326) to NZTM (EPSG:2193).
    All zones are returned — callers should filter by ride_end_allowed,
    ride_start_allowed, or ride_through_allowed as needed.

    Parameters
    ----------
    json_file : dict
        Parsed JSON response containing a 'data.geofencing_zones.features'
        structure as per the GBFS spec.

    Returns
    -------
    GeoDataFrame
        One row per zone with columns: name, ride_start_allowed,
        ride_end_allowed, ride_through_allowed, maximum_speed_kph, geometry.
        CRS is EPSG:2193.

    Raises
    ------
    ValueError
        If the expected 'data' key is absent from json_file.
    """
    if json_file is None:
        json_file = pd.read_json("https://data.rideflamingo.com/gbfs/3/auckland/geofencing_zones.json")

    if "data" not in json_file:
        raise ValueError("Invalid JSON structure: expected 'data.geofencing_zones.features' to be present.")
    data = json_file["data"]["geofencing_zones"]["features"]

    gdf = gpd.GeoDataFrame.from_features(data, crs="EPSG:4326").to_crs("EPSG:2193")

    gdf['name'] = gdf['name'].apply(lambda x: x[0]['text'] if isinstance(x, list) else str(x))
    gdf['ride_start_allowed'] = gdf['rules'].apply(lambda x: str(x[0]['ride_start_allowed']) if "ride_start_allowed" in x[0] else "Unknown")
    gdf['ride_end_allowed'] = gdf['rules'].apply(lambda x: str(x[0]['ride_end_allowed']) if "ride_end_allowed" in x[0] else "Unknown")
    gdf['ride_through_allowed'] = gdf['rules'].apply(lambda x: str(x[0]['ride_through_allowed']) if "ride_through_allowed" in x[0] else "Unknown")
    gdf['maximum_speed_kph'] = gdf['rules'].apply(lambda x: x[0]['maximum_speed_kph'] if "maximum_speed_kph" in x[0] else 25)

    gdf = gdf.drop(columns=['rules'])

    # gdf.to_file("no_parking_zone.gpkg", driver="GPKG")

    return gdf


def _get_api_key():
    load_dotenv()
    key = os.getenv("STATS_NZ_API_KEY")
  
    if key is None:
        raise EnvironmentError(
            "Set STATS_NZ_API_KEY in your environment "
            "or .env file before calling this function."
        )
    return key


# SA2 2026: 123515, SA1 2026: 123510
def load_sa(layer_id=123510, api_key=None):
    """
        Download Stats NZ statistical area boundaries via WFS.

        Fetches a bounding-box clipped layer from the Stats NZ datafinder WFS
        service and returns it as a GeoDataFrame in EPSG:2193.

        Parameters
        ----------
        layer_id : int, optional
            Stats NZ WFS layer ID. Defaults to 123510 (SA1 2026). Use 123515
            for SA2 2026.
        api_key : str, optional
            Stats NZ API key. If None, reads from the STATS_NZ_API_KEY
            environment variable.

        Returns
        -------
        GeoDataFrame
            Statistical area boundaries clipped to the Auckland CBD bounding
            box, in EPSG:2193.

        Raises
        ------
        EnvironmentError
            If no API key is supplied and STATS_NZ_API_KEY is not set.
        requests.HTTPError
            If the WFS request fails.
        """
    # print(api_key)
    api_key = api_key or _get_api_key()
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"layer-{layer_id}",       
        "outputFormat": "json",
        "srsName": "EPSG:2193",
        "bbox": "1740000,5900000,1790000,5950000,EPSG:2193",
    }
    response = requests.get(
        WFS_URL.format(key=api_key),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return gpd.read_file(BytesIO(response.content))


def load_sa_cached(layer_id=123510, api_key=None):
    """
    Download Stats NZ boundaries with local disk caching.

    On first call, fetches boundaries via load_sa() and writes a GeoPackage
    to ~/.cache/flamingo_escooter/{layer_id}_statsnz.gpkg. Subsequent calls read from
    cache, skipping the network request entirely.

    Parameters
    ----------
    layer_id : int, optional
        Stats NZ WFS layer ID. Defaults to 123510 (SA1 2026).
    api_key : str, optional
        Stats NZ API key. Passed through to load_sa() if a network call
        is needed.

    Returns
    -------
    GeoDataFrame
        Statistical area boundaries in EPSG:2193.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{layer_id}_statsnz.gpkg"

    if cache_file.exists():
        return gpd.read_file(cache_file)

    gdf = load_sa(layer_id, api_key)
    gdf.to_file(cache_file, driver="GPKG")
    return gdf

def load_transit_stations():
    """Load Auckland transit stations. (Bus + Train)"""
    path = DATA_DIR / "akl_transit_station.gpkg"
    stations = gpd.read_file(path)
    return stations.to_crs(2193)

