import tkinter as tk
from tkinter import messagebox
import tkintermapview
import numpy as np
import matplotlib.pyplot as plt
from src.config import (
    MAX_BBOX_AREA_KM2,
    DEFAULT_BBOX_CANVAS_SIZE,
    DEFAULT_METRIC_RESOLUTION,
    DEFAULT_FIGSIZE,
    COLORBAR_SHRINK,
    MARKER_SIZE_SELECTION,
    INTERACTIVE_SELECTION_FALLBACK_START,
    INTERACTIVE_SELECTION_FALLBACK_END,
    WATER_BODY_ELEVATION
)


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


def select_points(terrain, dx=DEFAULT_METRIC_RESOLUTION, dy=DEFAULT_METRIC_RESOLUTION):
    """
    Displays the terrain heightmap and allows the user to click to choose
    the start (1st click) and end (2nd click) coordinates for the pathfinder.
    
    Parameters:
        terrain (np.ndarray): 2D terrain elevation matrix.
        dx, dy (float): Spatial resolution in meters per pixel.
        
    Returns:
        tuple: (start_coord, end_coord) in pixel coordinate format (col, row).
    """
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    height, width = terrain.shape
    print(f"Terrain shape: {terrain.shape}")
    
    # Create a display copy and mask water pixels (equal to WATER_BODY_ELEVATION) as NaN
    plot_terrain = terrain.copy()
    plot_terrain[plot_terrain == WATER_BODY_ELEVATION] = np.nan

    cmap = plt.cm.viridis.copy()
    cmap.set_bad(color='blue')

    # Plot the heightmap, flipped vertically so that North (row 0) is at the top
    im = ax.imshow(np.flipud(plot_terrain), cmap=cmap, origin='lower', aspect='auto')
    fig.colorbar(im, ax=ax, label='Elevation (m)', shrink=COLORBAR_SHRINK)
    ax.set_box_aspect(1)
    ax.set_title('Interactive Selection: Click 1st: Start, 2nd: End')
    ax.set_xlabel('X (columns)')
    ax.set_ylabel('Y (rows)')

    # Display coordinates (pixel, metric, elevation) dynamically on mouse hover
    def format_coord(x, y):
        col = int(x + 0.5)
        row = height - 1 - int(y + 0.5)
        if 0 <= col < width and 0 <= row < height:
            z = plot_terrain[row, col]
            x_m = col * dx
            y_m = (height - 1 - row) * dy
            if np.isnan(z):
                return f'Pixel: ({col}, {row}) | Metric: ({x_m:.1f}m, {y_m:.1f}m) | Height: Water'
            return f'Pixel: ({col}, {row}) | Metric: ({x_m:.1f}m, {y_m:.1f}m) | Height: {z:.2f}m'
        return f'Pixel: ({col}, {row})'

    ax.format_coord = format_coord

    coords = []
    markers = []

    def onclick(event):
        if event.inaxes != ax:
            return
        
        x, y = event.xdata, event.ydata
        col = int(x + 0.5)
        row = height - 1 - int(y + 0.5)
        
        # Keep selected coordinates within the terrain boundaries
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        
        # Reset if clicked a third time
        if len(coords) >= 2:
            coords.clear()
            for m in markers:
                m.remove()
            markers.clear()
            ax.set_title('Interactive Selection: Click 1st: Start, 2nd: End')

        coords.append((col, row))
        
        if len(coords) == 1:
            # Place green start point marker
            m = ax.plot(col, height - 1 - row, 'go', markersize=MARKER_SIZE_SELECTION, label='Start Point')[0]
            markers.append(m)
            ax.set_title('Start Point Selected! Click for End Point.')
            
        elif len(coords) == 2:
            # Place red end point marker
            m = ax.plot(col, height - 1 - row, 'ro', markersize=MARKER_SIZE_SELECTION, label='End Point')[0]
            markers.append(m)
            ax.set_title('Start & End Selected! Close window to start pathfinding.')
            print(f"Selected Start coordinate: {coords[0]}")
            print(f"Selected End coordinate: {coords[1]}")
            
        fig.canvas.draw()
            
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    
    # Fallback to defaults if window is closed early without complete selection
    if len(coords) < 2:
        print("Warning: Coordinate selection incomplete. Using default path coordinates.")
        fallback_start = INTERACTIVE_SELECTION_FALLBACK_START
        fallback_end = INTERACTIVE_SELECTION_FALLBACK_END
        return fallback_start, fallback_end
        
    return coords[0], coords[1]
