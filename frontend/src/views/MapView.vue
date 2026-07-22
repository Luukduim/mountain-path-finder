<script setup>
import { ref, shallowRef, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Plotly from 'plotly.js-dist-min'

const mapStyles = [
  {
    id: 'topo-light',
    name: 'OpenTopoMap (Light)',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    maxZoom: 17,
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    darkFilter: false
  },
  {
    id: 'topo-dark',
    name: 'OpenTopoMap (Dark)',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    maxZoom: 17,
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    darkFilter: true
  },
  {
    id: 'carto-dark',
    name: 'CartoDB Dark Matter',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    darkFilter: false
  },
  {
    id: 'carto-light',
    name: 'CartoDB Positron',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    darkFilter: false
  },
  {
    id: 'osm',
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    darkFilter: false
  },
  {
    id: 'satellite',
    name: 'Esri World Imagery',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri',
    darkFilter: false
  }
]

const map = shallowRef(null)

const currentMapStyleId = ref('topo-dark')
const isDarkFilter = computed(() => {
  const style = mapStyles.find(s => s.id === currentMapStyleId.value)
  return style ? style.darkFilter : false
})

const startLocation = ref(null)
const endLocation = ref(null)
const pinningMode = ref(null)
const isLoading = ref(false)
const distance = ref('-- km')
const estTime = ref('--')
const colorMode = ref('elevation')
const currentPathData = ref(null)
const currentSampledPoints = ref(null)
const currentSimplices = ref(null)
const currentBBox = ref(null)
const is3DView = ref(false)

// Ready-to-use Plotly traces generator for 3D visualization
const plotlyTraces = computed(() => {
  if (!currentSampledPoints.value || !currentPathData.value) return []
  
  const traces = []
  
  // 1. Terrain Mesh or Point Cloud Trace
  const colorbarConfig = {
    title: {
      text: 'Elevation (m)',
      font: { color: '#ffffff', size: 12 },
      side: 'top'
    },
    tickfont: { color: '#a1a1aa', size: 11 },
    thickness: 14,
    len: 0.65,
    x: 0.95,
    y: 0.5,
    bgcolor: 'rgba(12, 7, 20, 0.75)',
    bordercolor: 'rgba(255, 255, 255, 0.1)',
    borderwidth: 1,
    outlinewidth: 0
  }

  if (currentSimplices.value && currentSimplices.value.length > 0) {
    traces.push({
      type: 'mesh3d',
      name: 'Terrain Mesh',
      x: currentSampledPoints.value.map(p => p.x),
      y: currentSampledPoints.value.map(p => p.y),
      z: currentSampledPoints.value.map(p => p.z),
      i: currentSimplices.value.map(t => t[0]),
      j: currentSimplices.value.map(t => t[1]),
      k: currentSimplices.value.map(t => t[2]),
      colorscale: 'Earth',
      intensity: currentSampledPoints.value.map(p => p.z),
      opacity: 1.0,
      hoverinfo: 'x+y+z',
      colorbar: colorbarConfig
    })
  } else {
    traces.push({
      type: 'scatter3d',
      mode: 'markers',
      name: 'Sampled Terrain Points',
      x: currentSampledPoints.value.map(p => p.x),
      y: currentSampledPoints.value.map(p => p.y),
      z: currentSampledPoints.value.map(p => p.z),
      marker: {
        size: 2,
        color: currentSampledPoints.value.map(p => p.z),
        colorscale: 'Earth',
        opacity: 1.0,
        colorbar: colorbarConfig
      }
    })
  }

  // 2. 3D Path Trace
  traces.push({
    type: 'scatter3d',
    mode: 'lines',
    name: 'Optimal Route',
    x: currentPathData.value.map(p => p.x),
    y: currentPathData.value.map(p => p.y),
    z: currentPathData.value.map(p => p.z + 25),
    line: {
      color: '#ff3b30',
      width: 8
    }
  })

  return traces
})

const renderPlotly3D = () => {
  if (!plotlyTraces.value || plotlyTraces.value.length === 0 || !currentSampledPoints.value) return
  
  // Calculate exact physical bounding box dimensions in meters from geographic coordinates
  const lons = currentSampledPoints.value.map(p => p.x)
  const lats = currentSampledPoints.value.map(p => p.y)
  const elevs = currentSampledPoints.value.map(p => p.z)
  
  const minLon = Math.min(...lons), maxLon = Math.max(...lons)
  const minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const minElev = Math.min(...elevs), maxElev = Math.max(...elevs)
  
  // Convert degree spans to metric distances using ~111,320m per degree lat and cos(lat) for lon
  const avgLatRad = ((minLat + maxLat) / 2) * (Math.PI / 180)
  const spanX_m = (maxLon - minLon) * 111320 * Math.cos(avgLatRad)
  const spanY_m = (maxLat - minLat) * 111320
  const spanZ_m = Math.max(maxElev - minElev, 10)
  
  // Normalize by the largest horizontal span to get true physical scale ratios
  const maxHoriz_m = Math.max(spanX_m, spanY_m)
  const ratioX = spanX_m / maxHoriz_m
  const ratioY = spanY_m / maxHoriz_m
  // Apply a subtle 1.5x vertical exaggeration to physical Z ratio for clear mountain relief viewing
  const ratioZ = Math.max((spanZ_m / maxHoriz_m) * 1.5, 0.15)

  Plotly.newPlot('plotly-3d-map', plotlyTraces.value, {
    paper_bgcolor: '#0c0714',
    plot_bgcolor: '#0c0714',
    scene: {
      xaxis: { 
        title: 'Longitude', 
        color: '#a1a1aa', 
        gridcolor: 'rgba(255, 255, 255, 0.08)',
        zerolinecolor: 'rgba(255, 255, 255, 0.15)',
        showbackground: true,
        backgroundcolor: 'rgba(18, 12, 28, 0.4)'
      },
      yaxis: { 
        title: 'Latitude', 
        color: '#a1a1aa', 
        gridcolor: 'rgba(255, 255, 255, 0.08)',
        zerolinecolor: 'rgba(255, 255, 255, 0.15)',
        showbackground: true,
        backgroundcolor: 'rgba(18, 12, 28, 0.4)'
      },
      zaxis: { 
        title: 'Elevation (m)', 
        color: '#a1a1aa', 
        gridcolor: 'rgba(255, 255, 255, 0.08)',
        zerolinecolor: 'rgba(255, 255, 255, 0.15)',
        showbackground: true,
        backgroundcolor: 'rgba(18, 12, 28, 0.6)'
      },
      camera: {
        eye: { x: 1.85, y: -1.85, z: 0.95 }
      },
      aspectmode: 'manual',
      aspectratio: { x: ratioX, y: ratioY, z: ratioZ }
    },
    margin: { l: 20, r: 80, b: 20, t: 30 },
    showlegend: true,
    legend: {
      x: 0.02,
      y: 0.95,
      font: { color: '#ffffff', size: 12 },
      bgcolor: 'rgba(12, 7, 20, 0.75)',
      bordercolor: 'rgba(255, 255, 255, 0.1)',
      borderwidth: 1
    }
  }, {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['toImage', 'sendDataToCloud', 'hoverClosest3d']
  })
}

const toggle3DView = async () => {
  is3DView.value = !is3DView.value
  if (is3DView.value) {
    await nextTick()
    renderPlotly3D()
  }
}

let startMarker = null
let endMarker = null
let routePolyline = null
let bboxRectangle = null

onMounted(() => {
  // Initialize Leaflet map
  map.value = L.map('map', {
    zoomControl: false // Custom placement below
  }).setView([27.9881, 86.9250], 12) // Default to Mount Everest area

  // Add zoom control to top right so it stays clear of the sidebar
  L.control.zoom({ position: 'topright' }).addTo(map.value)

  // Initial map layer
  const initialStyle = mapStyles.find(s => s.id === currentMapStyleId.value)
  let currentTileLayer = L.tileLayer(initialStyle.url, {
    maxZoom: initialStyle.maxZoom,
    attribution: initialStyle.attribution
  }).addTo(map.value)

  watch(currentMapStyleId, (newId) => {
    const style = mapStyles.find(s => s.id === newId)
    if (style && currentTileLayer) {
      map.value.removeLayer(currentTileLayer)
      currentTileLayer = L.tileLayer(style.url, {
        maxZoom: style.maxZoom,
        attribution: style.attribution
      }).addTo(map.value)
    }
  })

  // Handle map clicks for setting points
  map.value.on('click', (e) => {
    if (!pinningMode.value) return // Only set points when pinning mode is active
    
    const { lat, lng } = e.latlng
    
    if (pinningMode.value === 'start') {
      startLocation.value = { lat, lon: lng }
      
      // Update marker
      if (!startMarker) {
        startMarker = L.circleMarker([lat, lng], {
          radius: 7,
          fillColor: '#3b82f6',
          fillOpacity: 1,
          color: '#0C0714',
          weight: 3,
          opacity: 1
        }).addTo(map.value)
      } else {
        startMarker.setLatLng([lat, lng])
      }
      
      pinningMode.value = null
    } else if (pinningMode.value === 'end') {
      // Set End
      endLocation.value = { lat, lon: lng }
      
      if (!endMarker) {
        endMarker = L.circleMarker([lat, lng], {
          radius: 7,
          fillColor: '#ef4444',
          fillOpacity: 1,
          color: '#0C0714',
          weight: 3,
          opacity: 1
        }).addTo(map.value)
      } else {
        endMarker.setLatLng([lat, lng])
      }
      
      pinningMode.value = null
    }
    
    // Clear route and bbox when a point changes
    if (routePolyline) {
      map.value.removeLayer(routePolyline)
      routePolyline = null
    }
    if (bboxRectangle) {
      map.value.removeLayer(bboxRectangle)
      bboxRectangle = null
    }
    currentPathData.value = null
    currentSampledPoints.value = null
    currentSimplices.value = null
    currentBBox.value = null
    is3DView.value = false
    
    distance.value = '-- km'
    estTime.value = '--'
  })
})

onUnmounted(() => {
  if (map.value) {
    map.value.remove()
  }
})

const drawRoute = () => {
  if (!currentPathData.value) return;
  const fullPath = currentPathData.value;
  
  if (routePolyline) {
    map.value.removeLayer(routePolyline)
  }
  if (bboxRectangle) {
    map.value.removeLayer(bboxRectangle)
    bboxRectangle = null
  }
  
  if (currentBBox.value && map.value) {
    const [minLon, minLat, maxLon, maxLat] = currentBBox.value
    bboxRectangle = L.rectangle([[minLat, minLon], [maxLat, maxLon]], {
      color: '#ef4444',
      weight: 2,
      dashArray: '6, 6',
      fill: true,
      fillColor: '#ef4444',
      fillOpacity: 0.05,
      interactive: false
    }).addTo(map.value)
    bboxRectangle.bringToBack()
  }
  
  if (colorMode.value === 'primary') {
    // Normal primary color
    const coordinates = fullPath.map(p => [p.y, p.x]);
    routePolyline = L.polyline(coordinates, {
      color: '#ff3b30',
      weight: 5,
      opacity: 0.95,
      lineCap: 'round',
      lineJoin: 'round',
      className: 'route-line'
    }).addTo(map.value)
  } else {
    // Elevation colored
    let minZ = Infinity;
    let maxZ = -Infinity;
    fullPath.forEach(p => {
      if (p.z < minZ) minZ = p.z;
      if (p.z > maxZ) maxZ = p.z;
    });
    
    routePolyline = L.featureGroup().addTo(map.value)
    
    for (let i = 0; i < fullPath.length - 1; i++) {
      const p1 = fullPath[i];
      const p2 = fullPath[i+1];
      
      const avgZ = (p1.z + p2.z) / 2;
      
      let ratio = maxZ === minZ ? 0 : (avgZ - minZ) / (maxZ - minZ);
      const hue = (1 - ratio) * 120;
      const lightness = 45 - (ratio * 25);
      const color = `hsl(${hue}, 100%, ${lightness}%)`;
      
      L.polyline([[p1.y, p1.x], [p2.y, p2.x]], {
        color: color,
        weight: 6,
        opacity: 0.95,
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(routePolyline);
    }
  }
  
  routePolyline.bringToBack()
}

watch(colorMode, () => {
  drawRoute()
})

const calculateRoute = async () => {
  if (!startLocation.value || !endLocation.value) return
  
  isLoading.value = true
  
  try {
    // Use the exact visible map canvas bounds
    const bounds = map.value.getBounds();
    const min_lon = bounds.getWest();
    const min_lat = bounds.getSouth();
    const max_lon = bounds.getEast();
    const max_lat = bounds.getNorth();

    // Check area right away before querying API to give instant, clear feedback if box is too large
    const avgLatRad = ((min_lat + max_lat) / 2) * (Math.PI / 180)
    const width_m = Math.abs(max_lon - min_lon) * 111320 * Math.cos(avgLatRad)
    const height_m = Math.abs(max_lat - min_lat) * 111320
    const area_km2 = (width_m * height_m) / 1e6
    
    if (area_km2 > 10000) {
      alert(`Selected map area (${area_km2.toFixed(1)} km²) exceeds the maximum allowed limit of 10,000 km².\n\nPlease zoom in closer to reduce the bounding box area.`)
      isLoading.value = false
      return
    }

    console.log(min_lon, min_lat, max_lon, max_lat, "this should be the bbox")

    estTime.value = 'Connecting...'
    const response = await fetch('http://localhost:8000/api/pathfinding/find_stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        start: { lat: startLocation.value.lat, lon: startLocation.value.lon },
        end: { lat: endLocation.value.lat, lon: endLocation.value.lon },
        bbox: [min_lon, min_lat, max_lon, max_lat],
        smooth_path: true,
        return_sampled_points: true
      })
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => null)
      const errMsg = errData && errData.detail ? errData.detail : 'Failed to calculate route from backend.'
      throw new Error(errMsg)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalData = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() // keep incomplete chunk at the end
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.substring(6))
            if (payload.step === 'status') {
              estTime.value = payload.message
            } else if (payload.step === 'complete') {
              finalData = payload.result
            } else if (payload.step === 'error') {
              throw new Error(payload.message || 'Error occurred on server.')
            }
          } catch (err) {
            if (err.message && err.message !== 'Unexpected end of JSON input') {
              throw err
            }
          }
        }
      }
    }
    
    const data = finalData
    if (!data) {
      throw new Error('No route response received from server.')
    }
    
    if (data.status === 'success' && data.path.length > 0) {
      // Backend returns [{x: lon, y: lat, z: elev}, ...]
      const fullPath = [...data.path];
      
      // Because the backend now injects exact requested start and end points into the Delaunay 
      // triangulation before pathfinding, the first and last nodes naturally match the markers exactly.
      console.log('Successfully retrieved path from backend!')
      console.log('Number of nodes:', fullPath.length)
      
      // Save path, sampled points, and simplices for 2D/3D (Plotly) visualization
      currentPathData.value = fullPath;
      currentSampledPoints.value = data.sampled_points || null;
      currentSimplices.value = data.simplices || null;
      currentBBox.value = [min_lon, min_lat, max_lon, max_lat];
      drawRoute();
      if (is3DView.value) {
        nextTick(() => renderPlotly3D())
      }
      
      // Dummy distance calculation for UI purposes
      const dx = endLocation.value.lon - startLocation.value.lon
      const dy = endLocation.value.lat - startLocation.value.lat
      const straightLineDist = Math.sqrt(dx*dx + dy*dy) * 111 
      const estimatedDist = (straightLineDist * 1.5).toFixed(1)
      
      distance.value = `${estimatedDist} km`
      estTime.value = 'Ready'
      
      // Fit bounds to route
      map.value.fitBounds(routePolyline.getBounds(), { padding: [50, 50] })
    } else {
      estTime.value = 'Error'
      alert(data.message || 'Could not find a path.')
    }
    
  } catch (error) {
    console.error('Error fetching route:', error)
    estTime.value = 'Error'
    alert(error.message || 'Error connecting to backend API.')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="flex-grow flex flex-col md:flex-row min-h-screen pt-[72px]">
    <!-- SIDEBAR -->
    <aside class="w-full md:w-96 bg-dark p-6 flex flex-col gap-8 shadow-2xl z-[1000] overflow-y-auto">
      <div>
        <h2 class="text-2xl font-bold mb-2">Route planner</h2>
        <p class="text-sm ">Configure your start and end points to generate the optimal path</p>
      </div>

      <div class="space-y-6">
        <!-- Map Style -->
        <div>
          <label class="block text-sm mb-3">Map Style</label>
          <select v-model="currentMapStyleId" class="w-full bg-dark text-sm p-2 rounded border-2 border-white/20 focus:ring-0 outline-0 text-white cursor-pointer">
            <option v-for="style in mapStyles" :key="style.id" :value="style.id">
              {{ style.name }}
            </option>
          </select>
        </div>

        <!-- Elevation Color Toggle -->
        <div>
          <div class="mb-3">
            <label class="block text-sm font-medium text-white cursor-pointer" @click="colorMode = colorMode === 'elevation' ? 'primary' : 'elevation'">Elevation colors</label>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="colorMode" true-value="elevation" false-value="primary" class="sr-only peer">
            <div class="w-11 h-6 bg-white/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        <!-- Start Point -->
        <div class="bg-dark-alt p-5 rounded-lg shadow-inner">
          <label class="block text-l mb-3">Start Location</label>
          <div class="flex gap-3 items-center">
            <div class="w-3 h-3 rounded-full bg-blue-500 flex-shrink-0"></div>
            <input type="text" :value="startLocation ? `${startLocation.lat.toFixed(5)}, ${startLocation.lon.toFixed(5)}` : ''" placeholder="Click 'Pin' to set..." class="w-full bg-transparent text-sm focus:outline-none focus:border-primary transition-colors text-white cursor-default" readonly />
            <button @click="pinningMode = pinningMode === 'start' ? null : 'start'" :class="['flex items-center gap-1 px-3 py-1.5 border border-2 border-blue-500 text-xs font-semibold rounded transition-colors', pinningMode === 'start' ? 'bg-blue-500 text-dark' : 'text-blue-500']">
              <svg class="w-4 h-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M11.906 1.994a8.002 8.002 0 0 1 8.09 8.421 7.996 7.996 0 0 1-1.297 3.957.996.996 0 0 1-.133.204l-.108.129c-.178.243-.37.477-.573.699l-5.112 6.224a1 1 0 0 1-1.545 0L5.982 15.26l-.002-.002a18.146 18.146 0 0 1-.309-.38l-.133-.163a.999.999 0 0 1-.13-.202 7.995 7.995 0 0 1 6.498-12.518ZM15 9.997a3 3 0 1 1-5.999 0 3 3 0 0 1 5.999 0Z" clip-rule="evenodd"/></svg>
              Pin
            </button>
          </div>
        </div>

        <!-- End Point -->
        <div class="bg-dark-alt p-5 rounded-lg shadow-inner">
          <label class="block text-l mb-3 ">End Location</label>
          <div class="flex gap-3 items-center">
            <div class="w-3 h-3 rounded-full bg-red-500 flex-shrink-0"></div>
            <input type="text" :value="endLocation ? `${endLocation.lat.toFixed(5)}, ${endLocation.lon.toFixed(5)}` : ''" placeholder="Click 'Pin' to set..." class="w-full bg-transparent text-sm focus:outline-none focus:border-primary transition-colors text-white cursor-default" readonly />
            <button @click="pinningMode = pinningMode === 'end' ? null : 'end'" :class="['flex items-center gap-1 px-3 py-1.5 border border-2 border-red-500 text-xs font-semibold rounded transition-colors', pinningMode === 'end' ? 'bg-red-500 text-dark' : 'text-red-500']">
              <svg class="w-4 h-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M11.906 1.994a8.002 8.002 0 0 1 8.09 8.421 7.996 7.996 0 0 1-1.297 3.957.996.996 0 0 1-.133.204l-.108.129c-.178.243-.37.477-.573.699l-5.112 6.224a1 1 0 0 1-1.545 0L5.982 15.26l-.002-.002a18.146 18.146 0 0 1-.309-.38l-.133-.163a.999.999 0 0 1-.13-.202 7.995 7.995 0 0 1 6.498-12.518ZM15 9.997a3 3 0 1 1-5.999 0 3 3 0 0 1 5.999 0Z" clip-rule="evenodd"/></svg>
              Pin
            </button>
          </div>
        </div>
      </div>

      <div class="mt-auto pt-6 space-y-4">
        <div class="flex items-center justify-between text-sm text-gray-400 px-1">
          <span>Distance</span>
          <span>{{ distance }}</span>
        </div>
        <div class="flex items-center justify-between text-sm text-gray-400 px-1">
          <span>Status</span>
          <span>{{ estTime }}</span>
        </div>
        <button 
          @click="calculateRoute" 
          :disabled="!startLocation || !endLocation || isLoading"
          class="btn btn-outline w-full relative overflow-hidden flex justify-center items-center mt-4 disabled:cursor-not-allowed"
          :class="{'opacity-50': !startLocation || !endLocation}"
        >
          <div 
            class="absolute inset-y-0 left-0 bg-primary/30" 
            :style="{ 
              width: isLoading ? '95%' : '0%', 
              opacity: isLoading ? '1' : '0', 
              transition: isLoading ? 'width 45s ease-out' : 'width 0s, opacity 0.3s' 
            }"
          ></div>
          <span class="relative z-10">{{ isLoading ? 'Processing' : 'Calculate Route' }}</span>
        </button>
      </div>
    </aside>

    <!-- MAP & 3D PLOTLY CONTAINER -->
    <main class="flex-1 relative min-h-[500px]" :class="{ 'map-dark-filter': !is3DView && isDarkFilter }">
      <!-- Floating View Toggle Button (Top Middle of Map) -->
      <transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="transform -translate-y-4 scale-95 opacity-0"
        enter-to-class="transform translate-y-0 scale-100 opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="transform translate-y-0 scale-100 opacity-100"
        leave-to-class="transform -translate-y-4 scale-95 opacity-0"
      >
        <div 
          v-if="currentPathData && currentPathData.length > 0"
          class="fixed top-[92px] left-1/2 transform -translate-x-1/2 z-[500] pointer-events-auto"
        >
          <button 
            @click="toggle3DView"
            class="px-6 py-3 bg-[#de1047] hover:bg-[#e81952] text-white text-sm font-semibold rounded-full shadow-2xl hover:shadow-[#de1047]/50 border border-white/20 flex items-center gap-2.5 transition-all duration-200 cursor-pointer backdrop-blur-md hover:scale-105 active:scale-95"
          >
            <svg v-if="!is3DView" class="w-4 h-4 text-white/90 animate-pulse" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
            <svg v-else class="w-4 h-4 text-white/90" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span>{{ is3DView ? 'Switch back to 2D Map' : 'Show 3D visualisation of the terrain' }}</span>
          </button>
        </div>
      </transition>

      <!-- Leaflet 2D Map -->
      <div id="map" v-show="!is3DView" class="absolute inset-0 z-0"></div>

      <!-- Plotly 3D Map -->
      <div id="plotly-3d-map" v-show="is3DView" class="absolute inset-0 z-0 bg-[#0c0714]"></div>
    </main>
  </div>
</template>

<style>
/* Leaflet relies on global CSS for some of these dynamic elements, so no scoped */
.custom-div-icon {
  background: transparent;
  border: none;
}

/* Dark mode hack for map tiles */
.map-dark-filter .leaflet-tile-pane {
  filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
}
</style>
