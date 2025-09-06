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
    <title>MARITIME CONTROL SYSTEM - {{ vessels|length }} Vessel(s) Analysis</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #0a0e1a;
            color: #00ff88;
            line-height: 1.2;
            font-size: 13px;
            overflow-x: auto;
        }
        
        .container {
            max-width: 100vw;
            padding: 8px;
        }
        
        .header {
            background: linear-gradient(90deg, #001122 0%, #003344 50%, #001122 100%);
            border: 1px solid #00ff88;
            padding: 8px 12px;
            margin-bottom: 8px;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0,255,136,0.1), transparent);
            animation: scan 3s linear infinite;
        }
        
        @keyframes scan {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .header h1 {
            color: #00ffff;
            font-size: 18px;
            text-shadow: 0 0 10px #00ffff;
            letter-spacing: 2px;
        }
        
        .header .status {
            color: #00ff88;
            font-size: 11px;
            margin-top: 2px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            height: calc(100vh - 80px);
        }
        
        .column {
            background: #0f1419;
            border: 1px solid #334155;
            overflow-y: auto;
        }
        
        .column-header {
            background: #1e293b;
            border-bottom: 1px solid #00ff88;
            padding: 6px 8px;
            color: #00ffff;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .vessel-block {
            border-bottom: 1px solid #334155;
            padding: 8px;
            margin-bottom: 4px;
            position: relative;
        }
        
        .vessel-block:hover {
            background: #1a1f2e;
            border-left: 3px solid #00ff88;
        }
        
        .vessel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 1px solid #334155;
        }
        
        .vessel-name {
            color: #00ffff;
            font-weight: bold;
            font-size: 14px;
            text-shadow: 0 0 5px #00ffff;
        }
        
        .vessel-status {
            color: #00ff88;
            font-size: 10px;
            background: #001a0d;
            padding: 2px 6px;
            border: 1px solid #00ff88;
            border-radius: 2px;
        }
        
        .data-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            margin-bottom: 8px;
        }
        
        .data-item {
            background: #1a1f2e;
            border: 1px solid #334155;
            padding: 4px 6px;
            border-left: 2px solid #00ff88;
        }
        
        .data-label {
            color: #94a3b8;
            font-size: 10px;
            display: block;
            text-transform: uppercase;
        }
        
        .data-value {
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
            font-family: 'Courier New', monospace;
        }
        
        .map-toggle {
            background: #001122;
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 4px 8px;
            margin: 4px 0;
            cursor: pointer;
            font-family: 'Consolas', monospace;
            font-size: 11px;
            width: 100%;
            text-align: left;
            position: relative;
            overflow: hidden;
        }
        
        .map-toggle:hover {
            background: #002244;
            box-shadow: 0 0 5px #00ff88;
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
            margin: 4px 0;
            border: 1px solid #334155;
            height: 300px;
            overflow: hidden;
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
            background: #0a0f1a;
            border: 1px solid #334155;
            padding: 4px;
            text-align: center;
            border-left: 2px solid #00ffff;
        }
        
        .stat-number {
            color: #00ffff;
            font-weight: bold;
            font-size: 14px;
            display: block;
            text-shadow: 0 0 3px #00ffff;
        }
        
        .stat-label {
            color: #94a3b8;
            font-size: 9px;
            text-transform: uppercase;
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
            border: 1px solid #334155;
            cursor: pointer;
        }
        
        .photo-thumb:hover {
            border-color: #00ff88;
            box-shadow: 0 0 5px #00ff88;
        }
        
        .research-compact {
            background: #1a1f2e;
            border: 1px solid #334155;
            padding: 6px;
            margin: 4px 0;
            border-left: 2px solid #ff6600;
        }
        
        .research-title {
            color: #ff6600;
            font-size: 11px;
            font-weight: bold;
            margin-bottom: 2px;
        }
        
        .research-snippet {
            color: #94a3b8;
            font-size: 10px;
            line-height: 1.1;
        }
        
        .footer {
            background: #001122;
            border-top: 1px solid #00ff88;
            padding: 6px 8px;
            margin-top: 8px;
            text-align: center;
            color: #94a3b8;
            font-size: 10px;
        }
        
        .terminal-cursor {
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            50% { opacity: 0; }
        }
        
        .scrollbar-custom::-webkit-scrollbar {
            width: 8px;
        }
        
        .scrollbar-custom::-webkit-scrollbar-track {
            background: #0a0e1a;
        }
        
        .scrollbar-custom::-webkit-scrollbar-thumb {
            background: #334155;
            border-radius: 4px;
        }
        
        .scrollbar-custom::-webkit-scrollbar-thumb:hover {
            background: #00ff88;
        }
        
        .column {
            scrollbar-width: thin;
            scrollbar-color: #334155 #0a0e1a;
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
        
        function showPhotoModal(src) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(0,0,0,0.9); z-index: 1000; display: flex;
                justify-content: center; align-items: center; cursor: pointer;
            `;
            
            const img = document.createElement('img');
            img.src = src;
            img.style.cssText = 'max-width: 90%; max-height: 90%; border: 2px solid #00ff88;';
            
            modal.appendChild(img);
            document.body.appendChild(modal);
            
            modal.onclick = () => document.body.removeChild(modal);
        }
        
        window.onload = function() {
            // Terminal-like startup effect
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
            <div class="column scrollbar-custom">
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

            <div class="column scrollbar-custom">
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

            <div class="column scrollbar-custom">
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
                    
                    {% if web_research %}
                    {% for result in web_research %}
                    <div class="research-compact">
                        <div class="research-title">{{ result.title[:50] }}...</div>
                        <div class="research-snippet">{{ result.content_snippet[:120] }}...</div>
                    </div>
                    {% endfor %}
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
        """Generate complete HTML report for multiple vessels."""
        if not state.selected_vessels:
            return "<html><body><h1>No vessels found</h1></body></html>"

        vessels = state.selected_vessels
        
        # Create maps for all vessels
        vessel_maps = []
        vessel_max_speeds = []
        vessel_photos = []
        
        for vessel in vessels:
            # Create map for this vessel
            map_html = self.create_vessel_map(vessel)
            vessel_maps.append(map_html)
            
            # Calculate max speed for this vessel
            max_speed = 0
            if vessel.track_points:
                max_speed = max([point.get("sog", 0) for point in vessel.track_points])
            vessel_max_speeds.append(max_speed)
            
            # Collect photos for this vessel (for now, all vessels share the same research results)
            photos = []
            for result in state.web_research_results:
                photos.extend(result.images_found[:2])  # Max 2 photos per source
            photos = photos[:3]  # Max 3 photos total
            vessel_photos.append(photos)

        # Render template
        template = Template(self.report_template)
        html_content = template.render(
            vessels=vessels,
            vessel_maps=vessel_maps,
            vessel_max_speeds=vessel_max_speeds,
            vessel_photos=vessel_photos,
            web_research=state.web_research_results
        )

        # Save report
        os.makedirs("reports", exist_ok=True)
        # Use first vessel for filename or create multi-vessel filename
        if len(vessels) == 1:
            report_filename = f"reports/vessel_report_{vessels[0].mmsi}_{vessels[0].vessel_name.replace(' ', '_')}.html"
        else:
            report_filename = f"reports/multi_vessel_report_{len(vessels)}_vessels.html"
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        return report_filename