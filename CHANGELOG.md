# Changelog

## [0.4.0] — 2026-06-05

### Changed
- **Small metadata changes and file naming updates to ensure consistent naming convention. Final version before full PyPI release.

## [0.3.0] — 2026-05-27

### Added
- **`analyse()`** — New convenience function that runs the full analysis pipeline
  (load trips → OD flows → geofence violations → transit proximity) in a single
  call and returns a fully-enriched GeoDataFrame.

### Changed
- **`geofence_violations()`** — Changed from returning a filtered subset (inner join)
  to returning the **full trips DataFrame** with two new boolean/string columns
  (`is_violation`, `violated_area`). All rows are preserved, making subsequent
  composition with other analyses easier.

  ```python
  # Before (0.2.1): returned only violating trips
  violations = geofence_violations(trips, geofence)

  # After (0.3.0): returns all trips, adds flag columns
  trips = geofence_violations(trips, geofence)
  assert len(trips) == len(original)  # all rows preserved
  ```

- **`violations_table_wide()`** — Now accepts the full trips DataFrame instead of a
  pre-filtered violations subset. The `is_violation` filter is applied internally.
  Parameter renamed from `violations_gdf` → `trips_gdf` for consistency.
- **`transit_proximity()`** — Removed the printed summary output (now handled by
  `analyse()` when running the full pipeline).
- **`geofence_violations()`** — Added deduplication logic to handle trips whose
  endpoint falls inside multiple overlapping geofence zones.
- **`od_flows()`** — Added explicit docstring documenting the use of positional
  column indexing to locate zone name columns.

---

## [0.2.1] — 2026-05-25

### Changed
- No functional changes. Minor changes to `README.md`, correcting the instructions for package usage.

---

## [0.2.0] — 2026-05-21

### Added
- **`first_and_last_mile_heatmap()`** — New interactive Folium heatmap showing
  where trips started or ended within transit proximity threshold. Supports
  `location_type` parameter (`"start"`, `"end"`, or `"both"`).
- **`load_dotenv()`** — Now called in `_get_api_key()` so `STATS_NZ_API_KEY` can
  be loaded from a `.env` file in addition to the system environment.

### Changed
- **`load_geofence()`** — Renamed from `geofence_json_to_gdf()` for clarity.
- **`load_transit_stations()`** — Replaced the previous pair of
  `load_train_stations()` and `load_bus_stops()` with a single unified function
  that returns combined bus + train stations as a single GeoDataFrame.
- **`transit_proximity()`** — Default `distance` reduced from **50 m to 10 m** to
  reflect a more realistic first/last-mile connection distance.
  Added a printed summary showing the percentage of trips near transit.
- **`path_heatmap()`** and **`violation_heatmap()`** — Updated colour gradient from
  blue→cyan→lime→yellow→red to a consistent pink/magenta (Flamingo Scooters) palette
  (`#ffb3d9` → `#fe1f68`) across all heatmap functions.
  Tightened rendering parameters (`radius=6`, `blur=8`) for sharper visualisations.
- **`violations_table_wide()`** — Added docstring.

### Removed
- **`load_train_stations()`** — Merged into `load_transit_stations()`.
- **`load_bus_stops()`** — Merged into `load_transit_stations()`.
- **`geofence_json_to_gdf()`** — Renamed to `load_geofence()`.

### Data
- Replaced bundled raw data files with a cleaned, minimal dataset:
  - `BusService_-4169205071737169352 (1).gpkg`, full `Train_Station/` shapefile directory,
    `auckland_geofencing_zones.json`.
  - Added: `akl_transit_station.gpkg` (combined bus + train stations).
  - Renamed: `Flamingo - Auckland CBD UoA Trip Data (Polylines) - Sample.csv` to `flamingo_trip_dataset_sample.csv`.

---

## [0.1.0] — 2026-05-18

### Added
- **`load_trips()`** — Load Flamingo trip data from CSV, decode encoded polylines
  into LineString geometries, reproject to EPSG:2193 (NZTM).
- **`load_sa()`** / **`load_sa_cached()`** — Fetch Stats NZ statistical area
  boundaries via WFS with local disk caching (`.cache/flamingo_escooter/`).
- **`geofence_json_to_gdf()`** — Parse a GBFS v3 geofencing_zones JSON response
  into a GeoDataFrame with zone attributes (`ride_start_allowed`,
  `ride_end_allowed`, `ride_through_allowed`, `maximum_speed_kph`).
- **`load_train_stations()`** — Load Auckland train station locations from
  bundled shapefile.
- **`load_bus_stops()`** — Load Auckland bus stop locations from bundled GeoPackage.
- **`od_flows()`** — Spatial join of trip start/end points to SA zone polygons,
  producing `origin` and `destination` columns.
- **`geofence_violations()`** — Filter trips to those whose endpoint falls inside
  a no-parking geofence zone. Returns a subset with an `area` column naming
  the violated zone.
- **`violations_table_wide()`** — Aggregate violation counts per zone, sorted
  descending.
- **`transit_proximity()`** — Flag trips whose start or end point falls within
  50 m of a transit stop. Adds distance and boolean flag columns.
- **`path_heatmap()`** — Interactive Folium heatmap of all trip paths.
- **`violation_heatmap()`** — Interactive Folium heatmap of parking violation
  endpoint locations.
- Bundled sample data: `Flamingo - Auckland CBD UoA Trip Data (Polylines) - Sample.csv`,
  `auckland_geofencing_zones.json`, bus stop GeoPackage, train station shapefile.