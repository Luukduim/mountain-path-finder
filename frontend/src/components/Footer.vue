<template>
  <footer class="bg-dark px-16 py-16 grid grid-cols-[1fr_2fr_1fr] gap-8 mt-auto">
    <div>
      <div class="font-logo text-3xl font-bold">Fjellrouter</div>
    </div>
    
    <div class="text-white text-s">
      <p>Intelligent, physics-based pathfinding for the wild.</p>
      <p class="mt-2 opacity-60">&copy; 2026 Fjellrouter. All rights reserved.</p>
    </div>
    
    <div class="flex gap-16 text-s">
      <ul class="flex flex-col gap-2">
        <li><router-link to="/" class="hover:text-primary hover-transition">Home</router-link></li>
        <li><router-link to="/map" class="hover:text-primary hover-transition">Map</router-link></li>
        <li><a href="#" class="hover:text-primary hover-transition">Settings</a></li>
      </ul>
      <ul class="flex flex-col gap-2">
        <li><a href="#" class="hover:text-primary hover-transition">Backend repository</a></li>
        <li><a href="#" class="hover:text-primary hover-transition">Report an issue</a></li>
        <li><a href="#" class="hover:text-primary hover-transition">Contact</a></li>
      </ul>
    </div>
  </footer>
</template>

<script setup>
</script>
