<template>
  <div class="w-full">
    <!-- HERO SECTION -->
    <section class="min-h-screen flex items-center justify-center bg-hero bg-cover bg-center text-center">
      <div class="relative z-10 px-8">
        <h1 class="text-5xl md:text-6xl font-bold leading-tight mb-8">
          Intelligent, <span class="text-primary font-logo">physics-based</span> pathfinding<br>for your next mountain expedition
        </h1>
        <div class="flex gap-4 justify-center">
          <button class="btn btn-outline">
            Create your personal route
          </button>
          <button class="btn btn-outline-white">
            More information
          </button>
        </div>
      </div>
    </section>

    <!-- ACTION SECTION -->
    <section class="py-20 px-16 text-center bg-action bg-cover bg-top">
      <h2 class="text-4xl font-bold mb-16">See the algorithm in <span class="text-primary font-logo">action</span></h2>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-[90%] mx-auto text-left mb-16">
        <!-- Step 1 -->
        <div class="flex flex-col">
          <div class="bg-primary text-gray-950 self-start px-3 py-1 rounded font-logo font-bold text-xl mb-4">Step 1</div>
          <h3 class="text-lg font-semibold mb-2">Pick a section of the map</h3>
          <p class="text-gray-400 text-sm mb-6 min-h-[40px]">It will be picked from the center of the screen</p>
          <div class="aspect-square rounded-lg flex items-center justify-center">
            <img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeWRjYnBiams5YzY3MW5xd3I3bXNkeXpsbXR2eWIwamozd3FzNnpjcyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/aD7el9eHQ6qjBfeFdm/giphy.gif" alt="Step 1 Animation" class="w-full opacity-10 h-full object-cover" />
          </div>
        </div>
        
        <!-- Step 2 -->
        <div class="flex flex-col">
          <div class="bg-primary text-dark self-start px-3 py-1 rounded font-logo font-bold text-xl mb-4">Step 2</div>
          <h3 class="text-lg font-semibold mb-2">Pin the start- and endpoint</h3>
          <p class="text-gray-400 text-sm mb-6 min-h-[40px]">The optimal route will be found between points</p>
          <div class=" aspect-square rounded-lg flex items-center justify-center">
            <img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeWRjYnBiams5YzY3MW5xd3I3bXNkeXpsbXR2eWIwamozd3FzNnpjcyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/aD7el9eHQ6qjBfeFdm/giphy.gif" alt="Step 2 Animation" class="w-full opacity-10 h-full object-cover" />
          </div>
        </div>
        
        <!-- Step 3 -->
        <div class="flex flex-col">
          <div class="bg-primary text-dark self-start px-3 py-1 rounded font-logo font-bold text-xl mb-4">Step 3</div>
          <h3 class="text-lg font-semibold mb-2">View the route</h3>
          <p class="text-gray-400 text-sm mb-6 min-h-[40px]">Check the generated route and tweak settings</p>
          <div class="aspect-square rounded-lg flex items-center justify-center">
            <img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeWRjYnBiams5YzY3MW5xd3I3bXNkeXpsbXR2eWIwamozd3FzNnpjcyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/aD7el9eHQ6qjBfeFdm/giphy.gif" alt="Step 3 Animation" class="w-full opacity-10 h-full object-cover" />
          </div>
        </div>
      </div>
      
      <div class="mt-8">
        <button class="btn btn-outline">
          Start now
        </button>
      </div>
    </section>

    <!-- FEATURES SECTION -->
    <section class="relative py-20 px-16 bg-features h-screen bg-cover bg-center text-center">
      
      <div class="relative z-10">
        <h2 class="text-4xl font-bold mb-16"><span class="text-primary font-logo ">Features</span> of our application</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-[80%] mx-auto text-left mb-16">
          <!-- Feature 1 -->
          <div class="border border-white/10 rounded-lg py-12 px-8">
            <h3 class="text-2xl font-semibold mb-8">Physics-based routing</h3>
            <ul class="space-y-8">
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Gravity-aware:</strong> Advanced slope penalties avoid sheer cliffs.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Smart crossings:</strong> Seeks narrow streams instead of wide lakes.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Realistic paths:</strong> Naturally generates traversable switchbacks.
              </li>
            </ul>
          </div>
          
          <!-- Feature 2 -->
          <div class="border border-white/10 rounded-lg py-12 px-8">
            <h3 class="text-2xl font-semibold mb-8">Simple live topography</h3>
            <ul class="space-y-8">
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Zero downloads:</strong> No massive geographic files required.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">On-the-fly merging:</strong> Fetches high-resolution elevation instantly.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Direct streaming:</strong> Loads exactly the data you need, right in your browser.
              </li>
            </ul>
          </div>
          
          <!-- Feature 3 -->
          <div class="border border-white/10 rounded-lg py-12 px-8">
            <h3 class="text-2xl font-semibold mb-8">Adaptive precision</h3>
            <ul class="space-y-8">
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Quadtree tech:</strong> Dynamically adjusts calculation nodes.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">High detail:</strong> Pinpoint accuracy in rugged, complex terrain.
              </li>
              <li class="relative pl-5 text-gray-400 text-xl">
                <span class="absolute left-0 top-[-2px] text-primary text-2xl leading-none">&bull;</span>
                <strong class="text-primary font-semibold">Max speed:</strong> Optimizes flat plateaus for lightning-fast performance.
              </li>
            </ul>
          </div>
        </div>
        
        <div>
          <button class="btn btn-outline-white">
            Learn more
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.bg-hero {
  background-image: url('../assets/Background-1.png');
}
.bg-features {
  background-image: url('../assets/Background-2.png');
}
.bg-action {
  background-image: url('../assets/Background-3.png');
}
</style>
