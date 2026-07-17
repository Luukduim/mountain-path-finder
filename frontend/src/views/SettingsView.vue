<script setup>
import { ref, onMounted } from 'vue'
import { toast } from 'vue3-toastify'

const settings = ref({})
const originalTypes = ref({})
const isLoading = ref(false)
const isSaving = ref(false)

const sliderConfig = {
  SMOOTH_PATH_LAMBDA: { min: 1, max: 1000, step: 1 },
  MAIN_SLOPE_PENALTY_ALPHA: { min: 1, max: 10000, step: 100 },
  WATER_CROSSING_PENALTY: { min: 0, max: 2000, step: 50 }
}

onMounted(async () => {
  await fetchSettings()
})

const fetchSettings = async () => {
  isLoading.value = true
  try {
    const res = await fetch('http://localhost:8000/api/settings/')
    if (res.ok) {
      const data = await res.json()
      
      const types = {}
      for (const key in data) {
        types[key] = typeof data[key]
      }
      originalTypes.value = types
      settings.value = data
    }
  } catch (err) {
    console.error(err)
    toast.error('Failed to load settings.', { theme: 'dark' })
  } finally {
    isLoading.value = false
  }
}

const waitForBackend = async () => {
  let isUp = false
  let retries = 0
  const maxRetries = 30 // 15 seconds total
  
  // Wait 1 second before first poll to let Uvicorn begin restart
  await new Promise(r => setTimeout(r, 1000))
  
  while (!isUp && retries < maxRetries) {
    try {
      const res = await fetch('http://localhost:8000/health')
      if (res.ok) {
        isUp = true
      } else {
        retries++
        await new Promise(r => setTimeout(r, 500))
      }
    } catch (e) {
      retries++
      await new Promise(r => setTimeout(r, 500))
    }
  }
  
  if (!isUp) {
    throw new Error('Backend failed to restart in time.')
  }
}

const saveSettings = async () => {
  isSaving.value = true
  
  const payload = {}
  for (const [k, v] of Object.entries(settings.value)) {
    if (originalTypes.value[k] === 'number') {
      payload[k] = Number(v)
    } else {
      payload[k] = v
    }
  }

  try {
    const res = await fetch('http://localhost:8000/api/settings/', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok) {
      toast.info('Restarting backend', { autoClose: 3000, theme: 'dark' })
      await waitForBackend()
      toast.success('Settings saved successfully', { theme: 'dark' })
    } else {
      toast.error('Error saving settings.', { theme: 'dark' })
    }
  } catch (err) {
    console.error(err)
    toast.error('Failed to save settings or backend failed to restart.', { theme: 'dark' })
  } finally {
    isSaving.value = false
  }
}

const formatLabel = (key) => {
  const spaced = key.replace(/_/g, ' ').toLowerCase()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

const resetToDefaults = () => {
  if ('SMOOTH_PATH' in settings.value) settings.value.SMOOTH_PATH = true
  if ('SMOOTH_PATH_LAMBDA' in settings.value) settings.value.SMOOTH_PATH_LAMBDA = 250
  if ('MAIN_SLOPE_PENALTY_ALPHA' in settings.value) settings.value.MAIN_SLOPE_PENALTY_ALPHA = 5000
  if ('WATER_CROSSING_PENALTY' in settings.value) settings.value.WATER_CROSSING_PENALTY = 500.0
}

</script>

<template>
  <div class="min-h-screen mt-20 bg-dark flex justify-left p-8">
    <div class="w-full max-w-5xl flex flex-col">
      
      <!-- Header -->
      <div class="flex justify-between items-center ">
        <div>
          <h2 class="text-2xl font-bold text-white">Settings</h2>
          <p class="text-sm text-gray-400 mt-2">Tweak the backend parameters (Warning: saving restarts the server)</p>
        </div>
      </div>

      <!-- Body -->
      <div class="overflow-y-auto max-w-2xl mt-6">
        <div v-if="isLoading" class="flex justify-center p-12">
          <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
        </div>
        
        <div v-else class="flex flex-col gap-6">
          <div v-for="(value, key) in settings" :key="key" class="rounded-lg transition-colors">
            <label class="block text-l mb-3" :title="key">{{ formatLabel(key) }}</label>
            
            <!-- Boolean Toggle -->
            <template v-if="originalTypes[key] === 'boolean'">
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings[key]" class="sr-only peer">
                <div class="w-11 h-6 bg-white/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-white/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </template>
            
            <!-- Number Input -->
            <template v-else-if="originalTypes[key] === 'number'">
              <div class="flex flex-col gap-3 mt-1">
                <input type="number" v-model.number="settings[key]" :step="sliderConfig[key]?.step || 'any'" class="w-full bg-transparent text-base text-white border-b border-white/20 focus:border-primary outline-none py-1 focus:ring-0 hover-transition">
                <input 
                  v-if="sliderConfig[key]"
                  type="range" 
                  v-model.number="settings[key]" 
                  :min="sliderConfig[key].min" 
                  :max="sliderConfig[key].max" 
                  :step="sliderConfig[key].step"
                  class="w-full h-1.5 bg-primary/20 rounded-lg appearance-none cursor-pointer accent-primary"
                >
              </div>
            </template>
            
            <!-- String Input -->
            <template v-else>
              <input type="text" v-model="settings[key]" class="w-full bg-transparent text-base text-white outline-none py-1 focus:ring-0 hover-transition">
            </template>
          </div>
        </div>
        <!-- Footer -->
        <div class="flex flex-col mt-8">
          <div class="flex gap-4">
            <button 
              @click="resetToDefaults"
              :disabled="isSaving"
              class="w-full border-2 border-white text-white hover:bg-white hover:text-dark font-bold px-8 py-3 rounded transition-colors disabled:opacity-50 mt-4 flex justify-center items-center"
            >
              Reset to defaults
            </button>
            <button 
              @click="saveSettings" 
              :disabled="isSaving"
              class="btn btn-outline w-full relative overflow-hidden flex items-center justify-center mt-4 disabled:cursor-not-allowed"
              :class="{'opacity-50': isSaving}"
            >
              <div 
                class="absolute inset-y-0 left-0 bg-primary/30" 
                :style="{ 
                  width: isSaving ? '95%' : '0%', 
                  opacity: isSaving ? '1' : '0', 
                  transition: isSaving ? 'width 5s ease-out' : 'width 0s, opacity 0.3s' 
                }"
              ></div>
              <span class="relative z-10">{{ isSaving ? 'Saving' : 'Save' }}</span>
            </button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
