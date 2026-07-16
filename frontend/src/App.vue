<script setup>
import Navbar from './components/Navbar.vue'
import Footer from './components/Footer.vue'
</script>

<template>
  <div class="flex flex-col min-h-screen font-body text-white">
    <Navbar />
    
    <main class="flex-grow">
      <router-view />
    </main>

    <Footer />
  </div>
</template>
