"""
Elasticsearch service for vessel data operations.

Singleton service designed to be easily converted to MCP server in the future.
Handles all vessel search, aggregation, and data retrieval operations.
"""

import json
import math
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch

from ..models.vessel import VesselData
from ..utils.distance import calculate_distance_miles


class ElasticsearchService:
    """
    Singleton service for Elasticsearch vessel data operations.
    
    This class is designed to be easily converted to an MCP server.
    All public methods represent future MCP server endpoints.
    """
    
    _instance: Optional['ElasticsearchService'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs) -> 'ElasticsearchService':
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self, 
        host: str = "http://localhost:9200",
        vessel_index: str = "ais_data",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """Initialize Elasticsearch client (only once due to singleton)"""
        if self._initialized:
            return
            
        self.host = host
        self.vessel_index = vessel_index
        self.client = Elasticsearch([host], timeout=timeout, max_retries=max_retries)
        self._initialized = True
        
        print(f"🔌 ElasticsearchService initialized: {host}")
    
    # Future MCP Server Endpoints
    
    def search_vessels_by_distance(
        self, 
        min_distance_miles: float = 50.0, 
        date: str = "2022-01-01", 
        scroll_batches: int = 5
    ) -> List[VesselData]:
        """
        [Future MCP Endpoint] Search for vessels with long tracks using geohash aggregation.
        
        Args:
            min_distance_miles: Minimum distance threshold
            date: Analysis date (YYYY-MM-DD format)
            scroll_batches: Number of batches to process
            
        Returns:
            List of VesselData objects sorted by distance
        """
        print(f"🔍 Searching vessels with minimum {min_distance_miles} miles on {date}")
        
        # Geohash precision 5 gives ~4.9km x 4.9km cells
        geohash_query = self._build_geohash_query(date)
        fallback_query = self._build_fallback_query(date)
        
        all_vessels: Dict[str, Dict] = {}
        processed_batches = 0
        
        try:
            # First attempt with geo_point field
            try:
                response = self.client.search(index=self.vessel_index, body=geohash_query)
                current_query = geohash_query
            except Exception:
                print("⚠️ Using fallback geohash query with LAT field")
                response = self.client.search(index=self.vessel_index, body=fallback_query)
                current_query = fallback_query
                
            # Process first batch
            vessels_batch = self._process_geohash_batch(response, min_distance_miles)
            all_vessels.update(vessels_batch)
            processed_batches += 1
            
            print(f"✅ Processed batch {processed_batches}: {len(vessels_batch)} qualifying vessels")
            
            # Process additional scroll batches
            scroll_id = None
            while processed_batches < scroll_batches:
                try:
                    if scroll_id:
                        response = self.client.scroll(scroll_id=scroll_id, scroll="2m")
                    else:
                        response = self.client.search(
                            index=self.vessel_index,
                            body=current_query,
                            scroll="2m",
                            size=0
                        )
                    
                    scroll_id = response.get("_scroll_id")
                    
                    if not response.get("aggregations"):
                        break
                        
                    vessels_batch = self._process_geohash_batch(response, min_distance_miles)
                    all_vessels.update(vessels_batch)
                    processed_batches += 1
                    
                    print(f"✅ Processed batch {processed_batches}: {len(vessels_batch)} qualifying vessels")
                    
                except Exception as e:
                    print(f"❌ Scroll batch {processed_batches + 1} failed: {e}")
                    break
            
            # Clean up scroll context
            if scroll_id:
                try:
                    self.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass
            
        except Exception as e:
            print(f"❌ Elasticsearch query failed: {e}")
            return []
        
        # Convert to VesselData objects and sort by distance
        vessel_list = []
        for mmsi, vessel_data in all_vessels.items():
            vessel = VesselData(
                mmsi=mmsi,
                vessel_name=vessel_data.get("vessel_name", ""),
                imo=vessel_data.get("imo", ""),
                call_sign=vessel_data.get("call_sign", ""),
                vessel_type=vessel_data.get("vessel_type", ""),
                length=vessel_data.get("length"),
                width=vessel_data.get("width"), 
                draft=vessel_data.get("draft"),
                track_points=vessel_data.get("track_points", []),
                total_distance_miles=vessel_data.get("total_distance_miles", 0.0)
            )
            vessel_list.append(vessel)
        
        # Sort by distance and return top 3
        vessel_list.sort(key=lambda x: x.total_distance_miles, reverse=True)
        top_vessels = vessel_list[:3]
        
        print(f"🎯 Final results: {len(top_vessels)} vessels with tracks >= {min_distance_miles} miles")
        for i, vessel in enumerate(top_vessels, 1):
            print(f"  {i}. {vessel.vessel_name} ({vessel.mmsi}): {vessel.total_distance_miles:.1f} miles")
        
        return top_vessels
    
    def health_check(self) -> Dict[str, Any]:
        """[Future MCP Endpoint] Check Elasticsearch cluster health"""
        try:
            health = self.client.cluster.health()
            return {
                "status": "connected",
                "cluster_health": health.get("status", "unknown"),
                "node_count": health.get("number_of_nodes", 0),
                "index_exists": self.client.indices.exists(index=self.vessel_index)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    # Private helper methods
    
    def _build_geohash_query(self, date: str) -> Dict[str, Any]:
        """Build geohash aggregation query for geo_point field"""
        return {
            "query": {
                "range": {
                    "BaseDateTime": {
                        "gte": f"{date}T00:00:00",
                        "lte": f"{date}T23:59:59"
                    }
                }
            },
            "size": 0,
            "aggs": {
                "vessels": {
                    "terms": {
                        "field": "MMSI.keyword",
                        "size": 1000
                    },
                    "aggs": {
                        "vessel_info": {
                            "top_hits": {
                                "size": 1,
                                "_source": ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft"]
                            }
                        },
                        "geohash_grid": {
                            "geohash_grid": {
                                "field": "location",
                                "precision": 5
                            },
                            "aggs": {
                                "representative_point": {
                                    "top_hits": {
                                        "size": 1,
                                        "sort": [{"BaseDateTime": {"order": "asc"}}],
                                        "_source": ["BaseDateTime", "LAT", "LON"]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _build_fallback_query(self, date: str) -> Dict[str, Any]:
        """Build fallback query using LAT field for geohash"""
        return {
            "query": {
                "range": {
                    "BaseDateTime": {
                        "gte": f"{date}T00:00:00",
                        "lte": f"{date}T23:59:59"
                    }
                }
            },
            "size": 0,
            "aggs": {
                "vessels": {
                    "terms": {
                        "field": "MMSI.keyword",
                        "size": 1000
                    },
                    "aggs": {
                        "vessel_info": {
                            "top_hits": {
                                "size": 1,
                                "_source": ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft"]
                            }
                        },
                        "geohash_grid": {
                            "geohash_grid": {
                                "field": "LAT",
                                "precision": 5
                            },
                            "aggs": {
                                "representative_point": {
                                    "top_hits": {
                                        "size": 1,
                                        "sort": [{"BaseDateTime": {"order": "asc"}}],
                                        "_source": ["BaseDateTime", "LAT", "LON"]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _process_geohash_batch(self, response: Dict, min_distance_miles: float) -> Dict[str, Dict]:
        """Process a single batch of geohash aggregation results"""
        vessels_batch = {}
        
        if not response.get("aggregations", {}).get("vessels", {}).get("buckets"):
            return vessels_batch
        
        for vessel_bucket in response["aggregations"]["vessels"]["buckets"]:
            mmsi = vessel_bucket["key"]
            
            # Extract vessel metadata
            vessel_info_hits = vessel_bucket["vessel_info"]["hits"]["hits"]
            if not vessel_info_hits:
                continue
                
            vessel_metadata = vessel_info_hits[0]["_source"]
            
            # Process geohash cells to get representative points
            geohash_buckets = vessel_bucket.get("geohash_grid", {}).get("buckets", [])
            if not geohash_buckets:
                continue
            
            track_points = []
            for geohash_bucket in geohash_buckets:
                rep_hits = geohash_bucket.get("representative_point", {}).get("hits", {}).get("hits", [])
                if rep_hits:
                    point_data = rep_hits[0]["_source"]
                    track_points.append({
                        "timestamp": point_data["BaseDateTime"],
                        "lat": point_data["LAT"],
                        "lon": point_data["LON"],
                        "sog": 0,  # Not available in this aggregation
                        "cog": 0,
                        "heading": 0
                    })
            
            # Sort points by timestamp
            track_points.sort(key=lambda x: x["timestamp"])
            
            # Calculate total distance
            if len(track_points) > 1:
                total_distance = self._calculate_track_distance(track_points)
                
                if total_distance >= min_distance_miles:
                    vessels_batch[mmsi] = {
                        "vessel_name": vessel_metadata.get("VesselName", ""),
                        "imo": vessel_metadata.get("IMO", ""),
                        "call_sign": vessel_metadata.get("CallSign", ""),
                        "vessel_type": str(vessel_metadata.get("VesselType", "")),
                        "length": vessel_metadata.get("Length"),
                        "width": vessel_metadata.get("Width"),
                        "draft": vessel_metadata.get("Draft"),
                        "track_points": track_points,
                        "total_distance_miles": total_distance
                    }
        
        return vessels_batch
    
    def _calculate_track_distance(self, track_points: List[Dict]) -> float:
        """Calculate total track distance using Haversine formula"""
        if len(track_points) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(track_points)):
            prev_point = track_points[i-1]
            curr_point = track_points[i]
            
            distance = calculate_distance_miles(
                prev_point["lat"], prev_point["lon"],
                curr_point["lat"], curr_point["lon"]
            )
            total_distance += distance
        
        return total_distance


# Global singleton instance
elasticsearch_service = ElasticsearchService()