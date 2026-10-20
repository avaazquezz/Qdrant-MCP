<script setup lang="ts">
import gsap from 'gsap'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import tools from '~/data/tools.generated.json'
import type { Step } from '~/content/types'
import { pretty } from '~/composables/usePretty'
import { useLanding } from '~/composables/useLanding'

const props = defineProps<{ steps: Step[]; captions: string[] }>()

const { copy, t } = useLanding()
const labels = copy.scenarios

const current = ref(0)
const playing = ref(false)
const shown = reactive({ chars: 0, resultVisible: false, running: false })
let started = false
let tween: gsap.core.Tween | undefined
let timer: ReturnType<typeof setTimeout> | undefined
const root = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | undefined
let calm = false

const step = computed(() => props.steps[current.value]!)
const callName = computed(() => step.value.tool ?? step.value.method ?? '')
const argsText = computed(() => pretty(step.value.arguments ?? step.value.environment ?? {}, 2))
const resultText = computed(() => (step.value.ok ? pretty(step.value.result, 4) : (step.value.error ?? '')))
const meta = computed(() => tools.find((tool) => tool.name === step.value.tool))
const last = computed(() => current.value === props.steps.length - 1)

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** Minimal JSON colouring. Keys dim, strings bright, numbers and literals accented. */
function highlight(json: string, accent: boolean): string {
  return escapeHtml(json).replace(
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)/g,
    (_, str: string | undefined, colon: string | undefined, lit: string | undefined, num: string | undefined) => {
      if (str) return colon ? `<span class="text-panel-dim">${str}</span>${colon}` : `<span class="text-panel-ink">${str}</span>`
      const token = (lit ?? num) as string
      return accent ? `<span class="text-[#E0334A]">${token}</span>` : token
    }
  )
}

const argsHtml = computed(() => highlight(argsText.value.slice(0, shown.chars), false))
const resultHtml = computed(() => highlight(resultText.value, true))

function clearTimers() {
  tween?.kill()
  clearTimeout(timer)
}

/** Reveal the current step: type the arguments, "run" it, then show what came back. */
function reveal() {
  clearTimers()
  shown.resultVisible = false
  shown.running = false
  if (calm) {
    shown.chars = argsText.value.length
    shown.resultVisible = true
    return
  }
  shown.chars = 0
  const length = argsText.value.length
  const state = { n: 0 }
  tween = gsap.to(state, {
    n: length,
    duration: Math.min(1.5, Math.max(0.45, length * 0.007)),
    ease: 'none',
    onUpdate: () => (shown.chars = Math.round(state.n)),
    onComplete: () => {
      shown.chars = length
      shown.running = true
      timer = setTimeout(() => {
        shown.running = false
        shown.resultVisible = true
        if (playing.value) timer = setTimeout(next, 1700)
      }, 420)
    },
  })
}

function next() {
  if (current.value < props.steps.length - 1) {
    current.value += 1
    reveal()
  } else {
    playing.value = false
  }
}

function play() {
  playing.value = true
  started = true
  if (last.value && shown.resultVisible) current.value = 0
  reveal()
}
function pause() {
  playing.value = false
  clearTimers()
  shown.chars = argsText.value.length
  shown.running = false
  shown.resultVisible = true
}
function select(index: number) {
  playing.value = false
  clearTimers()
  current.value = index
  shown.chars = argsText.value.length
  shown.running = false
  shown.resultVisible = true
}

onMounted(() => {
  calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  shown.chars = argsText.value.length
  shown.resultVisible = true
  if (calm) return
  // Starts by itself the first time it is on screen. After that it is the visitor's.
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry?.isIntersecting && !started) {
        started = true
        current.value = 0
        play()
      }
    },
    { threshold: 0.45 }
  )
  if (root.value) observer.observe(root.value)
})
onUnmounted(() => {
  clearTimers()
  observer?.disconnect()
})
watch(
  () => props.steps,
  () => {
    clearTimers()
    current.value = 0
    started = false
    playing.value = false
    shown.chars = argsText.value.length
    shown.resultVisible = true
  }
)
</script>

