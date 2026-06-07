#### Link to full documentation: https://jhe482-uoa.github.io/flamingo-escooter/

This Python package is used for analysing Flamingo e-scooter movement patterns within the Auckland CBD, providing tools to clean trip data and easily identify trips ending in restricted no-parking zones. It is designed to assist Auckland Council, Auckland Transport, and Flamingo Scooters to better understand scooter usage, support infrastructure planning, and improve enforcement of parking restrictions.

## Features:
- Loads and cleans Flamingo trip data
- Generate OD flows between SA zones
- Detect rides ending in no-parking zones
- Create interactive folium maps to visualise common routes and parking violation areas
- Analyse how many users may be using the scooters to connect to public transport

## Installation
Install from PyPI:
```bash
pip install flamingo-escooter
```

Install from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ flamingo-escooter
```

Install from source for development:
```bash
git clone https://github.com/jhe482-uoa/flamingo-escooter
cd flamingo-escooter
python3 -m pip install -e .[dev]
```

## Quick-start example

```python
import flamingo_escooter as fe

trips = fe.analyse()
fe.path_heatmap(trips) # See Path Heatmap image for expected output

fe.violation_heatmap(trips) # See Violation Heatmap image for expected output

violation_df_wide = fe.violations_table_wide(trips)
violation_df_wide # See Violation table in wide format

fe.first_and_last_mile_heatmap(trips) # See First and Last Mile Heatmap for expected output
```

Expected output:
- A shape tuple for the loaded trips, e.g. `(N, M)`
- A columns index containing `start_point`, `end_point`, and `path_line`
- An origin/destination pair from the first row after `od_flows()`

Use `fe.analyse()` to run the full pipeline and return an enriched GeoDataFrame.

See `demo.ipynb` for an additional demonstration.

## Example Outputs using demo data

### Path Heatmap

![Path Heatmap](docs/path_heatmap.png)

### Violation Heatmap

![Violation Heatmap](docs/violation_heatmap.png)

### Violation table in wide format

![Violation Table](docs/violation_table.png)

### First and Last Mile Heatmap

![first_and_last_mile_heatmap](docs/transit_heatmap.png)

## Functions
### Master Function
- `analyse()` — Runs the full pipeline in one call: loads trips, SA1 boundaries, geofence zones, and transit stations, then computes OD flows, flags geofence violations, and calculates transit proximity. Returns a single enriched trip GeoDataFrame with `origin`, `destination`, `is_violation`, `violated_area`, `start/end_near_transit`, and `start/end_distance_to_transit_m` columns.

### Data Loading
- `load_trips(data_file=None)` — Loads Flamingo trip CSV, decodes encoded polylines into LineString geometries, and reprojects start/end points to EPSG:2193 (NZTM). Defaults to the bundled sample dataset; accepts a file path or DataFrame.
- `load_sa(layer_id=123510)` — Downloads Stats NZ SA1 (or SA2) boundaries from the datafinder WFS API, clipped to the Auckland CBD bounding box.
- `load_sa_cached(layer_id=123510)` — Wraps `load_sa()` with local disk caching at `~/.cache/flamingo_escooter/`. Skips the network call on subsequent runs.
- `load_geofence(json_file=None)` — Fetches live Flamingo geofence zones from the GBFS API and parses them into a GeoDataFrame with `ride_start_allowed`, `ride_end_allowed`, `ride_through_allowed`, and `maximum_speed_kph` columns. Accepts a pre-loaded JSON dict.
- `load_transit_stations()` — Loads bundled Auckland bus and train stop locations and merges them into a single GeoDataFrame.

### Analysis
- `od_flows(trips_gdf, zones_gdf)` — Spatially joins trip start and end points to SA1 zones, adding `origin` and `destination` columns. Trips outside any zone boundary are dropped.
- `geofence_violations(trips_gdf, no_park_gdf, location_type="end")` — Flags trips whose endpoint falls inside a no-parking zone. Adds `is_violation` (bool) and `violated_area` (zone name or None) columns to the full trips GeoDataFrame. All rows are preserved.
- `violations_table_wide(trips_gdf)` — Summarises violations by zone from the output of `geofence_violations()`, returning a wide-format DataFrame with `violated_area` and `total_violations` columns sorted by count descending.
- `transit_proximity(trips_gdf, transit_gdf, distance=10)` — Finds the nearest transit stop to each trip's start and end point, adding `start/end_distance_to_transit_m` and `start/end_near_transit` columns. Prints a proximity summary to stdout.

### Visualisation
All visualisation functions return a `folium.Map` object displayable inline in Jupyter.

- `path_heatmap(trips)` — Interactive heatmap of scooter route density across the CBD, decoded directly from encoded polylines. Hot spots indicate frequently used streets.
- `violation_heatmap(trips_gdf, location_type="end")` — Interactive heatmap of no-parking violation locations, filtered from `is_violation` column. Accepts the full trips GeoDataFrame from `geofence_violations()` or `analyse()`.
- `first_and_last_mile_heatmap(trips_gdf, location_type="both")` — Interactive heatmap of trip endpoints near transit stops, filtered from `start/end_near_transit` columns. Supports `"start"`, `"end"`, or `"both"` as toggleable layers.

## Authors

- Jeff He - jhe482@aucklanduni.ac.nz
- Georgia Short - gsho521@aucklanduni.ac.nz
- Hans Setiawan - hset686@aucklanduni.ac.nz

## Supervisor
- Dr. Hyesop Shin - hyesop.shin@auckland.ac.nz

## Industry Partner
- Flamingo Scooters