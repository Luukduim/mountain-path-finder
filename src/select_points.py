import numpy as np
import matplotlib.pyplot as plt
from src.config import (
    DEFAULT_METRIC_RESOLUTION,
    DEFAULT_FIGSIZE,
    COLORBAR_SHRINK,
    MARKER_SIZE_SELECTION,
    INTERACTIVE_SELECTION_FALLBACK_START,
    INTERACTIVE_SELECTION_FALLBACK_END,
    WATER_BODY_ELEVATION
)

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
