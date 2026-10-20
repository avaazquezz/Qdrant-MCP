<script setup lang="ts">
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { onMounted, onUnmounted, ref } from 'vue'
import { useLanding } from '~/composables/useLanding'

// The margin ruler. Its entries are the page's real sections in their real order, and the
// marker travels as the page scrolls: the "ruler" in "the instrument that measures".
// Purely a navigation aid: every target is also reachable from the masthead.
const { copy } = useLanding()

const sections = [
  { id: 'method', label: copy.nav.method },
  { id: 'architecture', label: copy.nav.architecture },
  { id: 'scenarios', label: copy.nav.scenarios },
  { id: 'tools', label: copy.nav.tools },
  { id: 'log', label: copy.nav.log },
  { id: 'quality', label: copy.nav.quality },
]

const active = ref('')
// The ruler sits over the page; on the dark contact section its ink-coloured marks would
// vanish, so it steps aside there instead of being restyled for one section.
const overDark = ref(false)
const marker = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | undefined
let darkObserver: IntersectionObserver | undefined
let trigger: ScrollTrigger | undefined

onMounted(() => {
  // The section that crosses the middle band of the viewport is "current".
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) if (entry.isIntersecting) active.value = entry.target.id
    },
    { rootMargin: '-45% 0px -50% 0px' }
  )
  for (const s of sections) {
    const el = document.getElementById(s.id)
    if (el) observer.observe(el)
  }

  const contact = document.getElementById('contact')
  if (contact) {
    darkObserver = new IntersectionObserver(([entry]) => (overDark.value = entry?.isIntersecting ?? false), {
      rootMargin: '0px 0px -40% 0px',
    })
    darkObserver.observe(contact)
  }

  if (marker.value && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const setY = gsap.quickSetter(marker.value, 'y', 'px')
    trigger = ScrollTrigger.create({
      start: 0,
      end: 'max',
      onUpdate: (self) => setY(self.progress * 100 * 4.2),
    })
  }
})
onUnmounted(() => {
  observer?.disconnect()
  darkObserver?.disconnect()
  trigger?.kill()
})
</script>

<template>
  <nav
    :aria-label="copy.a11y.sections"
    class="pointer-events-none fixed left-4 top-1/2 z-40 hidden -translate-y-1/2 transition-opacity duration-300 2xl:block"
    :class="overDark ? 'opacity-0' : 'opacity-100'"
  >
    <div class="relative pl-5" :class="overDark ? '' : 'pointer-events-auto'">
      <!-- Ticks: a real ruler, one tick per 8 px. -->
      <div
        class="absolute bottom-0 left-0 top-0 w-2 border-l border-ink/60"
        style="background-image: repeating-linear-gradient(to bottom, currentColor 0 1px, transparent 1px 8px); color: rgb(21 23 28 / 0.35); background-size: 6px 100%; background-repeat: no-repeat"
        aria-hidden="true"
      />
      <span
        ref="marker"
        class="absolute -left-[3px] top-0 block h-2 w-2 rounded-full bg-spot"
        aria-hidden="true"
      />
      <ol class="space-y-3 py-1">
        <li v-for="(s, i) in sections" :key="s.id">
          <a
            :href="`#${s.id}`"
            class="group flex items-baseline gap-2 font-mono text-ordinal uppercase tracking-[0.12em] transition-colors duration-200"
            :class="active === s.id ? 'text-ink' : 'text-mist hover:text-graphite'"
            :aria-current="active === s.id ? 'true' : undefined"
          >
            <span class="measure">{{ String(i + 1).padStart(2, '0') }}</span>
            <span>{{ s.label }}</span>
          </a>
        </li>
      </ol>
    </div>
  </nav>
</template>
