import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.spatial import Delaunay
from src.config import (
    DEFAULT_FIGSIZE,
    LINEWIDTH_QUADTREE_BORDER,
    LINEWIDTH_2D_DELAUNAY,
    MARKERSIZE_2D_NODES,
    LINEWIDTH_2D_PATH,
    PYVISTA_Z_FIGHTING_OFFSET,
    PYVISTA_POINT_SIZE,
    PYVISTA_PATH_LINE_WIDTH_CLOUD,
    PYVISTA_PATH_LINE_WIDTH_SURFACE,
    WATER_BODY_ELEVATION,
    PYVISTA_BACKGROUND_COLOR
)


def draw_quadtree(matrix, regions, max_depth=None, savepath=None, show=False, ax=None):
    """Draws the terrain heatmap and overlays red quadtree leaf boundaries."""
    if ax is None:
        fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
        created_fig = True
    else:
        fig = ax.get_figure()
        created_fig = False

    ax.imshow(matrix, cmap='viridis', interpolation='nearest', origin='lower', aspect='auto')
    ax.set_box_aspect(1)
    ax.grid(False)
    ax.set_xlim(0, matrix.shape[1])
    ax.set_ylim(0, matrix.shape[0])

    # Draw a bounding rectangle for each leaf region
    for reg in regions:
        x, y, w, h = reg['x'], reg['y'], reg['w'], reg['h']
        rect = patches.Rectangle(
            (x, y), w, h,
            linewidth=LINEWIDTH_QUADTREE_BORDER,
            edgecolor='red',
            facecolor='none',
        )
        ax.add_patch(rect)

    ax.set_title('Quadtree Region Overlay')
    if savepath and created_fig:
        fig.savefig(savepath, bbox_inches='tight')
    if show:
        plt.show()
    if created_fig:
        plt.close(fig)


def plot_2d_delaunay(points, path_3d=None):
    """Plot the 2D Delaunay triangulation layout and overlay the path if provided."""
    if points.shape[0] < 3:
        return

    tri = Delaunay(points)
    plt.figure(figsize=(DEFAULT_FIGSIZE[0] * 1.5, DEFAULT_FIGSIZE[1] * 1.5))
    # Emphasize the network: use a slightly thicker steelblue line and fade the background nodes
    plt.triplot(points[:, 0], points[:, 1], tri.simplices, color='steelblue', linewidth=LINEWIDTH_2D_DELAUNAY * 2.5, alpha=0.75)
    plt.plot(points[:, 0], points[:, 1], 'ko', markersize=MARKERSIZE_2D_NODES, alpha=0.15)
    
    if path_3d is not None and len(path_3d) > 0:
        plt.plot(path_3d[:, 0], path_3d[:, 1], 'r-', linewidth=LINEWIDTH_2D_PATH, label='A* Shortest Path')
        plt.legend()
        
    plt.gca().set_xlim(0, points[:, 0].max() + 1)
    plt.gca().set_ylim(0, points[:, 1].max() + 1)
    plt.title('2D Delaunay Triangulation')


def plot_3d_pointcloud_pyvista(height_points, path_3d=None, dx=1.0, dy=1.0, height=None):
    """3D point cloud interactive plot using PyVista (GPU-accelerated)."""
    try:
        import pyvista as pv
    except ImportError:
        print("Error: PyVista is not installed.")
        return

    if height is None and len(height_points) > 0:
        height = int(np.round(height_points[:, 1].max())) + 1

    scaled_points = height_points.copy()
    scaled_points[:, 0] *= dx
    if height is not None:
        scaled_points[:, 1] = (height - 1 - scaled_points[:, 1]) * dy
    else:
        scaled_points[:, 1] *= dy

    point_cloud = pv.PolyData(scaled_points)
    point_cloud["Elevation"] = scaled_points[:, 2]

    plotter = pv.Plotter()
    plotter.set_background(PYVISTA_BACKGROUND_COLOR)
    plotter.add_mesh(
        point_cloud, scalars="Elevation", cmap="terrain", point_size=PYVISTA_POINT_SIZE,
        render_points_as_spheres=True, label="Sampled Points (3D)",
        scalar_bar_args={"fmt": "%.0f", "title": "Elevation (m)"}
    )

    if path_3d is not None and len(path_3d) > 0:
        scaled_path = path_3d.copy()
        scaled_path[:, 0] *= dx
        if height is not None:
            scaled_path[:, 1] = (height - 1 - scaled_path[:, 1]) * dy
        else:
            scaled_path[:, 1] *= dy
        scaled_path[:, 2] += PYVISTA_Z_FIGHTING_OFFSET  # Floating offset to avoid overlay z-fighting

        num_points = len(scaled_path)
        cells = np.hstack(([num_points], np.arange(num_points)))

        path_mesh = pv.PolyData(scaled_path)
        path_mesh.lines = cells
        plotter.add_mesh(
            path_mesh, color="red", line_width=PYVISTA_PATH_LINE_WIDTH_CLOUD, render_lines_as_tubes=True, label="A* Route"
        )

    plotter.add_legend()
    plotter.show_axes()
    plotter.show()


def plot_terrain_surface_pyvista(terrain_matrix, dx=1.0, dy=1.0, path_3d=None):
    """Plot the warped 3D terrain surface mesh using PyVista (GPU-accelerated)."""
    try:
        import pyvista as pv
    except ImportError:
        print("Error: PyVista is not installed.")
        return

    height, width = terrain_matrix.shape
    x = np.arange(width) * dx
    y = np.arange(height) * dy
    x_grid, y_grid = np.meshgrid(x, y)

    # Flip the terrain vertically so that row 0 (North) is at the top of the Y axis
    grid = pv.StructuredGrid(x_grid, y_grid, np.flipud(terrain_matrix))
    grid["Elevation"] = grid.points[:, 2]

    # Filter out water body cells (which are set to WATER_BODY_ELEVATION)
    # to avoid vertical drop-off cliffs at the shorelines.
    try:
        land_grid = grid.threshold(value=WATER_BODY_ELEVATION + 0.5, scalars="Elevation")
    except Exception:
        land_grid = grid

    plotter = pv.Plotter()
    plotter.set_background(PYVISTA_BACKGROUND_COLOR)
    plotter.add_mesh(
        land_grid, scalars="Elevation", cmap="terrain", show_edges=False, label="3D Terrain",
        scalar_bar_args={"fmt": "%.0f", "title": "Elevation (m)"}
    )

    if path_3d is not None and len(path_3d) > 0:
        scaled_path = path_3d.copy()
        scaled_path[:, 0] *= dx
        scaled_path[:, 1] = (height - 1 - scaled_path[:, 1]) * dy
        scaled_path[:, 2] += PYVISTA_Z_FIGHTING_OFFSET  # Floating offset to avoid z-fighting

        num_points = len(scaled_path)
        cells = np.hstack(([num_points], np.arange(num_points)))

        path_mesh = pv.PolyData(scaled_path)
        path_mesh.lines = cells
        plotter.add_mesh(
            path_mesh, color="red", line_width=PYVISTA_PATH_LINE_WIDTH_SURFACE, render_lines_as_tubes=True, label="A* Route"
        )

    plotter.add_legend()
    plotter.show_axes()
    plotter.show()
