<script setup lang="ts">
import gsap from 'gsap'
import { onMounted, onUnmounted, ref } from 'vue'

// The probe: a ring that follows a fine pointer with spring physics and, over any element
// that carries `data-verified`, turns red and says what verifies it. It never replaces the
// native cursor, never intercepts a click, and does not exist at all for touch screens or
// under reduced motion.
const ring = ref<HTMLElement | null>(null)
const label = ref<HTMLElement | null>(null)
const text = ref('')
let cleanup: (() => void) | undefined

onMounted(() => {
  const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (!fine || calm || !ring.value || !label.value) return

  const moveX = gsap.quickTo(ring.value, 'x', { duration: 0.45, ease: 'power3' })
  const moveY = gsap.quickTo(ring.value, 'y', { duration: 0.45, ease: 'power3' })
  const labelX = gsap.quickTo(label.value, 'x', { duration: 0.6, ease: 'power3' })
  const labelY = gsap.quickTo(label.value, 'y', { duration: 0.6, ease: 'power3' })

  const onMove = (e: PointerEvent) => {
    ring.value!.dataset.active = 'true'
    moveX(e.clientX)
    moveY(e.clientY)
    labelX(e.clientX + 26)
    labelY(e.clientY + 22)
  }
  const onOver = (e: PointerEvent) => {
    const target = (e.target as Element | null)?.closest<HTMLElement>('[data-verified]')
    ring.value!.dataset.verified = target ? 'true' : 'false'
    text.value = target?.dataset.verified ?? ''
    gsap.to(ring.value!, { scale: target ? 1.35 : 1, duration: 0.3, overwrite: 'auto' })
  }
  const onLeave = () => {
    ring.value!.dataset.active = 'false'
  }

  window.addEventListener('pointermove', onMove, { passive: true })
  document.addEventListener('pointerover', onOver, { passive: true })
  document.documentElement.addEventListener('pointerleave', onLeave)
  cleanup = () => {
    window.removeEventListener('pointermove', onMove)
    document.removeEventListener('pointerover', onOver)
    document.documentElement.removeEventListener('pointerleave', onLeave)
  }
})
onUnmounted(() => cleanup?.())
</script>

<template>
  <div aria-hidden="true">
    <div ref="ring" class="probe-ring" data-active="false" data-verified="false" />
    <div
      ref="label"
      class="pointer-events-none fixed left-0 top-0 z-[61] max-w-[34ch] bg-ink px-2 py-1 font-mono text-micro text-paper transition-opacity duration-200"
      :class="text ? 'opacity-100' : 'opacity-0'"
    >
      <span class="font-semibold uppercase tracking-[0.08em]">verified</span> · {{ text }}
    </div>
  </div>
</template>