<template>
  <div ref="root" class="grid grid-cols-[minmax(0,1fr)] gap-px border border-ink bg-ink lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)]">
    <!-- The narration: one caption per real step. -->
    <ol class="bg-paper p-2 sm:p-3">
      <li v-for="(caption, i) in captions" :key="i">
        <button
          type="button"
          class="flex w-full gap-3 px-3 py-3 text-left transition-colors duration-200"
          :class="i === current ? 'bg-ink text-paper' : 'hover:bg-tint'"
          :aria-current="i === current ? 'step' : undefined"
          @click="select(i)"
        >
          <span class="measure mt-0.5 font-mono text-ordinal" :class="i === current ? 'text-paper/70' : 'text-graphite'">
            {{ String(i + 1).padStart(2, '0') }}
          </span>
          <span class="text-micro leading-snug">{{ caption }}</span>
        </button>
      </li>
    </ol>

    <!-- The console: what was called, and what the real server answered. -->
    <div class="on-panel flex min-h-[26rem] flex-col bg-panel text-panel-ink">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-panel-line px-4 py-3">
        <p class="flex flex-wrap items-center gap-2 font-mono text-ui font-semibold">
          <span class="text-panel-dim" aria-hidden="true">{{ step.method ? '↔' : '▸' }}</span>
          {{ callName }}
          <template v-if="meta">
            <span v-if="meta.read_only" class="border border-panel-line px-1.5 py-0.5 text-ordinal font-normal text-panel-dim">
              {{ copy.tools.badges.readOnly }}
            </span>
            <span v-if="meta.destructive" class="border border-[#E0334A] px-1.5 py-0.5 text-ordinal font-normal text-[#E0334A]">
              {{ copy.tools.badges.destructive }}
            </span>
          </template>
        </p>
        <p class="measure font-mono text-micro text-panel-dim" aria-live="polite">
          {{ t(labels.step, { n: current + 1, total: steps.length }) }}
        </p>
      </div>

      <div class="grid max-h-[30rem] flex-1 grid-cols-[minmax(0,1fr)] content-start gap-5 overflow-auto px-4 py-4" data-lenis-prevent>
        <div>
          <p class="mb-1.5 font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">
            {{ labels.arguments }}
          </p>
          <pre class="font-mono text-micro leading-relaxed [overflow-wrap:anywhere] whitespace-pre-wrap" v-html="argsHtml" />
        </div>

        <div class="min-h-[6rem]">
          <p class="mb-1.5 flex items-center gap-2 font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">
            {{ labels.result }}
            <span v-if="shown.running" class="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[#E0334A]" aria-hidden="true" />
            <span
              v-if="shown.resultVisible && !step.ok"
              class="border border-[#E0334A] px-1.5 py-0.5 text-[#E0334A]"
            >
              {{ labels.refused }}
            </span>
          </p>
          <Transition name="reveal">
            <pre
              v-if="shown.resultVisible"
              class="font-mono text-micro leading-relaxed [overflow-wrap:anywhere] whitespace-pre-wrap"
              :class="step.ok ? '' : 'text-panel-ink'"
              v-html="step.ok ? resultHtml : escapeHtml(resultText)"
            />
          </Transition>
        </div>
      </div>

      <div class="flex items-center gap-2 border-t border-panel-line px-4 py-3">
        <button
          type="button"
          class="min-h-9 border border-panel-line px-3 font-mono text-micro transition-colors duration-200 hover:border-panel-ink"
          @click="playing ? pause() : play()"
        >
          {{ playing ? labels.pause : last && shown.resultVisible && started ? labels.replay : labels.play }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reveal-enter-active {
  transition:
    opacity var(--dur-reveal) var(--ease-instrument),
    transform var(--dur-reveal) var(--ease-instrument);
}
.reveal-enter-from {
  opacity: 0;
  transform: translateY(0.5rem);
}
</style>
