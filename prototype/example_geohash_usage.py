#!/usr/bin/env python3
"""
Example usage of the optimized geohash vessel search functionality.

This demonstrates how to use the new search_vessels_optimized_geohash function
with various parameters and how to process the results.
"""

from tools import search_vessels_optimized_geohash
import json


def example_basic_usage():
    """Basic usage example with default parameters."""
    print("Example 1: Basic Usage")
    print("-" * 30)
    
    # Use default parameters: 50+ mile tracks, Jan 1 2022, 3 scroll batches
    vessels = search_vessels_optimized_geohash()
    
    print(f"Found {len(vessels)} vessels with 50+ mile tracks")
    for vessel in vessels:
        print(f"  - {vessel.vessel_name} (MMSI: {vessel.mmsi}): {vessel.total_distance_miles:.1f} miles")


def example_custom_parameters():
    """Example with custom parameters."""
    print("\nExample 2: Custom Parameters")
    print("-" * 30)
    
    # Search for vessels with 100+ mile tracks, process 2 scroll batches
    vessels = search_vessels_optimized_geohash(
        min_distance_miles=100.0,
        date="2022-01-01", 
        scroll_batches=2
    )
    
    print(f"Found {len(vessels)} vessels with 100+ mile tracks")
    for vessel in vessels:
        print(f"  - {vessel.vessel_name}: {vessel.total_distance_miles:.1f} miles, {len(vessel.track_points)} points")


def example_detailed_analysis():
    """Example showing detailed vessel analysis."""
    print("\nExample 3: Detailed Vessel Analysis")
    print("-" * 30)
    
    vessels = search_vessels_optimized_geohash(min_distance_miles=75.0)
    
    if vessels:
        top_vessel = vessels[0]
        print(f"Top Vessel Analysis: {top_vessel.vessel_name}")
        print(f"  MMSI: {top_vessel.mmsi}")
        print(f"  IMO: {top_vessel.imo}")
        print(f"  Vessel Type: {top_vessel.vessel_type}")
        print(f"  Dimensions: {top_vessel.length}m x {top_vessel.width}m x {top_vessel.draft}m")
        print(f"  Total Distance: {top_vessel.total_distance_miles:.2f} miles")
        print(f"  Track Points: {len(top_vessel.track_points)}")
        
        if top_vessel.track_points:
            first_point = top_vessel.track_points[0]
            last_point = top_vessel.track_points[-1]
            print(f"  Journey: {first_point['timestamp']} to {last_point['timestamp']}")
            print(f"  Start: {first_point['lat']:.4f}, {first_point['lon']:.4f}")
            print(f"  End: {last_point['lat']:.4f}, {last_point['lon']:.4f}")


def example_json_export():
    """Example showing how to export results to JSON."""
    print("\nExample 4: JSON Export")
    print("-" * 30)
    
    vessels = search_vessels_optimized_geohash(min_distance_miles=60.0, scroll_batches=1)
    
    # Convert to JSON-serializable format
    export_data = []
    for vessel in vessels:
        vessel_dict = {
            "mmsi": vessel.mmsi,
            "vessel_name": vessel.vessel_name,
            "imo": vessel.imo,
            "vessel_type": vessel.vessel_type,
            "total_distance_miles": vessel.total_distance_miles,
            "track_point_count": len(vessel.track_points),
            "track_points": vessel.track_points[:5]  # First 5 points for demo
        }
        export_data.append(vessel_dict)
    
    # Save to JSON file
    with open("/Users/yingzhou/work/myfirst_agent/vessel_analysis_results.json", "w") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"Exported {len(export_data)} vessels to vessel_analysis_results.json")


def example_error_handling():
    """Example showing proper error handling."""
    print("\nExample 5: Error Handling")
    print("-" * 30)
    
    try:
        # This might fail if Elasticsearch is not running
        vessels = search_vessels_optimized_geohash(min_distance_miles=200.0)
        
        if not vessels:
            print("No vessels found matching the high distance criteria (200+ miles)")
        else:
            print(f"Found {len(vessels)} vessels with very long tracks (200+ miles)")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        print("Make sure Elasticsearch is running on localhost:9200 with vessel_index")


def demonstrate_query_benefits():
    """Demonstrate the benefits of the geohash approach."""
    print("\nGeohash Query Benefits:")
    print("-" * 30)
    print("""
    1. SPATIAL CLUSTERING: Geohash precision 5 creates ~4.9km x 4.9km cells
       - Reduces noise from GPS drift and frequent position updates
       - One representative point per cell (earliest by timestamp)
       
    2. EFFICIENT DATA TRANSFER: Only essential fields retrieved
       - BaseDateTime, LAT, LON for track calculation  
       - Vessel metadata from single top_hits aggregation
       
    3. SCALABLE PROCESSING: Scroll API with configurable batches
       - Process 1000 vessels per batch by default
       - Configurable number of scroll batches (default: 3)
       
    4. ACCURATE DISTANCE CALCULATION: External Python computation
       - Haversine formula for great-circle distances
       - No Elasticsearch scripting overhead
       
    5. OPTIMIZED RESULTS: Top 3 vessels by track length
       - Sorted by total distance (descending)
       - Meets specified requirements exactly
    """)


if __name__ == "__main__":
    print("Optimized Geohash Vessel Search Examples")
    print("=" * 50)
    
    # Run all examples
    example_basic_usage()
    example_custom_parameters() 
    example_detailed_analysis()
    example_json_export()
    example_error_handling()
    demonstrate_query_benefits()
    
    print("\n" + "=" * 50)
    print("All examples completed!")
    print("Check vessel_analysis_results.json for exported data")