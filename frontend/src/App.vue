<script setup>
import Navbar from './components/Navbar.vue'
import HomeView from './views/HomeView.vue'
</script>

<template>
  <div class="app-container">
    <Navbar />
    <main>
      <HomeView />
    </main>
  </div>
</template>

<style>
/* Remove default margins/padding if they exist */
body {
  margin: 0;
  padding: 0;
  font-family: sans-serif;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
