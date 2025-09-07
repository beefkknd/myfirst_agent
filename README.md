# 🚢 Vessel Analysis Agent

A **prompt-driven multi-agent system** that generates comprehensive vessel analysis reports by combining AIS tracking data with automated web research. Built with LangChain/LangGraph and featuring interactive visualizations.

[View Sample Multi-Vessel Report](https://beefkknd.github.io/myfirst_agent/reports/multi_vessel_report_3_vessels.html)

## 🎯 Overview

This system analyzes vessel movements from Elasticsearch AIS data, conducts automated web research using MCP Chrome bridge, and generates beautiful HTML reports with interactive maps. Perfect for maritime analysis, vessel tracking research, and operational intelligence.

### Key Features

- **🔍 Intelligent Vessel Discovery**: Finds vessels with exceptional travel distances (50+ miles)
- **🌐 Automated Web Research**: Uses MCP Chrome bridge for vessel metadata and image collection
- **🗺️ Interactive Visualizations**: Folium maps with track lines, markers, and heatmaps
- **🤖 Multi-Agent Workflow**: LangGraph state machine with 6-step analysis process
- **📊 Rich HTML Reports**: Professional reports with vessel specs, photos, and route analysis
- **🚢 Multi-Vessel Processing**: Analyzes multiple vessels simultaneously with MMSI-based organization

## 🏗️ Architecture

### Core Components

```
vessel_agent.py      # Main LangGraph agent with Ollama Qwen3:8b
models.py           # Pydantic data models and state management
tools.py            # Elasticsearch queries, distance calculations, MCP integration
report_generator.py # HTML report generation with Folium maps
prompts/            # Structured analysis prompt configurations
```

### Workflow States

1. **parse_prompt** → Extract analysis tasks from structured prompt files
2. **fetch_tracks** → Query Elasticsearch, calculate vessel distances using Haversine formula
3. **internet_search** → Multi-vessel automated browser navigation via MCP Chrome bridge
4. **write_report** → Generate comprehensive HTML report with embedded maps
5. **review_report** → Quality validation and error checking
6. **publish_report** → Finalize and save complete analysis

### Multi-Vessel Processing

The system processes multiple vessels in a single analysis run:
- **Individual Research**: Each vessel gets its own web research session
- **MMSI-Based Organization**: Search results stored in `reports/search_results/{mmsi}/`
- **Parallel Visualization**: All vessels displayed in unified report with individual tabs
- **Error Isolation**: Issues with one vessel don't affect others

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (for Elasticsearch/Kibana)
- **Python 3.8+**
- **Ollama** with Qwen3:8b model
- **Node.js** (for MCP Chrome bridge)

### Installation

1. **Clone and Setup**:
```bash
git clone <repository>
cd myfirst_agent
pip install -r requirements.txt
```

2. **Start Infrastructure**:
```bash
# Start Elasticsearch and Kibana
docker-compose up -d

# Wait for Elasticsearch to be ready (check http://localhost:9200)
```

3. **Import Sample Data**:
```bash
# Import AIS data from January 1, 2022
python import_data.py
```

4. **Install Ollama Model**:
```bash
ollama pull qwen3:8b
```

### Usage

#### Run Analysis

```bash
# Basic analysis with default settings
python vessel_agent.py

# Use specific prompt configuration
python vessel_agent.py --prompt prompts/prompt1.md

# List available prompt configurations
python vessel_agent.py --list-prompts
```

#### Sample Output
```
🚢 Starting Vessel Analysis Agent
==================================================
🔍 Parsing analysis prompt...
🚢 Fetching vessel tracks from Elasticsearch...
Found 3 vessels with long tracks
1. OCEAN INTERVENTION (MMSI: 366614000) - 245.3 miles
2. MSC DANIELA (MMSI: 636019825) - 198.7 miles  
3. MAERSK ESSEX (MMSI: 219018671) - 156.2 miles
🌐 Researching vessels on the internet...
  🔍 Researching OCEAN INTERVENTION (366614000)...
  📁 Search results saved to: reports/search_results/366614000/
  🔍 Researching MSC DANIELA (636019825)...
  📁 Search results saved to: reports/search_results/636019825/
  🔍 Researching MAERSK ESSEX (219018671)...
  📁 Search results saved to: reports/search_results/219018671/
📝 Writing vessel analysis report...
✅ Report generated: reports/vessel_report_366614000_OCEAN_INTERVENTION.html
🎉 ANALYSIS COMPLETE! All 3 vessels processed.
```

## 📋 Prompt Configuration

Create structured prompts in the `prompts/` directory:

```markdown
# Vessel Analysis Prompt: Long Distance Investigation

## Objective
Find vessels with exceptionally long tracks to understand operational patterns.

## Vessel Selection Criteria
- Minimum distance: 100 miles
- Time range: 2022-01-01 (24 hours)
- Priority: Vessels with longest single-day distance

## Web Research Configuration
- Maximum pages to visit: 3
- Extract vessel images: Yes
- Focus on: Ship specifications, operational history

## Report Requirements
- Include Folium map visualization: Yes
- Include vessel photos: Yes (1-3 images)
- Output format: HTML
```

## 📊 Sample Report Features

### Interactive Maps
- **Track Visualization**: Complete vessel route with start/end markers
- **Speed Analysis**: Color-coded segments showing vessel speed
- **Density Heatmaps**: Areas of concentrated vessel activity
- **Interactive Markers**: Clickable points with timestamp and speed data

### Multi-Vessel Intelligence
- **Tabbed Interface**: Each vessel gets its own dedicated tab
- **Individual Research**: Unique web research results for each vessel MMSI
- **Comparative Analysis**: Side-by-side vessel performance metrics
- **MMSI-Based Organization**: Clean separation of vessel-specific data

### Vessel Details (Per Vessel)
- **Identification**: MMSI, IMO, call sign, vessel type
- **Physical Specs**: Length, width, draft measurements
- **Performance Stats**: Distance traveled, max speed, track duration
- **Dedicated Web Research**: Automated collection of vessel-specific photos and metadata

### Professional Layout
- **Responsive Design**: Works on desktop and mobile
- **Rich Typography**: Clean, professional presentation
- **Data Visualization**: Charts and statistics
- **Source Attribution**: Links to research sources with vessel-specific organization

## 🛠️ Development

### Project Structure
```
myfirst_agent/
├── vessel_agent.py         # Main agent entry point
├── models.py              # Pydantic data models
├── tools.py               # Core analysis tools
├── report_generator.py    # HTML report generation
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Infrastructure setup
├── prompts/              # Analysis configurations
│   └── prompt1.md
├── reports/              # Generated reports
│   ├── images/           # Downloaded vessel photos
│   └── search_results/   # Web research by MMSI
│       ├── 366614000/    # OCEAN INTERVENTION research
│       ├── 636019825/    # MSC DANIELA research  
│       └── 219018671/    # MAERSK ESSEX research
└── config/               # MCP configuration
    └── mcp_desktop_config.json
```

### Key Dependencies
- **LangChain/LangGraph**: Multi-agent workflow orchestration
- **Elasticsearch**: AIS data storage and querying
- **Folium**: Interactive map generation
- **Ollama**: Local LLM inference
- **Pydantic**: Data validation and parsing
- **Jinja2**: HTML template rendering

### Data Pipeline
1. **AIS Data Import**: CSV → Elasticsearch with proper field mapping
2. **Distance Calculation**: Haversine formula for great circle distances
3. **Vessel Filtering**: Identify vessels with 50+ mile tracks
4. **Multi-Vessel Web Research**: Individual browser sessions for each vessel with MMSI-based storage
5. **Report Generation**: Combine all vessel data into interactive HTML reports with tabbed interface

## 🔧 Configuration

### Environment Variables
```bash
GOOGLE_API_KEY=your_key_here  # For future Gemini integration (currently disabled)
```

### Elasticsearch Setup
- **Index**: `vessel_index`
- **Port**: localhost:9200
- **Sample Data**: January 1, 2022 AIS tracking (24 hours)
- **Security**: Disabled for local development

### MCP Chrome Bridge
- **Config**: `config/mcp_desktop_config.json`
- **Purpose**: Automated web browsing and content extraction
- **Node Path**: `/opt/homebrew/lib/node_modules/mcp-chrome-bridge/`

## 📈 Performance

### Typical Analysis Times
- **Data Query**: 2-5 seconds (10K+ vessel records)
- **Distance Calculation**: 1-3 seconds per vessel
- **Multi-Vessel Web Research**: 30-60 seconds per vessel (scales with number of vessels)
- **Report Generation**: 5-10 seconds
- **Total Runtime**: ~3-5 minutes for 3-vessel analysis

### Resource Usage
- **Memory**: ~500MB during analysis
- **Storage**: ~10-50MB per report (with images)
- **Network**: Moderate (web research phase)

## 🚨 Troubleshooting

### Common Issues

**Elasticsearch Connection Failed**:
```bash
# Check if Elasticsearch is running
curl http://localhost:9200
# Restart if needed
docker-compose restart elasticsearch
```

**No Vessels Found**:
```bash
# Verify data import
curl "http://localhost:9200/vessel_index/_count"
# Re-import if needed
python import_data.py
```

**MCP Chrome Bridge Issues**:
```bash
# Check Node.js installation
node --version
# Verify MCP installation
ls /opt/homebrew/lib/node_modules/mcp-chrome-bridge/
```

**Ollama Model Issues**:
```bash
# Check available models
ollama list
# Pull required model
ollama pull qwen3:8b
```

## 🤝 Contributing

This is a demonstration system showcasing multi-agent workflows for maritime analysis. Key areas for enhancement:

- **Additional Data Sources**: Real-time AIS feeds, weather data
- **Enhanced Web Research**: Specialized maritime databases
- **Advanced Analytics**: Route optimization, anomaly detection
- **Export Formats**: PDF reports, Excel summaries

## 📄 License

This project is for demonstration and educational purposes.

---

**🚢 Happy Vessel Analysis!** 

For questions or issues, refer to the troubleshooting section or check the logs in your terminal output.