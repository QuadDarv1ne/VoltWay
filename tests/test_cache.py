from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.config import settings
from app.utils import cache


def test_cache_manager_initialization_success():
    """Test that CacheManager initializes successfully when Redis is available"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        assert cache_manager.redis_client == mock_redis_instance


def test_cache_manager_initialization_failure():
    """Test that CacheManager handles Redis connection failure gracefully"""
    with patch("redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception("Redis connection failed")

        cache_manager = cache.CacheManager()
        assert cache_manager.redis_client is None


def test_cache_get_when_redis_unavailable():
    """Test that get returns None when Redis is not available"""
    cache_manager = cache.CacheManager()
    cache_manager.redis_client = None

    result = cache_manager.get("test_key")
    assert result is None


def test_cache_set_when_redis_unavailable():
    """Test that set returns False when Redis is not available"""
    cache_manager = cache.CacheManager()
    cache_manager.redis_client = None

    result = cache_manager.set("test_key", "test_value")
    assert result is False


def test_cache_delete_when_redis_unavailable():
    """Test that delete returns False when Redis is not available"""
    cache_manager = cache.CacheManager()
    cache_manager.redis_client = None

    result = cache_manager.delete("test_key")
    assert result is False


def test_cache_get_found():
    """Test cache get when key exists"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = b"serialized_value"
        mock_redis.return_value = mock_redis_instance

        # Mock pickle.loads to return a test value
        with patch("app.utils.cache.pickle.loads", return_value="deserialized_value"):
            cache_manager = cache.CacheManager()
            result = cache_manager.get("test_key")

            assert result == "deserialized_value"
            mock_redis_instance.get.assert_called_once_with("test_key")


def test_cache_get_not_found():
    """Test cache get when key doesn't exist"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = None
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        result = cache_manager.get("test_key")

        assert result is None


def test_cache_set_success():
    """Test cache set operation"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True
        mock_redis.return_value = mock_redis_instance

        # Mock pickle.dumps
        with patch("app.utils.cache.pickle.dumps", return_value=b"serialized_value"):
            cache_manager = cache.CacheManager()
            result = cache_manager.set("test_key", "test_value", expire=3600)

            assert result is True
            mock_redis_instance.setex.assert_called_once_with(
                "test_key", 3600, b"serialized_value"
            )


def test_cache_delete_success():
    """Test cache delete operation"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.delete.return_value = 1  # 1 key deleted
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        result = cache_manager.delete("test_key")

        assert result is True
        mock_redis_instance.delete.assert_called_once_with("test_key")


def test_cache_delete_not_found():
    """Test cache delete when key doesn't exist"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.delete.return_value = 0  # 0 keys deleted
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        result = cache_manager.delete("test_key")

        assert result is False


def test_get_station_cache_key():
    """Test generation of station cache key"""
    cache_manager = cache.CacheManager()

    key = cache_manager.get_station_cache_key(
        latitude=55.7558,
        longitude=37.6173,
        radius_km=10.0,
        connector_type="CCS",
        min_power_kw=50.0,
        skip=0,
        limit=10,
    )

    # Check that the key contains all the expected components
    assert "stations:" in key
    assert "lat:55.7558" in key
    assert "lon:37.6173" in key
    assert "radius:10.0" in key
    assert "connector:CCS" in key
    assert "min_power:50.0" in key
    assert "skip:0" in key
    assert "limit:10" in key


def test_get_station_cache_key_with_none_values():
    """Test generation of station cache key with None values"""
    cache_manager = cache.CacheManager()

    key = cache_manager.get_station_cache_key(
        latitude=55.7558,
        longitude=37.6173,
        radius_km=10.0,
        connector_type=None,  # This should be excluded
        min_power_kw=None,  # This should be excluded
        skip=0,
        limit=10,
    )

    # Check that the key contains all the expected components
    assert "stations:" in key
    assert "lat:55.7558" in key
    assert "lon:37.6173" in key
    assert "radius:10.0" in key
    # connector_type and min_power should not be in the key since they're None
    assert "connector:" not in key
    assert "min_power:" not in key
    assert "skip:0" in key
    assert "limit:10" in key


def test_clear_station_cache():
    """Test clearing station cache"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.keys.return_value = [
            "stations:lat:55.7558:lon:37.6173",
            "stations:lat:56.0:lon:38.0",
        ]
        mock_redis_instance.delete.return_value = 2
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        result = cache_manager.clear_station_cache()

        assert result == 2
        mock_redis_instance.keys.assert_called_once_with("stations:*")
        mock_redis_instance.delete.assert_called_once_with(
            "stations:lat:55.7558:lon:37.6173", "stations:lat:56.0:lon:38.0"
        )


def test_clear_station_cache_no_keys():
    """Test clearing station cache when no keys exist"""
    with patch("redis.from_url") as mock_redis:
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.keys.return_value = []  # No keys found
        mock_redis.return_value = mock_redis_instance

        cache_manager = cache.CacheManager()
        result = cache_manager.clear_station_cache()

        assert result == 0
        mock_redis_instance.keys.assert_called_once_with("stations:*")
        # delete should not be called if no keys exist
        mock_redis_instance.delete.assert_not_called()
