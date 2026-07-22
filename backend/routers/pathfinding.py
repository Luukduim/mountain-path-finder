from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas import PathRequest, PathResponse, Point3D
from services.core_engine import MountainPathFinder
import rasterio.transform
import logging
import numpy as np
import json
import queue
import threading

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/pathfinding",
    tags=["Pathfinding"],
)

def latlon_to_pixel(lat, lon, bounds, width, height, transform=None):
    """Converts geographic coordinates to continuous image pixel coordinates (floats)."""
    if transform is not None:
        col, row = ~transform * (lon, lat)
        x_pixel = max(0.0, min(float(width - 1), float(col)))
        y_pixel = max(0.0, min(float(height - 1), float(row)))
        return x_pixel, y_pixel

    left, bottom, right, top = bounds
    
    # Clamp coordinates to bounds
    lon = max(left, min(right, lon))
    lat = max(bottom, min(top, lat))
    
    x_percent = (lon - left) / (right - left)
    y_percent = (top - lat) / (top - bottom) # y is inverted
    
    x_pixel = x_percent * (width - 1)
    y_pixel = y_percent * (height - 1)
    
    return x_pixel, y_pixel

def pixel_to_latlon(x, y, bounds, width, height, transform=None):
    """Converts image pixel coordinates back to geographic coordinates."""
    if transform is not None:
        if isinstance(x, (int, np.integer)) or (isinstance(x, float) and x.is_integer()):
            lon, lat = rasterio.transform.xy(transform, y, x, offset='center')
        else:
            lon, lat = transform * (x, y)
        return lat, lon

    left, bottom, right, top = bounds
    
    lon = left + (x / (width - 1)) * (right - left)
    lat = top - (y / (height - 1)) * (top - bottom)
    
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
        
        # Convert requested lat/lon to pixel coordinates
        bounds = engine.terrain.bounds
        width = engine.terrain.width
        height = engine.terrain.height
        transform = engine.terrain.transform
        
        start_pixel = latlon_to_pixel(request.start.lat, request.start.lon, bounds, width, height, transform=transform)
        end_pixel = latlon_to_pixel(request.end.lat, request.end.lon, bounds, width, height, transform=transform)
        
        logger.info("Building mesh and graph with exact start/end points injected...")
        engine.build_graph(start_pixel=start_pixel, end_pixel=end_pixel)
        
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
        n_points = len(path_3d_pixels)
        for i, point in enumerate(path_3d_pixels):
            x_pix, y_pix, z_elevation = point[0], point[1], point[2]
            if i == 0 and src_idx == engine.mesh.source_idx:
                lat, lon = request.start.lat, request.start.lon
            elif i == n_points - 1 and tgt_idx == engine.mesh.target_idx:
                lat, lon = request.end.lat, request.end.lon
            else:
                lat, lon = pixel_to_latlon(x_pix, y_pix, bounds, width, height, transform=transform)
            geo_path.append(Point3D(x=lon, y=lat, z=z_elevation))
            
        sampled_geo_points = None
        simplices = None
        pts_to_return = engine.mesh.vis_height_points if engine.mesh.vis_height_points is not None else engine.mesh.height_points
        if request.return_sampled_points and pts_to_return is not None:
            sampled_geo_points = []
            for pt in pts_to_return:
                lat_pt, lon_pt = pixel_to_latlon(pt[0], pt[1], bounds, width, height, transform=transform)
                sampled_geo_points.append(Point3D(x=lon_pt, y=lat_pt, z=pt[2]))
            simplices = engine.mesh.simplices

        return PathResponse(
            status="success",
            path=geo_path,
            message=f"Path successfully found with {len(geo_path)} nodes.",
            sampled_points=sampled_geo_points,
            simplices=simplices
        )
        
    except Exception as e:
        logger.exception("Error during pathfinding")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find_stream")
def find_path_stream(request: PathRequest):
    """
    Streaming endpoint that yields SSE (Server-Sent Events) reporting live progress
    before sending the final PathResponse JSON payload.
    """
    def generate():
        q = queue.Queue()
        
        def run_pipeline():
            try:
                engine = MountainPathFinder()
                
                def report_progress(msg: str):
                    logger.info("Progress: %s", msg)
                    q.put({"step": "status", "message": msg})
                    
                bbox = request.bbox
                if not bbox:
                    bbox = [5.433225, 60.405077, 5.599050, 60.486869]
                    
                report_progress("Loading DEM tiles...")
                engine.load_terrain_from_stac(bbox, progress_callback=report_progress)
                
                bounds = engine.terrain.bounds
                width = engine.terrain.width
                height = engine.terrain.height
                transform = engine.terrain.transform
                
                start_pixel = latlon_to_pixel(request.start.lat, request.start.lon, bounds, width, height, transform=transform)
                end_pixel = latlon_to_pixel(request.end.lat, request.end.lon, bounds, width, height, transform=transform)
                
                report_progress("Building mesh and graph...")
                engine.build_graph(start_pixel=start_pixel, end_pixel=end_pixel, progress_callback=report_progress)
                
                report_progress("Running A* search...")
                path_3d_pixels, src_idx, tgt_idx = engine.find_path(
                    start_pixel, 
                    end_pixel, 
                    smooth=request.smooth_path,
                    progress_callback=report_progress
                )
                
                if len(path_3d_pixels) == 0:
                    q.put({"step": "error", "message": "Could not find a valid path between the start and end coordinates."})
                    return
                    
                report_progress("Converting coordinates...")
                geo_path = []
                n_points = len(path_3d_pixels)
                for i, point in enumerate(path_3d_pixels):
                    x_pix, y_pix, z_elevation = point[0], point[1], point[2]
                    if i == 0 and src_idx == engine.mesh.source_idx:
                        lat, lon = request.start.lat, request.start.lon
                    elif i == n_points - 1 and tgt_idx == engine.mesh.target_idx:
                        lat, lon = request.end.lat, request.end.lon
                    else:
                        lat, lon = pixel_to_latlon(x_pix, y_pix, bounds, width, height, transform=transform)
                    geo_path.append(Point3D(x=lon, y=lat, z=z_elevation))
                    
                sampled_geo_points = None
                simplices = None
                pts_to_return = engine.mesh.vis_height_points if engine.mesh.vis_height_points is not None else engine.mesh.height_points
                if request.return_sampled_points and pts_to_return is not None:
                    sampled_geo_points = []
                    for pt in pts_to_return:
                        lat_pt, lon_pt = pixel_to_latlon(pt[0], pt[1], bounds, width, height, transform=transform)
                        sampled_geo_points.append(Point3D(x=lon_pt, y=lat_pt, z=pt[2]))
                    simplices = engine.mesh.simplices

                response_obj = PathResponse(
                    status="success",
                    path=geo_path,
                    message=f"Path successfully found with {len(geo_path)} nodes.",
                    sampled_points=sampled_geo_points,
                    simplices=simplices
                )
                resp_dict = response_obj.model_dump() if hasattr(response_obj, "model_dump") else response_obj.dict()
                q.put({"step": "complete", "result": resp_dict})
            except Exception as e:
                logger.exception("Error during streaming pathfinding")
                q.put({"step": "error", "message": str(e)})
            finally:
                q.put(None)

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
        
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
