# Programming-project: Mountain Path Finder

This is a personal programming project that loads geographical elevation data (.tif files) and calculates an optimal hiking path through mountainous terrain. 

I started this project because I wanted to learn how to work with geographical data in Python and apply some pathfinding ideas (like A* search) to real-world maps. I also wanted to find a good path for a hike in Norway, which is where the idea originally came from.

---

## How it works

The code runs a pipeline to turn a raw elevation grid into a 3D path:

1. **Loading Terrain**: The script loads a GeoTIFF (.tif) heightmap. If the coordinates are stored in degrees (like EPSG:4326), it calculates the metric width and height per pixel based on the map's latitude.
2. **Quadtree Decomposition**: To avoid running pathfinding on millions of pixels, the terrain is split recursively into regions. Regions with high elevation variance are split into smaller quadrants, while flat areas are left as larger squares. This places more nodes in complex terrain and fewer in flat areas.
3. **Poisson Disk Sampling**: Points are sampled inside each quadtree region. To prevent points from clustering too close to each other, a minimum distance constraint is enforced. The radius is smaller in deep quadtree levels (rough terrain) and larger in shallow levels. This sampling is compiled with Numba to keep it fast.
4. **Delaunay Triangulation**: The sampled points are connected to their nearest neighbors using Delaunay triangulation to form a clean network of edges.
5. **Graph and A* Search**: A graph is built using NetworKit. Edge weights are calculated based on 3D distance and slope. Steep slopes are penalized quadratically so that the algorithm prefers longer, flatter routes over climbing steep cliffs.
6. **Path Smoothing**: Raw paths on a node network tend to have jagged corners. The code uses a parametric spline to smooth out these sharp turns.
7. **3D Visualization**: The final path is rendered over the terrain in 3D using PyVista.

---

## Project Structure

* **`main.py`**: The main script that runs the entire pipeline from loading the data to calculating the path and showing the 3D plot.
* **`Notebook/optimal_mountain_path.ipynb`**: A notebook explaining the process, the math, and the logic behind the steps.
* **`src/config.py`**: Holds all the variables and parameters (like max quadtree depth, slope penalty alpha, and sampling radius).
* **`src/`**: Modular python files containing the code for loading, quadtree creation, sampling, graph creation, and point selection.

---

## Installation & Setup

You will need Python 3.10 or newer.

1. Clone the project:
   ```bash
   git clone <repo-url>
   cd noorwegen_project
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

---

## How to Run

To run the pipeline:

```bash
python main.py
```

When you run `main.py`:
1. An interactive Tkinter map window will open. You can pan/zoom to find your area of interest.
2. Click the **Confirm & Export Bounding Box** button at the bottom of the map.
3. The script will automatically query the STAC API, download and merge all intersecting Copernicus DEM tiles covering your bounding box, and prompt you to click a start and end point in the 2D window to compute the optimal 3D path.
