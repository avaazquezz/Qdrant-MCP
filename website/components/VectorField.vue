<script setup lang="ts">
import gsap from 'gsap'
import { onMounted, onUnmounted, ref } from 'vue'

// A small, honest vector space: ~360 points in 3-D, projected onto a canvas. It is
// illustrative (the points are random clusters, and the page says so), but the part you can
// touch is real arithmetic: move the pointer and the five nearest points light up, with
// their Euclidean distances computed here, in your browser, every frame.
//
// One render loop (GSAP's ticker, shared with Lenis), paused when off-screen or when the
// visitor presses pause. Under reduced motion nothing moves by itself: the frame is drawn
// once and redrawn only when the visitor moves the pointer.

const props = defineProps<{
  label: string
  caption: string
  nearest: string
  pause: string
  play: string
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const readout = ref<string[]>([])
const paused = ref(false)

// Palette: the panel ground and the page's only accent. `spot` means "measured".
const INK = '#E9E6DD'
const DIM = '#9298A8'
const SPOT = '#E0334A' // spot, lifted a little so it keeps AA contrast on the dark panel
const LINE = '#2A2E38'

const COUNT = 360
const K = 5

interface Vec {
  x: number
  y: number
  z: number
}

/** Deterministic PRNG: the same constellation on every visit and in every build. */
function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function constellation(): Vec[] {
  const rand = mulberry32(20261020)
  const gauss = () => Math.sqrt(-2 * Math.log(rand() || 1e-9)) * Math.cos(2 * Math.PI * rand())
  const centers: Vec[] = [
    { x: -0.55, y: -0.2, z: 0.3 },
    { x: 0.5, y: 0.35, z: -0.25 },
    { x: 0.05, y: -0.5, z: -0.45 },
    { x: -0.1, y: 0.45, z: 0.5 },
  ]
  return Array.from({ length: COUNT }, (_, i) => {
    const c = centers[i % centers.length]!
    return { x: c.x + gauss() * 0.2, y: c.y + gauss() * 0.2, z: c.z + gauss() * 0.2 }
  })
}

const points = constellation()

let ctx: CanvasRenderingContext2D | null = null
let width = 0
let height = 0
let dpr = 1
let angle = 0
let pointer: { x: number; y: number } | null = null
let autoQuery = 0
let autoTimer = 0
let calm = false
let visible = true
let observer: IntersectionObserver | undefined
let resizeObserver: ResizeObserver | undefined
let readoutTimer = 0
const pulse = { r: 0, a: 0 }

// Rotated copies, refreshed each frame.
const rotated: Vec[] = points.map((p) => ({ ...p }))

function rotate() {
  const cy = Math.cos(angle)
  const sy = Math.sin(angle)
  const tilt = 0.38
  const cx = Math.cos(tilt)
  const sx = Math.sin(tilt)
  for (let i = 0; i < points.length; i++) {
    const p = points[i]!
    const x1 = p.x * cy + p.z * sy
    const z1 = -p.x * sy + p.z * cy
    const y2 = p.y * cx - z1 * sx
    const z2 = p.y * sx + z1 * cx
    const r = rotated[i]!
    r.x = x1
    r.y = y2
    r.z = z2
  }
}

const CAMERA = 3.2

function project(v: Vec): { x: number; y: number; s: number } {
  const scale = Math.min(width, height) * 0.42
  const s = CAMERA / (CAMERA - v.z)
  return { x: width / 2 + v.x * s * scale, y: height / 2 + v.y * s * scale, s }
}

/** The query is a point in the rotated model space: either the pointer (mapped to the z=0
 * plane) or, with no pointer, one of the points themselves. */
function queryVector(): Vec | null {
  if (pointer) {
    const scale = Math.min(width, height) * 0.42
    return { x: (pointer.x - width / 2) / scale, y: (pointer.y - height / 2) / scale, z: 0 }
  }
  if (calm) return null
  return rotated[autoQuery] ?? null
}

function nearestTo(q: Vec): { index: number; distance: number }[] {
  const found: { index: number; distance: number }[] = []
  for (let i = 0; i < rotated.length; i++) {
    const r = rotated[i]!
    const d = Math.hypot(r.x - q.x, r.y - q.y, r.z - q.z)
    if (d === 0) continue
    if (found.length < K || d < found[found.length - 1]!.distance) {
      found.push({ index: i, distance: d })
      found.sort((a, b) => a.distance - b.distance)
      if (found.length > K) found.pop()
    }
  }
  return found
}

function draw() {
  if (!ctx) return
  rotate()
  ctx.clearRect(0, 0, width, height)

  // Faint axes through the origin: just enough structure to read the space.
  ctx.strokeStyle = LINE
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(width / 2, height * 0.08)
  ctx.lineTo(width / 2, height * 0.92)
  ctx.moveTo(width * 0.06, height / 2)
  ctx.lineTo(width * 0.94, height / 2)
  ctx.stroke()

  const q = queryVector()
  const hits = q ? nearestTo(q) : []
  const lit = new Set(hits.map((h) => h.index))

  // Back to front, so nearer points paint over farther ones.
  const order = rotated.map((_, i) => i).sort((a, b) => rotated[a]!.z - rotated[b]!.z)
  for (const i of order) {
    if (lit.has(i)) continue
    const p = project(rotated[i]!)
    const depth = (rotated[i]!.z + 1) / 2
    ctx.fillStyle = DIM
    ctx.globalAlpha = 0.25 + 0.6 * Math.min(1, Math.max(0, depth))
    ctx.beginPath()
    ctx.arc(p.x, p.y, 1.1 * p.s * dpr * 0.7 + 0.6, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1

  if (q) {
    const origin = pointer ? { x: pointer.x, y: pointer.y } : project(q)
    ctx.strokeStyle = SPOT
    ctx.fillStyle = SPOT
    ctx.lineWidth = 1
    for (const h of hits) {
      const p = project(rotated[h.index]!)
      ctx.globalAlpha = 0.55
      ctx.beginPath()
      ctx.moveTo(origin.x, origin.y)
      ctx.lineTo(p.x, p.y)
      ctx.stroke()
      ctx.globalAlpha = 1
      ctx.beginPath()
      ctx.arc(p.x, p.y, 3.1, 0, Math.PI * 2)
      ctx.fill()
    }
    // The query itself: a hollow ring with a crosshair, plus an expanding pulse.
    ctx.strokeStyle = INK
    ctx.lineWidth = 1.25
    ctx.beginPath()
    ctx.arc(origin.x, origin.y, 6, 0, Math.PI * 2)
    ctx.moveTo(origin.x - 11, origin.y)
    ctx.lineTo(origin.x + 11, origin.y)
    ctx.moveTo(origin.x, origin.y - 11)
    ctx.lineTo(origin.x, origin.y + 11)
    ctx.stroke()
    if (pulse.a > 0.01) {
      ctx.strokeStyle = SPOT
      ctx.globalAlpha = pulse.a
      ctx.beginPath()
      ctx.arc(origin.x, origin.y, pulse.r, 0, Math.PI * 2)
      ctx.stroke()
      ctx.globalAlpha = 1
    }
  }

  updateReadout(hits)
}

function updateReadout(hits: { index: number; distance: number }[]) {
  const now = performance.now()
  if (now - readoutTimer < 120) return // text, not pixels: ~8 updates a second is plenty
  readoutTimer = now
  readout.value = hits.map((h) => h.distance.toFixed(3))
}

function firePulse() {
  pulse.r = 8
  pulse.a = 0.9
  gsap.to(pulse, { r: 90, a: 0, duration: 1.1, ease: 'power2.out', overwrite: true })
}

function tick(_time: number, deltaMs: number) {
  if (!visible || paused.value) return
  angle += (deltaMs / 1000) * 0.12
  if (!pointer) {
    autoTimer += deltaMs
    if (autoTimer > 2600) {
      autoTimer = 0
      autoQuery = Math.floor(Math.random() * points.length)
      firePulse()
    }
  }
  draw()
}

function resize() {
  const el = canvas.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2) // above 2x costs frames and buys nothing
  width = rect.width
  height = rect.height
  el.width = Math.round(width * dpr)
  el.height = Math.round(height * dpr)
  ctx = el.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
  draw()
}

function onPointerMove(e: PointerEvent) {
  const rect = canvas.value!.getBoundingClientRect()
  const first = pointer === null
  pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  if (first) firePulse()
  if (calm || paused.value) draw()
}
function onPointerLeave() {
  pointer = null
  if (calm || paused.value) draw()
}

onMounted(() => {
  calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resize()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(canvas.value!)
  observer = new IntersectionObserver(([entry]) => (visible = entry?.isIntersecting ?? true))
  observer.observe(canvas.value!)
  if (!calm) gsap.ticker.add(tick)
})
onUnmounted(() => {
  gsap.ticker.remove(tick)
  gsap.killTweensOf(pulse)
  observer?.disconnect()
  resizeObserver?.disconnect()
})
</script>

<template>
  <figure class="on-panel relative overflow-hidden bg-panel text-panel-ink">
    <canvas
      ref="canvas"
      class="block aspect-[5/4] w-full touch-pan-y sm:aspect-[4/3] lg:aspect-[1/1]"
      role="img"
      :aria-label="props.label"
      @pointermove="onPointerMove"
      @pointerleave="onPointerLeave"
    />
    <figcaption
      class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-t border-panel-line px-4 py-3 font-mono text-micro text-panel-dim"
    >
      <span>{{ props.caption }}</span>
      <span class="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span class="measure" aria-hidden="true">
          {{ props.nearest }}
          <span v-for="(d, i) in readout" :key="i" class="ml-1.5 text-panel-ink">{{ d }}</span>
        </span>
        <button
          type="button"
          class="min-h-9 border border-panel-line px-3 text-panel-ink transition-colors duration-200 hover:border-panel-ink"
          :aria-pressed="paused"
          @click="paused = !paused"
        >
          {{ paused ? props.play : props.pause }}
        </button>
      </span>
    </figcaption>
  </figure>
</template>
