"""
Legacy report generator module for backward compatibility.

This module provides the original VesselReportGenerator class interface
while using the new modular ReportWriter under the hood.
"""

from app.tools.report_writer import report_writer, ReportWriter
from app.models.workflow import AnalysisState


class VesselReportGenerator:
    """
    Legacy VesselReportGenerator class for backward compatibility.
    
    Delegates all operations to the new modular ReportWriter.
    """
    
    def __init__(self):
        """Initialize with the new report writer"""
        self.report_writer = report_writer
    
    def generate_report(self, state: AnalysisState) -> str:
        """
        Generate complete HTML report for multiple vessels.
        
        Args:
            state: Analysis state containing vessels and research data
            
        Returns:
            Path to generated report file
        """
        return self.report_writer.generate_report(state)
    
    def create_vessel_map(self, vessel):
        """
        Create interactive Folium map for vessel track.
        
        Args:
            vessel: VesselData with track points
            
        Returns:
            HTML string containing the map
        """
        return self.report_writer.create_vessel_map(vessel)


# For backward compatibility, also export the class directly
__all__ = ['VesselReportGenerator']