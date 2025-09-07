#!/usr/bin/env python3
"""
Test script for the optimized geohash-based vessel track analysis.

This script demonstrates the new search_vessels_optimized_geohash function
that implements all the specified requirements:
- Geohash grid aggregation with precision 5 (~4.9km x 4.9km cells)
- MMSI grouping with terms aggregation (size: 1000)  
- Representative points via top_hits sorted by BaseDateTime
- Minimal data retrieval (BaseDateTime, LAT, LON)
- Vessel metadata aggregation
- Scroll API processing (3 batches)
- External Python distance calculation using Haversine formula
- Top 3 longest track vessels
"""

import sys
import time
from typing import List
from tools import search_vessels_optimized_geohash, VesselData


def test_geohash_optimization():
    """Test the optimized geohash vessel search function."""
    print("=" * 80)
    print("TESTING OPTIMIZED GEOHASH VESSEL TRACK ANALYSIS")
    print("=" * 80)
    
    # Test parameters
    min_distance = 50.0
    test_date = "2022-01-01"
    scroll_batches = 3
    
    print(f"\nTest Parameters:")
    print(f"  - Minimum distance: {min_distance} miles")
    print(f"  - Date: {test_date}")
    print(f"  - Scroll batches: {scroll_batches}")
    print(f"  - Geohash precision: 5 (~4.9km x 4.9km cells)")
    print(f"  - Expected result: Top 3 vessels by track length")
    
    start_time = time.time()
    
    try:
        print("\n" + "-" * 60)
        print("EXECUTING GEOHASH OPTIMIZATION QUERY...")
        print("-" * 60)
        
        # Call the new optimized function
        vessels = search_vessels_optimized_geohash(
            min_distance_miles=min_distance,
            date=test_date,
            scroll_batches=scroll_batches
        )
        
        execution_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("RESULTS SUMMARY")
        print("="*60)
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Vessels found: {len(vessels)}")
        
        if vessels:
            print(f"\nTop {len(vessels)} Vessels by Track Length:")
            print("-" * 50)
            
            for i, vessel in enumerate(vessels, 1):
                print(f"{i}. {vessel.vessel_name or 'Unknown'} (MMSI: {vessel.mmsi})")
                print(f"   Track Length: {vessel.total_distance_miles:.1f} miles")
                print(f"   Track Points: {len(vessel.track_points)}")
                print(f"   Vessel Type: {vessel.vessel_type or 'Unknown'}")
                if vessel.length:
                    print(f"   Length: {vessel.length}m")
                print()
        else:
            print("No vessels found matching the criteria.")
            
        # Validate results meet requirements
        print("REQUIREMENT VALIDATION:")
        print("-" * 30)
        
        checks = [
            ("Returns top 3 vessels", len(vessels) <= 3),
            ("All vessels meet min distance", all(v.total_distance_miles >= min_distance for v in vessels)),
            ("Results sorted by distance", all(vessels[i].total_distance_miles >= vessels[i+1].total_distance_miles 
                                             for i in range(len(vessels)-1)) if len(vessels) > 1 else True),
            ("Track points contain required fields", all(
                all(key in point for key in ["timestamp", "lat", "lon"]) 
                for vessel in vessels for point in vessel.track_points
            ) if vessels else True),
        ]
        
        for check_name, passed in checks:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}: {check_name}")
            
        return vessels
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Execution failed after {time.time() - start_time:.2f} seconds")
        return []


def compare_with_original():
    """Compare performance and results with original function."""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    
    from tools import search_vessels_by_distance
    
    min_distance = 50.0
    test_date = "2022-01-01"
    
    # Test original function
    print("\nTesting original search_vessels_by_distance...")
    start_time = time.time()
    try:
        original_vessels = search_vessels_by_distance(min_distance, test_date)
        original_time = time.time() - start_time
        print(f"Original function: {len(original_vessels)} vessels in {original_time:.2f}s")
    except Exception as e:
        print(f"Original function failed: {e}")
        original_vessels = []
        original_time = 0
    
    # Test optimized function  
    print("\nTesting optimized search_vessels_optimized_geohash...")
    start_time = time.time()
    try:
        optimized_vessels = search_vessels_optimized_geohash(min_distance, test_date)
        optimized_time = time.time() - start_time
        print(f"Optimized function: {len(optimized_vessels)} vessels in {optimized_time:.2f}s")
    except Exception as e:
        print(f"Optimized function failed: {e}")
        optimized_vessels = []
        optimized_time = 0
    
    # Compare results
    if original_time > 0 and optimized_time > 0:
        speedup = original_time / optimized_time
        print(f"\nPerformance improvement: {speedup:.2f}x faster")
        
        # Find common vessels
        original_mmsis = {v.mmsi for v in original_vessels}
        optimized_mmsis = {v.mmsi for v in optimized_vessels}
        common = original_mmsis.intersection(optimized_mmsis)
        
        print(f"Common vessels found: {len(common)}")
        print(f"Original unique: {len(original_mmsis - optimized_mmsis)}")
        print(f"Optimized unique: {len(optimized_mmsis - original_mmsis)}")


def analyze_query_structure():
    """Analyze and document the query structure."""
    print("\n" + "=" * 80)
    print("ELASTICSEARCH QUERY ANALYSIS")  
    print("=" * 80)
    
    print("""
OPTIMIZED GEOHASH QUERY STRUCTURE:
==================================

1. Range Query Filter:
   - Field: BaseDateTime
   - Range: Full day (00:00:00 to 23:59:59)
   
2. Terms Aggregation:
   - Field: MMSI.keyword
   - Size: 1000 vessels per batch
   - Purpose: Group by vessel MMSI
   
3. Nested Aggregations per Vessel:
   
   a) vessel_info (top_hits):
      - Size: 1 document
      - Purpose: Get vessel metadata
      - Fields: VesselName, IMO, CallSign, VesselType, Length, Width, Draft
      
   b) geohash_grid:
      - Field: location (fallback to LAT)
      - Precision: 5 (~4.9km x 4.9km cells)
      - Purpose: Spatial clustering of track points
      
      Nested in geohash_grid:
      - representative_point (top_hits):
        - Size: 1 per cell
        - Sort: BaseDateTime ASC (earliest point in cell)
        - Fields: BaseDateTime, LAT, LON

4. Scroll API Processing:
   - Batches: 3 (configurable)
   - Scroll timeout: 2 minutes
   - Purpose: Handle large datasets efficiently
   
5. External Distance Calculation:
   - Algorithm: Haversine formula
   - Input: Representative points from geohash cells
   - Purpose: Accurate great-circle distance calculation
   
6. Result Processing:
   - Filter: >= minimum distance threshold
   - Sort: By total distance (descending)
   - Return: Top 3 vessels

BENEFITS:
=========
- Reduced data transfer (one point per geohash cell)
- No Elasticsearch scripting (better performance)
- Scalable processing via scroll API
- Accurate distance calculation in Python
- Spatial clustering reduces noise in track data
""")


if __name__ == "__main__":
    print("Geohash Optimization Test Suite")
    print("Ensure Elasticsearch is running on localhost:9200 with vessel_index")
    
    # Run main test
    vessels = test_geohash_optimization()
    
    # Analyze query structure
    analyze_query_structure()
    
    # Optional performance comparison
    if "--compare" in sys.argv:
        compare_with_original()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)