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

class Point3D(BaseModel):
    x: float
    y: float
    z: float

class PathResponse(BaseModel):
    status: str
    path: List[Point3D]
    message: Optional[str] = None
