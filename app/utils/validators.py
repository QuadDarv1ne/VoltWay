"""
Custom validators for input data.
"""

import re
from typing import Optional

from fastapi import HTTPException, status


def validate_coordinates(latitude: float, longitude: float) -> None:
    """
    Validate geographic coordinates.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        
    Raises:
        HTTPException: If coordinates are invalid
    """
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid latitude: {latitude}. Must be between -90 and 90",
        )
    
    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid longitude: {longitude}. Must be between -180 and 180",
        )


def validate_radius(radius_km: float, max_radius: float = 100.0) -> None:
    """
    Validate search radius.
    
    Args:
        radius_km: Radius in kilometers
        max_radius: Maximum allowed radius
        
    Raises:
        HTTPException: If radius is invalid
    """
    if radius_km <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid radius: {radius_km}. Must be positive",
        )
    
    if radius_km > max_radius:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Radius {radius_km}km exceeds maximum of {max_radius}km",
        )


def validate_connector_type(connector_type: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize connector type.
    
    Args:
        connector_type: Connector type string
        
    Returns:
        Sanitized connector type or None
        
    Raises:
        HTTPException: If connector type is invalid
    """
    if connector_type is None:
        return None
    
    # Check length
    if len(connector_type) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connector type too long (max 50 characters)",
        )
    
    # Allow only alphanumeric, spaces, and common separators
    if not re.match(r'^[a-zA-Z0-9\s,\-/]+$', connector_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connector type contains invalid characters",
        )
    
    return connector_type.strip()


def validate_power(power_kw: Optional[float], max_power: float = 1000.0) -> None:
    """
    Validate power rating.
    
    Args:
        power_kw: Power in kilowatts
        max_power: Maximum allowed power
        
    Raises:
        HTTPException: If power is invalid
    """
    if power_kw is None:
        return
    
    if power_kw <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid power: {power_kw}. Must be positive",
        )
    
    if power_kw > max_power:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Power {power_kw}kW exceeds maximum of {max_power}kW",
        )
