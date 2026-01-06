import pytest

from app.utils import geo


def test_haversine_distance_same_point():
    """Test that distance between same points is 0"""
    distance = geo.haversine_distance(55.7558, 37.6173, 55.7558, 37.6173)
    assert distance == 0.0


def test_haversine_distance_positive():
    """Test that distance is always positive"""
    distance = geo.haversine_distance(55.7558, 37.6173, 55.7559, 37.6174)
    assert distance > 0


def test_haversine_distance_symmetric():
    """Test that distance calculation is symmetric"""
    dist1 = geo.haversine_distance(55.7558, 37.6173, 55.7559, 37.6174)
    dist2 = geo.haversine_distance(55.7559, 37.6174, 55.7558, 37.6173)

    # Allow for small floating point differences
    assert abs(dist1 - dist2) < 0.0001


def test_haversine_distance_reasonable_values():
    """Test that distance calculations return reasonable values"""
    # Distance between Moscow and St. Petersburg should be around 634 km
    distance = geo.haversine_distance(55.7558, 37.6173, 59.9343, 30.3351)
    assert 600 < distance < 700  # Should be between 600 and 700 km


def test_haversine_distance_poles():
    """Test distance calculation to poles"""
    # Distance from Moscow to North Pole
    distance = geo.haversine_distance(55.7558, 37.6173, 90, 0)
    assert 3000 < distance < 4000  # Should be between 3000 and 4000 km


def test_haversine_distance_equator():
    """Test distance calculation near equator"""
    # Distance between two points on equator, 1 degree longitude apart
    distance = geo.haversine_distance(0, 0, 0, 1)
    assert 110 < distance < 120  # Should be around 111 km


def test_get_geospatial_filter_empty():
    """Test geospatial filter with no stations"""
    # This test will need to be implemented with a mock database session
    # For now, we'll just test that the function exists and can be called
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = geo.get_geospatial_filter(mock_db, 55.7558, 37.6173, 1.0)
    assert isinstance(result, list)


def test_haversine_distance_invalid_coordinates():
    """Test that the function handles edge cases properly"""
    # These should not raise exceptions
    try:
        # Test with coordinates that are valid but extreme
        distance = geo.haversine_distance(
            -90, -180, 90, 180
        )  # From south pole to north pole
        assert isinstance(distance, float)
        assert distance > 0
    except Exception:
        pytest.fail(
            "haversine_distance should not raise exception for valid coordinates"
        )
