<script setup>
import { ref, shallowRef, onMounted, onUnmounted, watch, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

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

const currentMapStyleId = ref('osm')
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

let startMarker = null
let endMarker = null
let routePolyline = null

onMounted(() => {
  // Initialize Leaflet map
  map.value = L.map('map', {
    zoomControl: false // Custom placement below
  }).setView([60.445, 5.516], 11) // Default to Bergen area

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
    
    // Clear route when a point changes
    if (routePolyline) {
      map.value.removeLayer(routePolyline)
      routePolyline = null
    }
    
    distance.value = '-- km'
    estTime.value = '--'
  })
})

onUnmounted(() => {
  if (map.value) {
    map.value.remove()
  }
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

    console.log(min_lon, min_lat, max_lon, max_lat, "this should be the bbox")

    const response = await fetch('http://localhost:8000/api/pathfinding/find', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        start: { lat: startLocation.value.lat, lon: startLocation.value.lon },
        end: { lat: endLocation.value.lat, lon: endLocation.value.lon },
        bbox: [min_lon, min_lat, max_lon, max_lat],
        smooth_path: true
      })
    })
    
    if (!response.ok) {
      throw new Error('Network response was not ok')
    }
    
    const data = await response.json()
    
    if (data.status === 'success' && data.path.length > 0) {
      // Backend returns [{x: lon, y: lat, z: elev}, ...]
      // Leaflet polylines expect [lat, lon]
      const coordinates = data.path.map(p => [p.y, p.x])
      
      // The backend pathfinding runs on a discrete terrain grid, so the first and last 
      // nodes of the path are the centers of the nearest grid cells. To make the line 
      // perfectly connect to the markers visually, we add the exact coordinates.
      if (coordinates.length > 0) {
        coordinates.unshift([startLocation.value.lat, startLocation.value.lon])
        coordinates.push([endLocation.value.lat, endLocation.value.lon])
      }
      console.log('Successfully retrieved path from backend!')
      console.log('Number of nodes:', coordinates.length)
      console.log('Path coordinates [lat, lon]:', coordinates)
      
      if (routePolyline) {
        map.value.removeLayer(routePolyline)
      }
      
      // Draw path
      routePolyline = L.polyline(coordinates, {
        color: '#ff3b30',
        weight: 5,
        opacity: 0.95,
        lineCap: 'round',
        lineJoin: 'round',
        className: 'route-line'
      }).addTo(map.value)
      
      // Ensure the line renders behind the point markers
      routePolyline.bringToBack()
      
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
      alert(data.message || 'Could not find a path.')
    }
    
  } catch (error) {
    console.error('Error fetching route:', error)
    alert('Error connecting to backend API.')
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
        <h2 class="text-2xl font-bold  mb-2">Route planner</h2>
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
          <span>{{ isLoading ? 'Calculating' : estTime }}</span>
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

    <!-- MAP CONTAINER -->
    <main class="flex-1 relative min-h-[500px]" :class="{ 'map-dark-filter': isDarkFilter }">
      <div id="map" class="absolute inset-0 z-0"></div>
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
