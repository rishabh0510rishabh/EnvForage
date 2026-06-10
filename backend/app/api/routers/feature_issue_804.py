from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/locations", tags=["Locations"])

class Location(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    
# Mock database with spatial indexes
# In a real scenario, this would be a PostGIS database or MongoDB 2dsphere index
MOCK_LOCATIONS = [
    Location(id="1", name="Central Park Foraging Spot", latitude=40.7812, longitude=-73.9665),
    Location(id="2", name="Mushroom Trail", latitude=40.7850, longitude=-73.9680)
]

# Strict validation for spatial queries to prevent DoS
MAX_SEARCH_RADIUS_KM = 50.0

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula placeholder for demo
    # Real app uses DB geospatial functions
    import math
    R = 6371.0 # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.get(
    "/nearby",
    summary="Optimized Spatial Query (Issue #804)",
    description="Enforces strict input validation and simulated spatial bounding-box optimization for location data to prevent full-table scans."
)
async def get_nearby_locations(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of the center point"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of the center point"),
    radius_km: float = Query(5.0, gt=0, le=MAX_SEARCH_RADIUS_KM, description=f"Search radius in km. Max {MAX_SEARCH_RADIUS_KM}km to prevent DB locks.")
):
    """
    Search for nearby locations using bounding box filtering followed by distance calculation.
    """
    # 1. Spatial Query Optimization: Calculate bounding box
    # 1 degree of latitude is roughly 111km
    lat_delta = radius_km / 111.0
    import math
    lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))
    
    min_lat, max_lat = latitude - lat_delta, latitude + lat_delta
    min_lon, max_lon = longitude - lon_delta, longitude + lon_delta
    
    # 2. Optimized Database Query (Simulated)
    # First, filter by bounding box (utilizes indexes in PostGIS/MongoDB)
    bbox_filtered = [
        loc for loc in MOCK_LOCATIONS
        if min_lat <= loc.latitude <= max_lat and min_lon <= loc.longitude <= max_lon
    ]
    
    # 3. Precise Distance Calculation on the reduced set
    results = []
    for loc in bbox_filtered:
        distance = calculate_distance(latitude, longitude, loc.latitude, loc.longitude)
        if distance <= radius_km:
            results.append({
                "location": loc,
                "distance_km": round(distance, 2)
            })
            
    # Sort by nearest
    results.sort(key=lambda x: x["distance_km"])
    
    return {
        "center": {"latitude": latitude, "longitude": longitude},
        "radius_km": radius_km,
        "results": results
    }
