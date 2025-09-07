# Tests Directory

This directory contains unit tests and integration tests for the vessel analysis system.

## Test Files

- `test_elements.py` - Tests for HTML element parsing
- `test_geohash_optimization.py` - Tests for geohash-based vessel search optimization  
- `my_elements_test.py` - Additional element parsing tests

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_elements.py

# Run with verbose output
python -m pytest tests/ -v
```

## Test Requirements

Make sure Elasticsearch is running locally on port 9200 for integration tests that require database access.