<script setup lang="ts">
import gsap from 'gsap'

// Deterministic point layout (no Math.random — must match between SSR and
// client hydration). Loosely scattered, not grid-aligned.
const ambient = [
  [40, 40], [90, 80], [30, 150], [60, 250], [20, 280],
  [120, 30], [200, 40], [280, 30], [400, 50], [440, 100],
  [420, 180], [450, 260], [380, 280], [300, 270], [220, 290],
  [140, 270], [70, 190], [400, 140], [10, 60], [470, 200],
]

const query: [number, number] = [240, 160]
const neighbors: [number, number][] = [
  [150, 110],
  [320, 90],
  [180, 230],
  [340, 220],
]

const props = withDefaults(defineProps<{ animated?: boolean }>(), { animated: true })

const root = ref<HTMLElement | null>(null)

if (props.animated) {
  useReveal(root, () => {
    if (!root.value) return
    const lines = root.value.querySelectorAll<SVGLineElement>('.vf-line')
    lines.forEach((line) => {
      const len = line.getTotalLength()
      gsap.set(line, { strokeDasharray: len, strokeDashoffset: len })
      gsap.to(line, { strokeDashoffset: 0, duration: 0.9, ease: 'power2.out', delay: 0.3 })
    })
  })
}
</script>

<template>
  <svg ref="root" viewBox="0 0 480 320" class="h-full w-full" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="vf-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#7C6CFF" />
        <stop offset="100%" stop-color="#34E2C4" />
      </linearGradient>
    </defs>

    <circle
      v-for="([x, y], i) in ambient"
      :key="`a-${i}`"
      :cx="x"
      :cy="y"
      r="2"
      class="fill-dust/40"
    />

    <line
      v-for="([x, y], i) in neighbors"
      :key="`l-${i}`"
      class="vf-line"
      :x1="query[0]"
      :y1="query[1]"
      :x2="x"
      :y2="y"
      stroke="url(#vf-gradient)"
      stroke-width="1.5"
    />

    <circle
      v-for="([x, y], i) in neighbors"
      :key="`n-${i}`"
      :cx="x"
      :cy="y"
      r="3.5"
      class="fill-pulse"
    />

    <circle :cx="query[0]" :cy="query[1]" r="5" class="fill-signal vf-query" />
  </svg>
</template>

<style scoped>
.vf-query {
  animation: vf-pulse 3.2s ease-in-out infinite;
  transform-origin: center;
  transform-box: fill-box;
}

@media (prefers-reduced-motion: reduce) {
  .vf-query {
    animation: none;
  }
}

@keyframes vf-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.35);
    opacity: 0.7;
  }
}
</style>
