# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **prompt-driven vessel analysis system** using LangChain/LangGraph that generates comprehensive vessel reports. The system analyzes vessel tracks from Elasticsearch, conducts web research via MCP Chrome bridge, and produces interactive HTML reports with Folium maps. Users define analysis preferences in structured prompt files.

## Architecture

**Core Components**:
- **vessel_agent.py**: Main LangGraph multi-agent system with Ollama Qwen3:8b for LLM-driven workflow orchestration
- **models.py**: Pydantic models for structured prompt parsing and state management
- **tools.py**: Vessel search, distance calculation, and intelligent MCP Chrome bridge navigation
- **report_generator.py**: HTML report generation with embedded Folium maps and Jinja2 templates

**LLM-Driven Dynamic Workflow**:
1. `parse_and_plan` → LLM unpacks user prompt and plans task sequence
2. `fetch_tracks` → Query Elasticsearch based on LLM-parsed criteria
3. `assess_vessels` → LLM selects most interesting vessel for research
4. `intelligent_research` → LLM-driven browser navigation focusing on best first result
5. `evaluate_information` → LLM assesses information sufficiency (may loop back)
6. `write_report` → Generate HTML report with LLM-analyzed content
7. `quality_review` → LLM validates report completeness

**Decision Points**: LLM determines state transitions, information sufficiency, and research continuation

**Data Models**:
- `AnalysisPrompt`: Structured prompt configuration
- `VesselData`: Track points with distance calculations using Haversine formula
- `WebSearchResult`: Research findings with extracted images and metadata
- `AnalysisState`: Complete workflow state management

## Development Commands

**Environment Setup**:
```bash
# Install dependencies
pip install -r requirements.txt

# Start Elasticsearch and Kibana
docker-compose up -d

# Import vessel data (AIS_2022_01_01.csv)
python import_data.py
```

**Running the Agent**:
```bash
# Run with Ollama Qwen3:8b (default)
python vessel_agent.py --model ollama

# Run with Ollama (Gemini currently disabled, falls back to Ollama)
python vessel_agent.py --model gemini

# Use specific prompt file
python vessel_agent.py --prompt prompts/prompt1.md

# List available prompts
python vessel_agent.py --list-prompts
```

**Utility Commands**:
```bash
# Test model availability
python list_models.py

# Legacy simple agent
python main.py
```

## Key Features

**Distance Analysis**: 
- Haversine formula for accurate great circle distance calculation
- Filters vessels with 50+ mile tracks from 2022-01-01 dataset
- Ranks by total distance traveled

**Intelligent Web Research**:
- LLM-driven MCP Chrome bridge for smart browser navigation
- LLM analyzes search results and selects most promising first result
- Evaluates page content quality and decides if additional research needed
- Extracts vessel specifications, operational context, and images from optimal sources

**Report Generation**:
- Interactive Folium maps with track visualization, start/end markers
- Responsive HTML layout with vessel specifications and photos
- Embedded heatmaps showing vessel density patterns
- Statistical summaries (track points, distance, max speed)

## Configuration

**Model Selection**: CLI argument `--model` (currently only ollama/qwen3:8b supported)
**Environment Variables**: `GOOGLE_API_KEY` for potential Gemini access (currently disabled)
**Prompt Structure**: YAML-like markdown in `prompts/` directory
**Output Directory**: Reports saved to `reports/` with images in `reports/images/`

## Data Sources

- **Elasticsearch Index**: `vessel_index` on localhost:9200
- **AIS Data**: January 1, 2022 (24-hour dataset)
- **Web Sources**: Automated research via MCP Chrome bridge
- **Maps**: OpenStreetMap tiles via Folium