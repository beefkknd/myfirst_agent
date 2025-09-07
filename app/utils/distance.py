"""
Geospatial distance calculation utilities using Haversine formula
"""

import math
from typing import List, Dict, Any


def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in miles.
    
    Uses the Haversine formula to compute the shortest distance between
    two points on a sphere (Earth) given their latitude and longitude.
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees  
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
        
    Returns:
        Distance in nautical miles
    """
    R = 3959  # Earth's radius in miles
    
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def calculate_track_distance(track_points: List[Dict[str, Any]]) -> float:
    """
    Calculate total distance traveled along a track of coordinate points.
    
    Args:
        track_points: List of dicts with 'lat' and 'lon' keys
        
    Returns:
        Total distance in miles
    """
    if len(track_points) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(1, len(track_points)):
        prev_point = track_points[i-1]
        curr_point = track_points[i]
        
        distance = calculate_distance_miles(
            prev_point["lat"], prev_point["lon"],
            curr_point["lat"], curr_point["lon"]
        )
        total_distance += distance
    
    return total_distance


def calculate_bounding_box_distance(min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> Dict[str, float]:
    """
    Calculate distances for a bounding box defined by min/max coordinates.
    
    Args:
        min_lat: Minimum latitude
        min_lon: Minimum longitude
        max_lat: Maximum latitude  
        max_lon: Maximum longitude
        
    Returns:
        Dict with diagonal, horizontal, and vertical distances
    """
    diagonal = calculate_distance_miles(min_lat, min_lon, max_lat, max_lon)
    
    # Horizontal distance at average latitude
    avg_lat = (min_lat + max_lat) / 2
    horizontal = calculate_distance_miles(avg_lat, min_lon, avg_lat, max_lon)
    
    # Vertical distance at average longitude
    avg_lon = (min_lon + max_lon) / 2  
    vertical = calculate_distance_miles(min_lat, avg_lon, max_lat, avg_lon)
    
    return {
        "diagonal_miles": diagonal,
        "horizontal_miles": horizontal,
        "vertical_miles": vertical,
        "max_dimension_miles": max(diagonal, horizontal, vertical)
    }