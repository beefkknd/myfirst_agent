"""
Report writer for vessel analysis reports.

MCP-ready service for generating interactive HTML reports with maps and visualizations.
Designed to be easily converted to MCP server in the future.
"""

import os
from typing import List, Dict, Any, Optional

import folium
from folium import plugins
from jinja2 import Template

from ..models.vessel import VesselData
from ..models.workflow import AnalysisState
from ..utils.file_ops import ensure_directory


class ReportWriter:
    """
    Report generation service for vessel analysis.
    
    This class is designed to be easily converted to an MCP server.
    All public methods represent future MCP server endpoints.
    """
    
    def __init__(self):
        """Initialize report writer with HTML template"""
        self.report_template = self._load_report_template()
        print("📝 ReportWriter initialized")
    
    # Future MCP Server Endpoints
    
    def generate_report(self, state: AnalysisState) -> str:
        """
        [Future MCP Endpoint] Generate complete HTML report for multiple vessels.
        
        Args:
            state: Analysis state containing vessels and research data
            
        Returns:
            Path to generated report file
        """
        if not state.selected_vessels:
            return self._generate_empty_report()
        
        print(f"📊 Generating report for {len(state.selected_vessels)} vessels...")
        
        vessels = state.selected_vessels
        
        # Create visualizations and data for all vessels
        vessel_maps = []
        vessel_max_speeds = []
        vessel_photos = []
        
        for vessel in vessels:
            # Create map for this vessel
            map_html = self.create_vessel_map(vessel)
            vessel_maps.append(map_html)
            
            # Calculate max speed
            max_speed = self._calculate_max_speed(vessel)
            vessel_max_speeds.append(max_speed)
            
            # Collect photos
            photos = self._collect_vessel_photos(vessel, state)
            vessel_photos.append(photos)
        
        # Render template
        template = Template(self.report_template)
        html_content = template.render(
            vessels=vessels,
            vessel_maps=vessel_maps,
            vessel_max_speeds=vessel_max_speeds,
            vessel_photos=vessel_photos,
            web_research=state.web_research_results,  # Legacy compatibility
            vessel_research_results=state.vessel_research_results  # New vessel-specific data
        )
        
        # Save report
        report_filename = self._save_report(html_content, vessels)
        
        print(f"✅ Report generated: {report_filename}")
        return report_filename
    
    def create_vessel_map(self, vessel: VesselData) -> str:
        """
        [Future MCP Endpoint] Create interactive Folium map for vessel track.
        
        Args:
            vessel: VesselData with track points
            
        Returns:
            HTML string containing the map
        """
        if not vessel.track_points:
            return "<p style='color: #FF5A5A; text-align: center; padding: 20px;'>No track data available</p>"
        
        # Calculate map center
        lats = [point["lat"] for point in vessel.track_points]
        lons = [point["lon"] for point in vessel.track_points]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create map with ocean theme
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles="OpenStreetMap",
            attr='Maritime Analysis System'
        )
        
        # Add vessel track line
        track_coords = [[point["lat"], point["lon"]] for point in vessel.track_points]
        folium.PolyLine(
            locations=track_coords,
            color="#4a90e2",  # Ocean blue
            weight=4,
            opacity=0.9,
            popup=f"{vessel.vessel_name} Track ({vessel.total_distance_miles:.1f} miles)"
        ).add_to(m)
        
        # Add start marker (green)
        if len(vessel.track_points) > 0:
            start_point = vessel.track_points[0]
            folium.Marker(
                [start_point["lat"], start_point["lon"]],
                popup=f"<b>START</b><br>{vessel.vessel_name}<br>{start_point['timestamp']}",
                icon=folium.Icon(color="green", icon="play")
            ).add_to(m)
        
        # Add end marker (red)
        if len(vessel.track_points) > 1:
            end_point = vessel.track_points[-1]
            folium.Marker(
                [end_point["lat"], end_point["lon"]],
                popup=f"<b>END</b><br>{vessel.vessel_name}<br>{end_point['timestamp']}",
                icon=folium.Icon(color="red", icon="stop")
            ).add_to(m)
        
        # Add intermediate waypoints (every 10th point)
        step = max(1, len(vessel.track_points) // 10)
        for i in range(0, len(vessel.track_points), step):
            if i == 0 or i == len(vessel.track_points) - 1:
                continue  # Skip start/end points
                
            point = vessel.track_points[i]
            folium.CircleMarker(
                [point["lat"], point["lon"]],
                radius=5,
                popup=f"<b>Waypoint {i+1}</b><br>Time: {point['timestamp']}<br>Speed: {point.get('sog', 0)} knots",
                color="#2c9aa0",
                fillColor="#60a5fa",
                fillOpacity=0.8
            ).add_to(m)
        
        # Add heatmap overlay
        heat_data = [[point["lat"], point["lon"]] for point in vessel.track_points]
        plugins.HeatMap(
            heat_data,
            radius=15,
            blur=12,
            gradient={0.2: '#2c9aa0', 0.4: '#4a90e2', 0.6: '#60a5fa', 1: '#06b6d4'}
        ).add_to(m)
        
        # Fit map to track bounds with padding
        sw = [min(lats), min(lons)]
        ne = [max(lats), max(lons)]
        m.fit_bounds([sw, ne], padding=(20, 20))
        
        return m._repr_html_()
    
    def health_check(self) -> Dict[str, Any]:
        """[Future MCP Endpoint] Check report writer service health"""
        return {
            "status": "operational",
            "template_loaded": self.report_template is not None,
            "dependencies": {
                "folium": True,
                "jinja2": True
            }
        }
    
    # Private helper methods
    
    def _generate_empty_report(self) -> str:
        """Generate a report when no vessels are found"""
        empty_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Vessel Analysis - No Results</title>
            <style>
                body { font-family: monospace; background: #1a2a38; color: #E6EEF2; 
                       display: flex; justify-content: center; align-items: center; 
                       height: 100vh; margin: 0; }
                .message { text-align: center; padding: 40px; 
                          border: 2px solid #2CA6D9; border-radius: 10px; }
                h1 { color: #2CA6D9; }
            </style>
        </head>
        <body>
            <div class="message">
                <h1>🚢 VESSEL ANALYSIS SYSTEM</h1>
                <p>No vessels found matching the specified criteria.</p>
                <p>Try adjusting the search parameters or date range.</p>
            </div>
        </body>
        </html>
        """
        
        ensure_directory("reports")
        filename = "reports/no_vessels_found.html"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(empty_html)
        
        return filename
    
    def _calculate_max_speed(self, vessel: VesselData) -> float:
        """Calculate maximum speed from vessel track points"""
        if not vessel.track_points:
            return 0.0
            
        max_speed = 0.0
        for point in vessel.track_points:
            speed = point.get("sog", 0)
            if isinstance(speed, (int, float)) and speed > max_speed:
                max_speed = speed
                
        return max_speed
    
    def _collect_vessel_photos(self, vessel: VesselData, state: AnalysisState) -> List[str]:
        """Collect photos for a vessel from research results"""
        photos = []
        
        # Get vessel-specific research results
        vessel_research = state.vessel_research_results.get(vessel.mmsi, [])
        
        # Fallback to legacy format for backward compatibility
        if not vessel_research and state.web_research_results:
            vessel_research = state.web_research_results
        
        # Extract images from research results
        for result in vessel_research:
            if hasattr(result, 'images_found'):
                photos.extend(result.images_found[:2])  # Max 2 photos per source
            elif isinstance(result, dict) and 'images_found' in result:
                photos.extend(result['images_found'][:2])
        
        return photos[:3]  # Maximum 3 photos total
    
    def _save_report(self, html_content: str, vessels: List[VesselData]) -> str:
        """Save HTML report to file with appropriate filename"""
        ensure_directory("reports")
        
        # Generate filename based on vessel count
        if len(vessels) == 1:
            vessel = vessels[0]
            safe_name = "".join(c for c in vessel.vessel_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            filename = f"reports/vessel_report_{vessel.mmsi}_{safe_name}.html"
        else:
            filename = f"reports/multi_vessel_report_{len(vessels)}_vessels.html"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return filename
    
    def _load_report_template(self) -> str:
        """Load the HTML report template"""
        # This is the complete template from the original report_generator.py
        # Keeping it as a string for now, but could be moved to external file
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MARITIME CONTROL SYSTEM - {{ vessels|length }} Vessel(s) Analysis</title>
    <style>
        :root {
            /* Deep Navy Gray with Aqua Accents */
            --navy-deepest: #0c1118;
            --navy-darker: #15232F;
            --navy-dark: #1a2a38;
            --navy-medium: #233645;
            --navy-light: #2d4152;
            --text-primary: #E6EEF2;
            --text-secondary: #B8C8D4;
            --text-muted: #8A9BA8;
            --aqua-bright: #2CA6D9;
            --aqua-medium: #2690C2;
            --aqua-dark: #1F7BA8;
            --aqua-muted: #4CB8E6;
            --panel-bg: #15232F;
            --panel-border: #233645;
            --success: #00D4AA;
            --warning: #FFB020;
            --error: #FF5A5A;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
            background: var(--navy-darker);
            color: var(--text-primary);
            line-height: 1.4;
            font-size: 13px;
            overflow-x: auto;
        }
        
        .container {
            max-width: 100vw;
            padding: 8px;
        }
        
        .header {
            background: linear-gradient(90deg, var(--navy-deepest) 0%, var(--navy-darker) 50%, var(--navy-deepest) 100%);
            border: 1px solid var(--aqua-bright);
            padding: 12px 16px;
            margin-bottom: 12px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(12, 17, 24, 0.4);
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(44, 166, 217, 0.15), transparent);
            animation: scan 4s linear infinite;
        }
        
        @keyframes scan {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .header h1 {
            color: var(--aqua-bright);
            font-size: 20px;
            font-weight: 600;
            text-shadow: 0 0 8px rgba(44, 166, 217, 0.4);
            letter-spacing: 1.5px;
        }
        
        .header .status {
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 4px;
            font-weight: 500;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            height: calc(100vh - 100px);
        }
        
        .column {
            background: var(--navy-darker);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            overflow-y: auto;
            box-shadow: 0 4px 12px rgba(12, 17, 24, 0.5);
        }
        
        .column-header {
            background: var(--navy-deepest);
            border-bottom: 2px solid var(--aqua-bright);
            padding: 12px 16px;
            color: var(--aqua-bright);
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 8px 8px 0 0;
        }
        
        .vessel-block {
            border-bottom: 1px solid var(--panel-border);
            padding: 16px;
            margin-bottom: 8px;
            position: relative;
            transition: all 0.2s ease;
        }
        
        .vessel-block:hover {
            background: var(--navy-dark);
            border-left: 4px solid var(--aqua-bright);
            transform: translateX(2px);
        }
        
        .vessel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--panel-border);
        }
        
        .vessel-name {
            color: var(--aqua-bright);
            font-weight: 600;
            font-size: 16px;
            text-shadow: 0 0 6px rgba(44, 166, 217, 0.3);
        }
        
        .vessel-status {
            color: var(--text-primary);
            font-size: 11px;
            background: var(--aqua-dark);
            padding: 4px 8px;
            border: 1px solid var(--aqua-bright);
            border-radius: 4px;
            font-weight: 500;
        }
        
        .data-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            margin-bottom: 8px;
        }
        
        .data-item {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            padding: 8px 10px;
            border-left: 3px solid var(--aqua-bright);
            border-radius: 4px;
            transition: border-color 0.2s ease;
        }
        
        .data-item:hover {
            border-left-color: var(--aqua-medium);
        }
        
        .data-label {
            color: var(--aqua-medium);
            font-size: 10px;
            display: block;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }
        
        .data-value {
            color: var(--text-primary);
            font-weight: 700;
            font-size: 13px;
            font-family: 'SF Mono', 'Monaco', monospace;
        }
        
        .map-toggle {
            background: var(--navy-deepest);
            border: 1px solid var(--aqua-bright);
            color: var(--text-primary);
            padding: 10px 14px;
            margin: 8px 0;
            cursor: pointer;
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 12px;
            font-weight: 500;
            width: 100%;
            text-align: left;
            position: relative;
            overflow: hidden;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        
        .map-toggle:hover {
            background: var(--aqua-medium);
            border-color: var(--aqua-muted);
            box-shadow: 0 4px 12px rgba(44, 166, 217, 0.3);
        }
        
        .map-toggle::before {
            content: '▶ ';
            transition: transform 0.2s;
        }
        
        .map-toggle.expanded::before {
            transform: rotate(90deg);
            display: inline-block;
        }
        
        .map-container {
            display: none;
            margin: 8px 0;
            border: 2px solid var(--panel-border);
            border-radius: 6px;
            height: 300px;
            overflow: hidden;
            background: var(--panel-bg);
        }
        
        .map-container.expanded {
            display: block;
        }
        
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 4px;
            margin: 6px 0;
        }
        
        .stat-box {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            padding: 8px 6px;
            text-align: center;
            border-left: 3px solid var(--aqua-bright);
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        
        .stat-box:hover {
            border-left-color: var(--success);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(12, 17, 24, 0.3);
        }
        
        .stat-number {
            color: var(--text-primary);
            font-weight: 700;
            font-size: 16px;
            display: block;
            text-shadow: none;
            font-family: 'SF Mono', monospace;
        }
        
        .stat-label {
            color: var(--aqua-medium);
            font-size: 9px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }
        
        .photos-compact {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 4px;
            margin: 6px 0;
        }
        
        .photo-thumb {
            width: 100%;
            height: 60px;
            object-fit: cover;
            border: 1px solid var(--panel-border);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .photo-thumb:hover {
            border-color: var(--aqua-bright);
            box-shadow: 0 0 8px rgba(44, 166, 217, 0.5);
        }
        
        .research-tabs {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            margin: 8px 0;
            border-radius: 6px;
            overflow: hidden;
        }

        .tab-headers {
            display: flex;
            background: var(--navy-darker);
            border-bottom: 1px solid var(--panel-border);
        }

        .tab-btn {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 10px 8px;
            cursor: pointer;
            font-family: inherit;
            font-size: 11px;
            font-weight: 500;
            border-right: 1px solid var(--panel-border);
            position: relative;
            transition: all 0.2s ease;
        }

        .tab-btn:last-child {
            border-right: none;
        }

        .tab-btn:hover {
            background: var(--aqua-medium);
            color: var(--text-primary);
        }

        .tab-btn.active {
            background: var(--aqua-bright);
            color: var(--text-primary);
        }

        .status-dot {
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            margin-left: 4px;
        }

        .status-success { background: var(--success); }
        .status-partial { background: var(--warning); }
        .status-failed { background: var(--error); }
        .status-unknown { background: var(--panel-border); }

        .tab-content {
            padding: 6px;
        }

        .source-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid var(--panel-border);
            background: var(--navy-darker);
            margin-bottom: 8px;
        }

        .source-url {
            color: var(--aqua-bright);
            text-decoration: none;
            font-size: 11px;
            font-weight: 500;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .source-url:hover {
            text-decoration: underline;
            color: var(--success);
        }

        .reliability-badge {
            background: var(--aqua-dark);
            color: var(--text-primary);
            padding: 4px 8px;
            font-size: 9px;
            font-weight: 500;
            border: 1px solid var(--aqua-bright);
            border-radius: 4px;
        }

        .research-details {
            background: var(--navy-dark);
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            padding: 12px;
            margin: 8px 0;
        }

        .details-header {
            color: var(--aqua-bright);
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--panel-border);
            padding-bottom: 4px;
        }

        .details-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .detail-item {
            color: var(--text-primary);
            font-size: 11px;
            line-height: 1.5;
            padding: 6px 0;
            border-left: 3px solid var(--aqua-bright);
            padding-left: 12px;
            margin-bottom: 6px;
            background: linear-gradient(90deg, rgba(44, 166, 217, 0.05) 0%, transparent 20%);
            border-radius: 0 4px 4px 0;
            transition: all 0.2s ease;
        }

        .detail-item:hover {
            background: linear-gradient(90deg, rgba(44, 166, 217, 0.1) 0%, transparent 30%);
            border-left-color: var(--aqua-muted);
            transform: translateX(2px);
        }

        .detail-item:last-child {
            margin-bottom: 0;
        }

        .detail-item::before {
            content: '▸';
            color: var(--aqua-bright);
            font-weight: bold;
            margin-right: 8px;
            font-size: 10px;
        }

        .screenshot-container {
            background: var(--navy-darker);
            border: 1px solid var(--panel-border);
            margin: 8px 0;
            border-radius: 6px;
            overflow: hidden;
        }

        .screenshot-toggle {
            background: var(--navy-deepest);
            color: var(--warning);
            padding: 8px 12px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            position: relative;
            transition: all 0.2s ease;
            border-bottom: 1px solid var(--panel-border);
        }

        .screenshot-toggle:hover {
            background: var(--warning);
            color: var(--navy-deepest);
        }

        .screenshot-toggle::before {
            content: '▶ ';
            transition: transform 0.2s;
            display: inline-block;
        }

        .screenshot-toggle.expanded::before {
            transform: rotate(90deg);
        }

        .screenshot-content {
            display: none;
            padding: 8px;
        }

        .screenshot-content.expanded {
            display: block;
        }

        .screenshot-image {
            width: 100%;
            max-width: 300px;
            height: auto;
            max-height: 200px;
            object-fit: contain;
            border: 2px solid var(--panel-border);
            border-radius: 4px;
            margin: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .screenshot-image:hover {
            border-color: var(--aqua-bright);
            box-shadow: 0 0 12px rgba(44, 166, 217, 0.4);
            transform: scale(1.02);
        }

        .screenshot-unavailable {
            padding: 12px;
            text-align: center;
            color: var(--text-muted);
            font-size: 11px;
            font-style: italic;
        }
        
        .footer {
            background: var(--navy-deepest);
            border-top: 1px solid var(--aqua-bright);
            padding: 12px 16px;
            margin-top: 12px;
            text-align: center;
            color: var(--text-secondary);
            font-size: 11px;
            border-radius: 0 0 8px 8px;
        }
        
        .terminal-cursor {
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            50% { opacity: 0; }
        }
        
        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr 1fr;
            }
        }
        
        @media (max-width: 800px) {
            .main-grid {
                grid-template-columns: 1fr;
                height: auto;
            }
            .data-grid {
                grid-template-columns: 1fr;
            }
            .stats-row {
                grid-template-columns: repeat(2, 1fr);
            }
            .screenshot-image {
                max-width: 100%;
                max-height: 150px;
            }
        }
    </style>
    <script>
        function toggleMap(button, vesselId) {
            const mapContainer = document.getElementById('map-' + vesselId);
            const isExpanded = mapContainer.classList.contains('expanded');
            
            if (isExpanded) {
                mapContainer.classList.remove('expanded');
                button.classList.remove('expanded');
                button.innerHTML = '▶ TRACK VISUALIZATION';
            } else {
                mapContainer.classList.add('expanded');
                button.classList.add('expanded');
                button.innerHTML = '▼ TRACK VISUALIZATION';
            }
        }
        
        function toggleScreenshots(button, vesselId, sourceIndex) {
            const contentId = 'screenshot-content-' + vesselId + '_' + sourceIndex;
            const content = document.getElementById(contentId);
            const isExpanded = content.classList.contains('expanded');
            
            if (isExpanded) {
                content.classList.remove('expanded');
                button.classList.remove('expanded');
            } else {
                content.classList.add('expanded');
                button.classList.add('expanded');
            }
        }
        
        function showPhotoModal(src, title) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(21, 35, 47, 0.85); z-index: 1000; display: flex;
                justify-content: center; align-items: center; cursor: pointer;
                backdrop-filter: blur(4px);
            `;
            
            const img = document.createElement('img');
            img.src = src;
            img.style.cssText = `
                max-width: 95%; max-height: 95%; border: 3px solid #2CA6D9;
                border-radius: 8px; box-shadow: 0 8px 32px rgba(44, 166, 217, 0.3);
            `;
            
            modal.onclick = () => document.body.removeChild(modal);
            modal.appendChild(img);
            document.body.appendChild(modal);
        }
        
        function showTab(tabId) {
            let vessel_mmsi = '';
            if (tabId.toString().includes('_')) {
                vessel_mmsi = tabId.toString().split('_')[0];
            }
            
            if (vessel_mmsi) {
                document.querySelectorAll(`[id^="tab-${vessel_mmsi}_"]`).forEach(tab => {
                    tab.style.display = 'none';
                });
                document.querySelectorAll(`[onclick*="${vessel_mmsi}_"]`).forEach(btn => {
                    btn.classList.remove('active');
                });
            } else {
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.style.display = 'none';
                });
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
            }
            
            document.getElementById('tab-' + tabId).style.display = 'block';
            document.querySelector(`[onclick*="${tabId}"]`).classList.add('active');
        }
        
        window.onload = function() {
            document.querySelectorAll('.vessel-block').forEach((block, i) => {
                block.style.opacity = '0';
                setTimeout(() => {
                    block.style.transition = 'opacity 0.3s';
                    block.style.opacity = '1';
                }, i * 100);
            });
        };
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MARITIME CONTROL SYSTEM</h1>
            <div class="status">
                ACTIVE TRACKING | {{ vessels|length }} VESSELS | AIS DATA: 2022-01-01 | STATUS: OPERATIONAL<span class="terminal-cursor">█</span>
            </div>
        </div>

        <div class="main-grid">
            <div class="column">
                <div class="column-header">VESSEL IDENTIFICATION & SPECIFICATIONS</div>
                {% for vessel in vessels %}
                <div class="vessel-block">
                    <div class="vessel-header">
                        <span class="vessel-name">{{ vessel.vessel_name }}</span>
                        <span class="vessel-status">TRACKED</span>
                    </div>
                    
                    <div class="data-grid">
                        <div class="data-item">
                            <span class="data-label">MMSI</span>
                            <span class="data-value">{{ vessel.mmsi }}</span>
                        </div>
                        {% if vessel.imo and vessel.imo != "IMO0000000" %}
                        <div class="data-item">
                            <span class="data-label">IMO</span>
                            <span class="data-value">{{ vessel.imo }}</span>
                        </div>
                        {% endif %}
                        {% if vessel.call_sign %}
                        <div class="data-item">
                            <span class="data-label">CALL SIGN</span>
                            <span class="data-value">{{ vessel.call_sign }}</span>
                        </div>
                        {% endif %}
                        {% if vessel.vessel_type %}
                        <div class="data-item">
                            <span class="data-label">TYPE</span>
                            <span class="data-value">{{ vessel.vessel_type }}</span>
                        </div>
                        {% endif %}
                        {% if vessel.length %}
                        <div class="data-item">
                            <span class="data-label">LENGTH</span>
                            <span class="data-value">{{ vessel.length }}M</span>
                        </div>
                        {% endif %}
                        {% if vessel.width %}
                        <div class="data-item">
                            <span class="data-label">BEAM</span>
                            <span class="data-value">{{ vessel.width }}M</span>
                        </div>
                        {% endif %}
                        {% if vessel.draft %}
                        <div class="data-item">
                            <span class="data-label">DRAFT</span>
                            <span class="data-value">{{ vessel.draft }}M</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="column">
                <div class="column-header">TRACKING DATA & PERFORMANCE</div>
                {% for vessel in vessels %}
                <div class="vessel-block">
                    <div class="vessel-header">
                        <span class="vessel-name">{{ vessel.vessel_name }}</span>
                        <span class="vessel-status">{{ "%.1f"|format(vessel.total_distance_miles) }}MI</span>
                    </div>
                    
                    <div class="stats-row">
                        <div class="stat-box">
                            <span class="stat-number">{{ vessel.track_points|length }}</span>
                            <span class="stat-label">POINTS</span>
                        </div>
                        <div class="stat-box">
                            <span class="stat-number">{{ "%.0f"|format(vessel.total_distance_miles) }}</span>
                            <span class="stat-label">MILES</span>
                        </div>
                        <div class="stat-box">
                            <span class="stat-number">{{ vessel_max_speeds[loop.index0] }}</span>
                            <span class="stat-label">MAX KT</span>
                        </div>
                        <div class="stat-box">
                            <span class="stat-number">24</span>
                            <span class="stat-label">HOURS</span>
                        </div>
                    </div>
                    
                    <button class="map-toggle" onclick="toggleMap(this, '{{ vessel.mmsi }}')">
                        ▶ TRACK VISUALIZATION
                    </button>
                    <div class="map-container" id="map-{{ vessel.mmsi }}">
                        {{ vessel_maps[loop.index0]|safe }}
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="column">
                <div class="column-header">INTELLIGENCE & IMAGERY</div>
                {% for vessel in vessels %}
                <div class="vessel-block">
                    <div class="vessel-header">
                        <span class="vessel-name">{{ vessel.vessel_name }}</span>
                        <span class="vessel-status">{% if vessel_photos[loop.index0] %}IMG{% else %}NO-IMG{% endif %}</span>
                    </div>
                    
                    {% if vessel_photos[loop.index0] %}
                    <div class="photos-compact">
                        {% for photo in vessel_photos[loop.index0] %}
                        <img src="{{ photo }}" alt="Vessel" class="photo-thumb" 
                             onclick="showPhotoModal('{{ photo }}')" 
                             onerror="this.style.display='none'">
                        {% endfor %}
                    </div>
                    {% endif %}
                    
                    {% set vessel_research = vessel_research_results.get(vessel.mmsi, []) %}
                    {% if not vessel_research and web_research %}
                        {% set vessel_research = web_research %}
                    {% endif %}
                    
                    {% if vessel_research %}
                    <div class="research-tabs">
                        <div class="tab-headers">
                            {% for result in vessel_research %}
                            <button class="tab-btn {% if loop.first %}active{% endif %}" 
                                    onclick="showTab({{ vessel.mmsi }}_{{ loop.index }})"
                                    data-status="{{ result.status if result.status else 'unknown' }}">
                                <span>SRC {{ loop.index }}</span>
                                <span class="status-dot status-{{ result.status if result.status else 'unknown' }}"></span>
                            </button>
                            {% endfor %}
                        </div>
                        
                        {% for result in vessel_research %}
                        <div class="tab-content" id="tab-{{ vessel.mmsi }}_{{ loop.index }}" 
                             {% if not loop.first %}style="display:none"{% endif %}>
                            <div class="source-header">
                                <a href="{{ result.url }}" target="_blank" class="source-url">{{ result.title if result.title else result.url[:50] }}</a>
                                <span class="reliability-badge">{{ result.reliability if result.reliability else 'PENDING' }}</span>
                            </div>
                            
                            <div class="screenshot-container">
                                <button class="screenshot-toggle" onclick="toggleScreenshots(this, {{ vessel.mmsi }}, {{ loop.index }})">
                                    SCREENSHOTS - {{ vessel.vessel_name }} ({{ vessel.mmsi }})
                                </button>
                                <div class="screenshot-content" id="screenshot-content-{{ vessel.mmsi }}_{{ loop.index }}">
                                    {% set screenshot_path = 'search_results/' + vessel.mmsi|string + '/screenshot_' + loop.index|string + '.jpg' %}
                                    <img src="{{ screenshot_path }}" 
                                         alt="Page Screenshot" 
                                         class="screenshot-image" 
                                         onclick="showPhotoModal('{{ screenshot_path }}')"
                                         onerror="this.parentNode.querySelector('.screenshot-unavailable').style.display='block'; this.style.display='none';">
                                    <div class="screenshot-unavailable" style="display:none;">Screenshot failed to load</div>
                                </div>
                            </div>
                            
                            <div class="research-details">
                                <div class="details-header">KEY INFORMATION</div>
                                <ul class="details-list">
                                    {% if result.metadata_extracted and result.metadata_extracted.get('details') %}
                                        {% for detail in result.metadata_extracted.get('details') %}
                                            <li class="detail-item">{{ detail }}</li>
                                        {% endfor %}
                                    {% elif result.metadata_extracted and result.metadata_extracted.get('textContent') %}
                                        {% set content = result.metadata_extracted.get('textContent')[:600] %}
                                        {% set sentences = content.split('.') %}
                                        {% for sentence in sentences[:5] if sentence.strip() %}
                                            <li class="detail-item">{{ sentence.strip() }}{% if not sentence.endswith('.') %}.{% endif %}</li>
                                        {% endfor %}
                                    {% else %}
                                        {% set content = result.content_snippet %}
                                        {% set sentences = content.split('.') %}
                                        {% for sentence in sentences[:4] if sentence.strip() %}
                                            <li class="detail-item">{{ sentence.strip() }}{% if not sentence.endswith('.') %}.{% endif %}</li>
                                        {% endfor %}
                                    {% endif %}
                                </ul>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="footer">
            MARITIME CONTROL SYSTEM v2.1 | VESSEL ANALYSIS AGENT | REAL-TIME AIS PROCESSING | SECURE CONNECTION
        </div>
    </div>
</body>
</html>
        """


# Global report writer instance
report_writer = ReportWriter()