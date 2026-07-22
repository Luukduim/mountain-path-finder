from pydantic import BaseModel, Field
from typing import List, Optional, Tuple



class Coordinate(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

class PathRequest(BaseModel):
    start: Coordinate
    end: Coordinate
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    smooth_path: bool = True
    return_sampled_points: bool = True

class Point3D(BaseModel):
    x: float
    y: float
    z: float

class PathResponse(BaseModel):
    status: str
    path: List[Point3D]
    message: Optional[str] = None
    sampled_points: Optional[List[Point3D]] = None
    simplices: Optional[List[List[int]]] = None
    dx: Optional[float] = None
    dy: Optional[float] = None
    res_x: Optional[float] = None
    res_y: Optional[float] = None
