import rasterio
import numpy as np
from src.config import DEFAULT_RASTER_BAND, MAX_BBOX_AREA_KM2, DEFAULT_BBOX_CANVAS_SIZE 
import tkinter as tk
from tkinter import messagebox
import tkintermapview


def load_terrain(file_path):
    """
    Loads a single-band GeoTIFF heightmap file and returns it as a NumPy float32 matrix.
    
    Parameters:
        file_path (str): Path to the .tif heightmap file.
        
    Returns:
        np.ndarray: 2D array of elevation values.
    """
    try:
        with rasterio.open(file_path) as src:
            # Read first band and cast to float for stability in variance / slope math
            terrain_matrix = src.read(DEFAULT_RASTER_BAND).astype(np.float32)
        print(f"Terrain successfully loaded. Matrix shape: {terrain_matrix.shape}")
        return terrain_matrix
    except Exception as e:
        raise RuntimeError(f"Failed to load terrain file from {file_path}: {e}")

def calculate_bbox_area_km2(west, south, east, north):
    """
    Calculates the approximate area of the bounding box in square kilometers.
    """
    R = 6371000.0  # Earth radius in meters
    center_lat = (south + north) / 2.0
    center_lat_rad = np.radians(center_lat)
    
    # Calculate width and height in meters
    width_m = abs(east - west) * (np.cos(center_lat_rad) * np.pi * R) / 180.0
    height_m = abs(north - south) * (np.pi * R) / 180.0
    
    return (width_m * height_m) / 1e6

def select_bounding_box(map_widget, root, max_area_km2=MAX_BBOX_AREA_KM2):
    # Fetch the bounding box of the current map view
    # Top-left corner coordinates (latitude, longitude)
    top_left = map_widget.convert_canvas_coords_to_decimal_coords(0, 0)
    canvas_w = map_widget.canvas.winfo_width()
    canvas_h = map_widget.canvas.winfo_height()
    # Bottom-right corner coordinates (latitude, longitude)
    bottom_right = map_widget.convert_canvas_coords_to_decimal_coords(
        canvas_w, 
        canvas_h
    )
    
    # Extract coordinates (latitude is index 0, longitude is index 1)
    north, west = top_left
    south, east = bottom_right
    
    # Ensure proper ordering
    west, east = min(west, east), max(west, east)
    south, north = min(south, north), max(south, north)
    
    # Enforce maximum area constraint if specified
    if max_area_km2 is not None:
        area = calculate_bbox_area_km2(west, south, east, north)
        if area > max_area_km2:
            messagebox.showwarning(
                "Selection Too Large",
                f"The currently visible map area is {area:.2f} km², which exceeds the "
                f"maximum allowed limit of {max_area_km2:.2f} km².\n\n"
                f"Please zoom in closer to reduce the bounding box area."
            )
            return None
            
    bbox = [west, south, east, north]
    print("\n" + "="*80)
    print("--- SELECTED BOUNDING BOX ---")
    print(f"Canvas Dimensions: {canvas_w}x{canvas_h} px (Square N x N)")
    print(f"BBOX Format [West, South, East, North]:")
    print(f"[{west:.6f}, {south:.6f}, {east:.6f}, {north:.6f}]")
    if max_area_km2 is not None:
        area = calculate_bbox_area_km2(west, south, east, north)
        print(f"Area: {area:.2f} km²")
    print("="*80 + "\n")
    
    # Close the window automatically after selecting
    root.destroy()
    return bbox

def select_bbox_interactively(start_lat=0.0, start_lon=0.0, zoom=1, max_area_km2=MAX_BBOX_AREA_KM2, canvas_size=DEFAULT_BBOX_CANVAS_SIZE):
    """
    Spawns an interactive Tkinter window with a square (N x N) map canvas. 
    The user can pan/zoom to their area of interest.
    Clicking the 'Confirm Bounding Box' button prints the bounding box coordinates 
    and closes the window.
    """
    root = tk.Tk()
    root.title(f"Select Bounding Box [Square Canvas: {canvas_size}x{canvas_size} px]")
    
    button_frame_height = 60
    root.geometry(f"{canvas_size}x{canvas_size + button_frame_height}")
    root.minsize(400, 400 + button_frame_height)

    # 1. Pack the button frame at the bottom first so it occupies a fixed height
    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", side="bottom")

    # 2. Pack the map container frame above the button frame
    map_container = tk.Frame(root, bg="#2b2b2b")
    map_container.pack(fill="both", expand=True, side="top")

    # 3. Create map widget inside the container
    map_widget = tkintermapview.TkinterMapView(map_container, width=canvas_size, height=canvas_size, corner_radius=0)

    # Set position (Default: Mount Everest area)
    map_widget.set_position(start_lat, start_lon)
    map_widget.set_zoom(zoom)

    # Dynamic layout handler to keep canvas always square (N x N) and centered when window resizes
    def on_container_resize(event):
        if event.widget != map_container:
            return
        N = min(event.width, event.height)
        if N <= 1:
            return
        x = (event.width - N) // 2
        y = (event.height - N) // 2
        map_widget.place(x=x, y=y, width=N, height=N)
        root.title(f"Select Bounding Box [Square Canvas: {N}x{N} px]")

    map_container.bind("<Configure>", on_container_resize)

    selected_bbox = []

    # Callback helper
    def on_confirm():
        bbox = select_bounding_box(map_widget, root, max_area_km2=max_area_km2)
        if bbox is not None:
            selected_bbox.append(bbox)

    confirm_button = tk.Button(
        button_frame, 
        text="Confirm & Export Bounding Box", 
        command=on_confirm,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 12, "bold"),
        pady=10
    )
    confirm_button.pack(fill="x")

    root.mainloop()
    
    if selected_bbox:
        return selected_bbox[0]
    return None