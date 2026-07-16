<template>
  <div class="flex-grow flex flex-col md:flex-row min-h-screen pt-[72px]">
    <!-- SIDEBAR -->
    <aside class="w-full md:w-96 bg-dark border-r border-white/10 p-6 flex flex-col gap-8 shadow-2xl z-[1000] overflow-y-auto">
      <div>
        <h2 class="text-2xl font-bold font-logo text-primary mb-2">Route Planner</h2>
        <p class="text-sm text-gray-400">Configure your start and end points to generate the optimal path.</p>
      </div>

      <div class="space-y-6">
        <!-- Start Point -->
        <div class="bg-[#1E192D]/60 border border-white/5 p-5 rounded-lg shadow-inner">
          <label class="block text-xs uppercase tracking-wider font-semibold mb-3 text-gray-400">Start Location</label>
          <div class="flex gap-3 items-center">
            <div class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)] flex-shrink-0"></div>
            <input type="text" :value="startLocation ? `${startLocation.lat.toFixed(5)}, ${startLocation.lon.toFixed(5)}` : ''" placeholder="Click map to set..." class="w-full bg-transparent border-b border-white/10 pb-1 text-sm focus:outline-none focus:border-primary transition-colors text-white" readonly />
          </div>
        </div>

        <!-- End Point -->
        <div class="bg-[#1E192D]/60 border border-white/5 p-5 rounded-lg shadow-inner">
          <label class="block text-xs uppercase tracking-wider font-semibold mb-3 text-gray-400">End Location</label>
          <div class="flex gap-3 items-center">
            <div class="w-3 h-3 rounded-full bg-primary shadow-[0_0_10px_var(--color-primary)] flex-shrink-0"></div>
            <input type="text" :value="endLocation ? `${endLocation.lat.toFixed(5)}, ${endLocation.lon.toFixed(5)}` : ''" placeholder="Click map to set..." class="w-full bg-transparent border-b border-white/10 pb-1 text-sm focus:outline-none focus:border-primary transition-colors text-white" readonly />
          </div>
        </div>
      </div>

      <div class="mt-auto pt-6 space-y-4">
        <div class="flex items-center justify-between text-sm text-gray-400 px-1">
          <span>Distance</span>
          <span class="font-mono">{{ distance }}</span>
        </div>
        <div class="flex items-center justify-between text-sm text-gray-400 px-1">
          <span>Status</span>
          <span class="font-mono">{{ isLoading ? 'Calculating...' : estTime }}</span>
        </div>
        <button 
          @click="calculateRoute" 
          :disabled="!startLocation || !endLocation || isLoading"
          class="btn btn-outline w-full flex justify-center items-center mt-4 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ isLoading ? 'Processing...' : 'Calculate Route' }}
        </button>
      </div>
    </aside>

    <!-- MAP CONTAINER -->
    <main class="flex-1 relative min-h-[500px]">
      <div id="map" class="absolute inset-0 z-0"></div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const map = ref(null)

const startLocation = ref(null)
const endLocation = ref(null)
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

  // Use OpenTopoMap tiles (No API key needed!)
  L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 17,
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
  }).addTo(map.value)

  // Handle map clicks for setting points
  map.value.on('click', (e) => {
    const { lat, lng } = e.latlng
    
    // If start doesn't exist, or BOTH exist (we are resetting), set Start
    if (!startLocation.value || (startLocation.value && endLocation.value)) {
      startLocation.value = { lat, lon: lng }
      endLocation.value = null // Reset end
      
      const startIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color: #22c55e; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(34,197,94,0.8);"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      })
      
      // Update marker
      if (!startMarker) {
        startMarker = L.marker([lat, lng], { icon: startIcon }).addTo(map.value)
      } else {
        startMarker.setLatLng([lat, lng])
      }
      
      // Remove end marker
      if (endMarker) {
        map.value.removeLayer(endMarker)
        endMarker = null
      }
      
      // Clear route
      if (routePolyline) {
        map.value.removeLayer(routePolyline)
        routePolyline = null
      }
      
      distance.value = '-- km'
      estTime.value = '--'
      
    } else if (!endLocation.value) {
      // Set End
      endLocation.value = { lat, lon: lng }
      
      const endIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color: #00d2ff; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,210,255,0.8);"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      })
      
      if (!endMarker) {
        endMarker = L.marker([lat, lng], { icon: endIcon }).addTo(map.value)
      } else {
        endMarker.setLatLng([lat, lng])
      }
    }
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
      console.log('Successfully retrieved path from backend!')
      console.log('Number of nodes:', coordinates.length)
      console.log('Path coordinates [lat, lon]:', coordinates)
      
      if (routePolyline) {
        map.value.removeLayer(routePolyline)
      }
      
      // Draw path
      routePolyline = L.polyline(coordinates, {
        color: '#00d2ff',
        weight: 5,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round',
        className: 'route-line'
      }).addTo(map.value)
      
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

<style>
/* Leaflet relies on global CSS for some of these dynamic elements, so no scoped */
.custom-div-icon {
  background: transparent;
  border: none;
}
.route-line {
  filter: drop-shadow(0 0 8px rgba(0, 210, 255, 0.6));
}
</style>
