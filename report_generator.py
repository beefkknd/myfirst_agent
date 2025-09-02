import os

import folium
from folium import plugins
from jinja2 import Template

from models import VesselData, AnalysisState


class VesselReportGenerator:
    def __init__(self):
        self.report_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vessel Analysis Report: {{ vessel.vessel_name }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .vessel-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .info-card {
            background: #f8f9fa;
            border-left: 4px solid #2a5298;
            padding: 20px;
            border-radius: 5px;
        }
        .distance-highlight {
            background: #e8f5e8;
            border: 2px solid #28a745;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
        }
        .map-container {
            margin: 30px 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .photos-section {
            margin: 30px 0;
        }
        .photo-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .photo-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .research-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
        }
        .source-link {
            color: #2a5298;
            text-decoration: none;
            font-weight: 500;
        }
        .source-link:hover {
            text-decoration: underline;
        }
        .track-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #2a5298;
        }
        .stat-label {
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ vessel.vessel_name }}</h1>
        <p>Comprehensive Vessel Analysis Report</p>
        <p><strong>Analysis Date:</strong> January 1, 2022</p>
    </div>

    <div class="distance-highlight">
        <h2>🚢 Total Distance Traveled: {{ "%.1f"|format(vessel.total_distance_miles) }} miles</h2>
        <p>This vessel covered an exceptional distance in a single day, ranking among the longest journeys observed.</p>
    </div>

    <div class="vessel-info">
        <div class="info-card">
            <h3>🏷️ Vessel Identification</h3>
            <p><strong>Name:</strong> {{ vessel.vessel_name }}</p>
            <p><strong>MMSI:</strong> {{ vessel.mmsi }}</p>
            {% if vessel.imo and vessel.imo != "IMO0000000" %}
            <p><strong>IMO:</strong> {{ vessel.imo }}</p>
            {% endif %}
            {% if vessel.call_sign %}
            <p><strong>Call Sign:</strong> {{ vessel.call_sign }}</p>
            {% endif %}
            {% if vessel.vessel_type %}
            <p><strong>Vessel Type:</strong> {{ vessel.vessel_type }}</p>
            {% endif %}
        </div>

        <div class="info-card">
            <h3>📏 Physical Specifications</h3>
            {% if vessel.length %}
            <p><strong>Length:</strong> {{ vessel.length }}m</p>
            {% endif %}
            {% if vessel.width %}
            <p><strong>Width:</strong> {{ vessel.width }}m</p>
            {% endif %}
            {% if vessel.draft %}
            <p><strong>Draft:</strong> {{ vessel.draft }}m</p>
            {% endif %}
        </div>
    </div>

    <div class="track-stats">
        <div class="stat-item">
            <div class="stat-number">{{ track_points|length }}</div>
            <div class="stat-label">Track Points</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">{{ "%.1f"|format(vessel.total_distance_miles) }}</div>
            <div class="stat-label">Miles Traveled</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">{{ max_speed }}</div>
            <div class="stat-label">Max Speed (knots)</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">24</div>
            <div class="stat-label">Hours Tracked</div>
        </div>
    </div>

    <div class="map-container">
        <h2>🗺️ Vessel Track Visualization</h2>
        {{ map_html|safe }}
    </div>

    {% if photos %}
    <div class="photos-section">
        <h2>📷 Vessel Photographs</h2>
        <div class="photo-grid">
            {% for photo in photos %}
            <div class="photo-item">
                <img src="{{ photo }}" alt="Vessel photograph" onerror="this.style.display='none'">
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    {% if web_research %}
    <div class="research-section">
        <h2>🔍 Research Findings</h2>
        {% for result in web_research %}
        <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px;">
            <h4><a href="{{ result.url }}" class="source-link" target="_blank">{{ result.title or result.url }}</a></h4>
            <p>{{ result.content_snippet[:300] }}...</p>
            {% if result.images_found %}
            <p><strong>Images found:</strong> {{ result.images_found|length }} vessel images</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div style="margin-top: 50px; padding: 20px; background: #f8f9fa; border-radius: 10px; text-align: center;">
        <p><em>Report generated by Vessel Analysis Agent</em></p>
        <p>Data source: AIS tracking data for January 1, 2022</p>
    </div>
</body>
</html>
        """

    def create_vessel_map(self, vessel: VesselData) -> str:
        """Create Folium map for vessel track."""
        if not vessel.track_points:
            return "<p>No track data available</p>"

        # Calculate map center
        lats = [point["lat"] for point in vessel.track_points]
        lons = [point["lon"] for point in vessel.track_points]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles="OpenStreetMap"
        )

        # Add track line
        track_coords = [[point["lat"], point["lon"]] for point in vessel.track_points]
        folium.PolyLine(
            locations=track_coords,
            color="blue",
            weight=3,
            opacity=0.8,
            popup=f"{vessel.vessel_name} Track"
        ).add_to(m)

        # Add start point (green)
        if len(vessel.track_points) > 0:
            start_point = vessel.track_points[0]
            folium.Marker(
                [start_point["lat"], start_point["lon"]],
                popup=f"Start: {start_point['timestamp']}",
                icon=folium.Icon(color="green", icon="play")
            ).add_to(m)

        # Add end point (red)
        if len(vessel.track_points) > 1:
            end_point = vessel.track_points[-1]
            folium.Marker(
                [end_point["lat"], end_point["lon"]],
                popup=f"End: {end_point['timestamp']}",
                icon=folium.Icon(color="red", icon="stop")
            ).add_to(m)

        # Add intermediate points (every 10th point for clarity)
        for i in range(0, len(vessel.track_points), max(1, len(vessel.track_points) // 10)):
            point = vessel.track_points[i]
            folium.CircleMarker(
                [point["lat"], point["lon"]],
                radius=4,
                popup=f"Time: {point['timestamp']}<br>Speed: {point.get('sog', 0)} knots",
                color="orange",
                fillColor="orange",
                fillOpacity=0.7
            ).add_to(m)

        # Add heatmap plugin for density
        heat_data = [[point["lat"], point["lon"]] for point in vessel.track_points]
        plugins.HeatMap(heat_data, radius=15, blur=10, gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1: 'red'}).add_to(m)

        # Fit map to track bounds
        sw = [min(lats), min(lons)]
        ne = [max(lats), max(lons)]
        m.fit_bounds([sw, ne], padding=(20, 20))

        return m._repr_html_()

    def generate_report(self, state: AnalysisState) -> str:
        """Generate complete HTML report."""
        if not state.selected_vessels:
            return "<html><body><h1>No vessels found</h1></body></html>"

        vessel = state.selected_vessels[0]  # Use first vessel for detailed report
        
        # Create map
        map_html = self.create_vessel_map(vessel)

        # Calculate max speed
        max_speed = 0
        if vessel.track_points:
            max_speed = max([point.get("sog", 0) for point in vessel.track_points])

        # Collect photos from web research
        photos = []
        for result in state.web_research_results:
            photos.extend(result.images_found[:2])  # Max 2 photos per source
        photos = photos[:3]  # Max 3 photos total

        # Render template
        template = Template(self.report_template)
        html_content = template.render(
            vessel=vessel,
            track_points=vessel.track_points,
            max_speed=max_speed,
            map_html=map_html,
            photos=photos,
            web_research=state.web_research_results
        )

        # Save report
        os.makedirs("reports", exist_ok=True)
        report_filename = f"reports/vessel_report_{vessel.mmsi}_{vessel.vessel_name.replace(' ', '_')}.html"
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        return report_filename