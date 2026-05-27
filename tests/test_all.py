import pytest
import folium
import flamingo_escooter as fe


@pytest.fixture
def trips():
    return fe.load_trips()

@pytest.fixture
def zones():
    return fe.load_sa_cached()

@pytest.fixture
def geofence():
    return fe.load_geofence()

@pytest.fixture
def trips_with_violations(trips, geofence):
    return fe.geofence_violations(trips, geofence)

@pytest.fixture
def transit():
    return fe.load_transit_stations()


def test_load_trips(trips):
    assert len(trips) > 0
    assert trips.crs.to_epsg() == 2193
    assert all(col in trips.columns for col in ["start_point", "end_point", "encodedPolyline"])

def test_od_flows(trips, zones):
    od = fe.od_flows(trips, zones)
    assert "origin" in od.columns and "destination" in od.columns
    assert od["origin"].notna().all()
    assert len(od) <= len(trips)

def test_load_geofence(geofence):
    assert geofence.crs.to_epsg() == 2193
    assert set(geofence["ride_end_allowed"]).issubset({"True", "False", "Unknown"})

def test_geofence_violations(trips, trips_with_violations):
    # all rows preserved, new flag columns added
    assert len(trips_with_violations) == len(trips)
    assert "is_violation" in trips_with_violations.columns
    assert "violated_area" in trips_with_violations.columns
    assert trips_with_violations["is_violation"].dtype == bool
    assert trips_with_violations["is_violation"].sum() > 0

@pytest.mark.parametrize("location_type", ["middle", "", "END", 123])
def test_invalid_location_type_raises(trips, geofence, location_type):
    with pytest.raises((ValueError, TypeError)):
        fe.geofence_violations(trips, geofence, location_type=location_type)

def test_violations_table_wide(trips_with_violations):
    table = fe.violations_table_wide(trips_with_violations)
    assert "violated_area" in table.columns
    assert "total_violations" in table.columns
    assert table["total_violations"].is_monotonic_decreasing
    assert table["total_violations"].sum() == trips_with_violations["is_violation"].sum()

def test_transit_proximity(trips, transit):
    result = fe.transit_proximity(trips, transit)
    assert len(result) == len(trips)
    assert result["start_near_transit"].dtype == bool
    assert (result["start_distance_to_transit_m"] >= 0).all()

def test_path_heatmap(trips):
    assert isinstance(fe.path_heatmap(trips), folium.Map)

def test_violation_heatmap(trips_with_violations):
    assert isinstance(fe.violation_heatmap(trips_with_violations), folium.Map)

def test_load_sa_cached_writes_cache(tmp_path, monkeypatch):
    import flamingo_escooter.io as fe_io
    monkeypatch.setattr(fe_io, "CACHE_DIR", tmp_path)
    fe.load_sa_cached()
    assert any(tmp_path.iterdir())