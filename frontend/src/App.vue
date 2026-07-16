<script setup>
import HomeView from './views/HomeView.vue'
import Navbar from './components/Navbar.vue'
import Footer from './components/Footer.vue'
</script>

<template>
  <div class="flex flex-col min-h-screen font-body text-white">
    <Navbar />
    
    <main>
      <HomeView />
    </main>

    <Footer />
  </div>
</template>
