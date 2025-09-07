# Prototype Directory

This directory contains experimental code, prototypes, and development utilities that are not part of the main application.

## Files Overview

### **Legacy/Experimental**
- `main.py` - Original simple agent implementation (superseded by vessel_agent.py)
- `update_report_final*.py` - Report generation experiments
- `debug_mcp.py` - MCP debugging utilities
- `browser_mcp_test.py` - Browser automation testing
- `test_mcp_client.py` - MCP client testing
- `test_intelligent_search.py` - Search algorithm testing

### **Utilities**
- `import_data.py` - Elasticsearch data import utility
- `list_models.py` - LLM model listing utility  
- `example_geohash_usage.py` - Geohash implementation examples

## Usage

These files are kept for reference and experimentation. They may have dependencies on older versions of the codebase or experimental features.

```bash
# Example: Run data import utility
python prototype/import_data.py

# Example: List available models
python prototype/list_models.py
```

**Note**: These files may not be actively maintained and could require updates to work with the current modular architecture.