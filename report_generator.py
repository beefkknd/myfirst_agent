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
        
        .research-compact {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            padding: 12px;
            margin: 8px 0;
            border-left: 3px solid var(--warning);
            border-radius: 6px;
        }
        
        .research-title {
            color: var(--warning);
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 6px;
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

        /* Enhanced tabbed interface for multiple research results */
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

        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 6px;
            padding: 8px 0;
            background: var(--navy-darker);
            margin-bottom: 8px;
        }

        .metadata-item {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            padding: 6px 8px;
            border-left: 2px solid var(--aqua-bright);
            border-radius: 4px;
        }

        .metadata-label {
            color: var(--aqua-bright);
            font-size: 9px;
            font-weight: 600;
            display: block;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .metadata-value {
            color: var(--text-primary);
            font-size: 10px;
            font-weight: 500;
            display: block;
            margin-top: 2px;
        }

        /* Screenshot display styling */
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

        .screenshot-label {
            background: var(--navy-deepest);
            color: var(--warning);
            padding: 6px 12px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--panel-border);
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
        
        .scrollbar-custom::-webkit-scrollbar {
            width: 8px;
        }
        
        .scrollbar-custom::-webkit-scrollbar-track {
            background: var(--navy-darker);
        }
        
        .scrollbar-custom::-webkit-scrollbar-thumb {
            background: var(--panel-border);
            border-radius: 4px;
        }
        
        .scrollbar-custom::-webkit-scrollbar-thumb:hover {
            background: var(--aqua-bright);
        }
        
        .column {
            scrollbar-width: thin;
            scrollbar-color: var(--panel-border) var(--navy-darker);
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
            .metadata-grid {
                grid-template-columns: 1fr;
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
                animation: fadeIn 0.3s ease-out;
            `;
            
            const modalContent = document.createElement('div');
            modalContent.style.cssText = `
                max-width: 95%; max-height: 95%; display: flex; flex-direction: column;
                align-items: center;
            `;
            
            // Add title if provided
            if (title) {
                const titleDiv = document.createElement('div');
                titleDiv.style.cssText = `
                    color: #2CA6D9; font-size: 16px; font-weight: 600;
                    margin-bottom: 12px; text-align: center;
                    text-shadow: 0 0 8px rgba(44, 166, 217, 0.4);
                `;
                titleDiv.textContent = title;
                modalContent.appendChild(titleDiv);
            }
            
            const img = document.createElement('img');
            img.src = src;
            img.style.cssText = `
                max-width: 100%; max-height: 85%; border: 3px solid #2CA6D9;
                border-radius: 8px; box-shadow: 0 8px 32px rgba(44, 166, 217, 0.3);
                animation: scaleIn 0.3s ease-out; cursor: default;
            `;
            
            const closeButton = document.createElement('div');
            closeButton.style.cssText = `
                position: absolute; top: 20px; right: 25px; color: #2CA6D9;
                font-size: 28px; font-weight: bold; cursor: pointer;
                background: rgba(21, 35, 47, 0.8); border: 2px solid #2CA6D9;
                border-radius: 50%; width: 40px; height: 40px;
                display: flex; align-items: center; justify-content: center;
                transition: all 0.2s ease;
            `;
            closeButton.innerHTML = '×';
            closeButton.onmouseover = () => {
                closeButton.style.background = 'rgba(44, 166, 217, 0.2)';
                closeButton.style.transform = 'scale(1.1)';
            };
            closeButton.onmouseout = () => {
                closeButton.style.background = 'rgba(21, 35, 47, 0.8)';
                closeButton.style.transform = 'scale(1)';
            };
            
            modalContent.appendChild(img);
            modalContent.onclick = (e) => e.stopPropagation();
            closeButton.onclick = () => document.body.removeChild(modal);
            modal.onclick = () => document.body.removeChild(modal);
            
            modal.appendChild(modalContent);
            modal.appendChild(closeButton);
            document.body.appendChild(modal);
            
            // Add CSS animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes scaleIn {
                    from { transform: scale(0.9); }
                    to { transform: scale(1); }
                }
            `;
            if (!document.querySelector('style[data-modal-animations]')) {
                style.setAttribute('data-modal-animations', 'true');
                document.head.appendChild(style);
            }
        }
        
        function showTab(tabId) {
            // Parse vessel MMSI from tab ID if it contains underscore
            let vessel_mmsi = '';
            if (tabId.toString().includes('_')) {
                vessel_mmsi = tabId.toString().split('_')[0];
            }
            
            // Hide all tabs for the same vessel (same MMSI prefix)
            if (vessel_mmsi) {
                document.querySelectorAll(`[id^="tab-${vessel_mmsi}_"]`).forEach(tab => {
                    tab.style.display = 'none';
                });
                // Remove active class from all buttons for this vessel
                document.querySelectorAll(`[onclick*="${vessel_mmsi}_"]`).forEach(btn => {
                    btn.classList.remove('active');
                });
            } else {
                // Fallback for legacy single-vessel format
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.style.display = 'none';
                });
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
            }
            
            // Show selected tab and mark button as active
            document.getElementById('tab-' + tabId).style.display = 'block';
            document.querySelector(`[onclick*="${tabId}"]`).classList.add('active');
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
                                <span class="source-indicator">SRC {{ loop.index }}</span>
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
                            
                            {% if result.metadata_extracted and result.metadata_extracted != result.content_snippet %}
                            <div class="metadata-grid">
                                {% set metadata = result.metadata_extracted %}
                                {% if metadata and metadata != 'error' %}
                                    {% for key, value in metadata.items() if value and key not in ['status', 'reliability', 'screenshot_path', 'content_file'] %}
                                    <div class="metadata-item">
                                        <span class="metadata-label">{{ key.replace('_', ' ').upper() }}</span>
                                        <span class="metadata-value">{{ value }}</span>
                                    </div>
                                    {% endfor %}
                                {% endif %}
                            </div>
                            {% endif %}
                            
                            <!-- Screenshot Display Section -->
                            <div class="screenshot-container">
                                <button class="screenshot-toggle" onclick="toggleScreenshots(this, {{ vessel.mmsi }}, {{ loop.index }})">
                                    SCREENSHOTS - {{ vessel.vessel_name }} ({{ vessel.mmsi }})
                                </button>
                                <div class="screenshot-content" id="screenshot-content-{{ vessel.mmsi }}_{{ loop.index }}">
                                    {% set screenshot_path = 'search_results/' + vessel.mmsi|string + '/screenshot_' + loop.index|string + '.jpg' %}
                                    <img src="{{ screenshot_path }}" 
                                         alt="Page Screenshot" 
                                         class="screenshot-image" 
                                         onclick="showPhotoModal('{{ screenshot_path }}', '{{ vessel.vessel_name }} ({{ vessel.mmsi }}) - Screenshot {{ loop.index }}')"
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

        # Add track line with ocean-inspired colors
        track_coords = [[point["lat"], point["lon"]] for point in vessel.track_points]
        folium.PolyLine(
            locations=track_coords,
            color="#4a90e2",  # Ocean blue
            weight=4,
            opacity=0.9,
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
                radius=5,
                popup=f"Time: {point['timestamp']}<br>Speed: {point.get('sog', 0)} knots",
                color="#2c9aa0",  # Ocean teal
                fillColor="#60a5fa",  # Ocean bright
                fillOpacity=0.8
            ).add_to(m)

        # Add heatmap plugin with ocean-inspired gradient
        heat_data = [[point["lat"], point["lon"]] for point in vessel.track_points]
        plugins.HeatMap(
            heat_data, 
            radius=15, 
            blur=12, 
            gradient={0.2: '#2c9aa0', 0.4: '#4a90e2', 0.6: '#60a5fa', 1: '#06b6d4'}
        ).add_to(m)

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
            
            # Collect photos for this vessel using vessel-specific research results
            photos = []
            vessel_research = state.vessel_research_results.get(vessel.mmsi, [])
            if not vessel_research and state.web_research_results:  # Fallback for backward compatibility
                vessel_research = state.web_research_results
            
            for result in vessel_research:
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
            web_research=state.web_research_results,  # Keep for backward compatibility
            vessel_research_results=state.vessel_research_results  # New vessel-specific research data
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