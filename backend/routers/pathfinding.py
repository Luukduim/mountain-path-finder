from fastapi import APIRouter, HTTPException
from schemas import PathRequest, PathResponse, Point3D
from services.core_engine import MountainPathFinder
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/pathfinding",
    tags=["Pathfinding"],
)

def latlon_to_pixel(lat, lon, bounds, width, height):
    """Converts geographic coordinates to image pixel coordinates."""
    left, bottom, right, top = bounds
    
    # Clamp coordinates to bounds
    lon = max(left, min(right, lon))
    lat = max(bottom, min(top, lat))
    
    x_percent = (lon - left) / (right - left)
    y_percent = (top - lat) / (top - bottom) # y is inverted
    
    x_pixel = int(x_percent * width)
    y_pixel = int(y_percent * height)
    
    return x_pixel, y_pixel

def pixel_to_latlon(x, y, bounds, width, height):
    """Converts image pixel coordinates back to geographic coordinates."""
    left, bottom, right, top = bounds
    
    lon = left + (x / width) * (right - left)
    lat = top - (y / height) * (top - bottom)
    
    return lat, lon

# For demonstration, we'll keep a global engine instance if we want to cache, 
# but since the bbox can change per request, we instantiate per request for now.
# In a production environment, you'd want to cache the graph for commonly used bounding boxes.

@router.post("/find", response_model=PathResponse)
def find_path(request: PathRequest):
    """
    Endpoint to find a 3D path between two coordinates.
    Downloads terrain data on the fly based on the bounding box.
    """
    try:
        engine = MountainPathFinder()
        
        # Use provided bbox or fallback
        bbox = request.bbox
        if not bbox:
            bbox = [5.433225, 60.405077, 5.599050, 60.486869]
            logger.info("No bbox provided, using fallback: %s", bbox)
            
        logger.info("Loading terrain from STAC...")
        engine.load_terrain_from_stac(bbox)
        
        logger.info("Building mesh and graph...")
        engine.build_graph()
        
        # Convert requested lat/lon to pixel coordinates
        bounds = engine.terrain.bounds
        width = engine.terrain.width
        height = engine.terrain.height
        
        start_pixel = latlon_to_pixel(request.start.lat, request.start.lon, bounds, width, height)
        end_pixel = latlon_to_pixel(request.end.lat, request.end.lon, bounds, width, height)
        
        logger.info("Finding path...")
        path_3d_pixels, src_idx, tgt_idx = engine.find_path(
            start_pixel, 
            end_pixel, 
            smooth=request.smooth_path
        )
        
        if len(path_3d_pixels) == 0:
            return PathResponse(
                status="error",
                path=[],
                message="Could not find a valid path between the start and end coordinates."
            )
            
        # Convert pixel coordinates back to geographic coordinates for the frontend
        geo_path = []
        for point in path_3d_pixels:
            x_pix, y_pix, z_elevation = point[0], point[1], point[2]
            lat, lon = pixel_to_latlon(x_pix, y_pix, bounds, width, height)
            geo_path.append(Point3D(x=lon, y=lat, z=z_elevation))
            
        return PathResponse(
            status="success",
            path=geo_path,
            message=f"Path successfully found with {len(geo_path)} nodes."
        )
        
    except Exception as e:
        logger.exception("Error during pathfinding")
        raise HTTPException(status_code=500, detail=str(e))
