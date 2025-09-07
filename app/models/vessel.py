"""
Vessel domain models - Core business entities for maritime vessels
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VesselData(BaseModel):
    """
    Core vessel data model representing a maritime vessel with tracking information.
    
    This is the primary domain entity that aggregates vessel identification,
    physical specifications, and movement tracking data.
    """
    mmsi: str = Field(..., description="Maritime Mobile Service Identity - primary vessel identifier")
    vessel_name: str = Field(..., description="Official vessel name")
    imo: Optional[str] = Field(None, description="International Maritime Organization number")
    call_sign: Optional[str] = Field(None, description="Radio call sign identifier")
    vessel_type: Optional[str] = Field(None, description="Vessel classification type")
    
    # Physical specifications
    length: Optional[float] = Field(None, description="Vessel length overall in meters")
    width: Optional[float] = Field(None, description="Vessel beam width in meters") 
    draft: Optional[float] = Field(None, description="Vessel draft depth in meters")
    
    # Movement tracking data
    track_points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Time-series location data points with coordinates and movement metrics"
    )
    total_distance_miles: float = Field(
        default=0.0,
        description="Computed total distance traveled in nautical miles"
    )
    
    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            # Custom encoders can be added here for special types
        }
        
    def get_track_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the vessel's track"""
        if not self.track_points:
            return {
                "point_count": 0,
                "distance_miles": 0.0,
                "duration_hours": 0
            }
            
        return {
            "point_count": len(self.track_points),
            "distance_miles": self.total_distance_miles,
            "start_time": self.track_points[0].get("timestamp") if self.track_points else None,
            "end_time": self.track_points[-1].get("timestamp") if self.track_points else None,
            "max_speed_knots": max(point.get("sog", 0) for point in self.track_points) if self.track_points else 0
        }