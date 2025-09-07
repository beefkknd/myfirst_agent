"""
Vessel search service orchestration.

High-level service that orchestrates vessel search operations using
the ElasticsearchService tool.
"""

from typing import List, Optional
from ..models.vessel import VesselData
from ..tools.elasticsearch_client import elasticsearch_service


class VesselSearchService:
    """
    High-level service for vessel search operations.
    
    Orchestrates vessel search workflows using the underlying
    ElasticsearchService tool.
    """
    
    def __init__(self):
        """Initialize vessel search service"""
        self.elasticsearch = elasticsearch_service
        print("🔍 VesselSearchService initialized")
    
    def find_long_distance_vessels(
        self,
        min_distance_miles: float = 50.0,
        date: str = "2022-01-01",
        max_vessels: int = 10
    ) -> List[VesselData]:
        """
        Find vessels that traveled long distances on a specific date.
        
        Args:
            min_distance_miles: Minimum distance threshold
            date: Analysis date (YYYY-MM-DD format)
            max_vessels: Maximum number of vessels to return
            
        Returns:
            List of VesselData objects sorted by distance traveled
        """
        print(f"🚢 Searching for vessels with >{min_distance_miles} miles on {date}")
        
        try:
            # Use the elasticsearch service to find vessels
            vessels = self.elasticsearch.search_vessels_by_distance(
                min_distance_miles=min_distance_miles,
                date=date
            )
            
            # Limit results to max_vessels
            limited_vessels = vessels[:max_vessels]
            
            print(f"✅ Found {len(limited_vessels)} vessels matching criteria")
            return limited_vessels
            
        except Exception as e:
            print(f"❌ Vessel search failed: {e}")
            return []
    
    def get_vessel_summary_stats(self, vessels: List[VesselData]) -> dict:
        """
        Get summary statistics for a list of vessels.
        
        Args:
            vessels: List of VesselData objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not vessels:
            return {
                "total_vessels": 0,
                "total_distance_miles": 0.0,
                "average_distance_miles": 0.0,
                "max_distance_miles": 0.0,
                "total_track_points": 0
            }
        
        total_distance = sum(vessel.total_distance_miles for vessel in vessels)
        max_distance = max(vessel.total_distance_miles for vessel in vessels)
        total_points = sum(len(vessel.track_points) for vessel in vessels)
        
        return {
            "total_vessels": len(vessels),
            "total_distance_miles": total_distance,
            "average_distance_miles": total_distance / len(vessels),
            "max_distance_miles": max_distance,
            "total_track_points": total_points,
            "vessels_with_names": len([v for v in vessels if v.vessel_name]),
            "vessels_with_imo": len([v for v in vessels if v.imo and v.imo != "IMO0000000"])
        }
    
    def validate_vessel_data(self, vessel: VesselData) -> dict:
        """
        Validate vessel data completeness and quality.
        
        Args:
            vessel: VesselData object to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            "is_valid": True,
            "issues": [],
            "completeness_score": 0.0
        }
        
        # Check required fields
        if not vessel.mmsi:
            validation["issues"].append("Missing MMSI")
            validation["is_valid"] = False
        
        if not vessel.vessel_name:
            validation["issues"].append("Missing vessel name")
        
        if not vessel.track_points:
            validation["issues"].append("No track points available")
            validation["is_valid"] = False
        elif len(vessel.track_points) < 2:
            validation["issues"].append("Insufficient track points for analysis")
        
        # Calculate completeness score
        fields_present = 0
        total_fields = 8
        
        if vessel.mmsi: fields_present += 1
        if vessel.vessel_name: fields_present += 1
        if vessel.imo and vessel.imo != "IMO0000000": fields_present += 1
        if vessel.call_sign: fields_present += 1
        if vessel.vessel_type: fields_present += 1
        if vessel.length: fields_present += 1
        if vessel.width: fields_present += 1
        if vessel.draft: fields_present += 1
        
        validation["completeness_score"] = fields_present / total_fields
        
        return validation
    
    def check_service_health(self) -> dict:
        """
        Check the health of the vessel search service.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Check elasticsearch health
            es_health = self.elasticsearch.health_check()
            
            return {
                "service_status": "operational",
                "elasticsearch_status": es_health.get("status", "unknown"),
                "dependencies": {
                    "elasticsearch": es_health.get("status") == "connected"
                }
            }
        except Exception as e:
            return {
                "service_status": "error",
                "error": str(e),
                "dependencies": {
                    "elasticsearch": False
                }
            }


# Global service instance
vessel_search_service = VesselSearchService()