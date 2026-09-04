<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    text: string
    /** Accessible name AND visible label — every copy button on the page
     * names its own payload ("Copy the config", "Copy the Docker command"),
     * never a bare "Copy", so two buttons never share an accessible name. */
    label: string
    /** 'primary' = the ink-filled CTA (masthead, hero, colophon — one
     * artifact, three places). 'plate' = the small outlined button in a
     * CodePlate header, used everywhere else. */
    variant?: 'primary' | 'plate'
    /** Swap ink/paper on the primary variant — the colophon sits on an ink
     * ground, so its copy of this same button has to fill paper instead. */
    invert?: boolean
  }>(),
  { variant: 'plate', invert: false }
)

type State = 'idle' | 'copied' | 'failed'
const state = ref<State>('idle')
const announcement = ref('')
let resetTimer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  clearTimeout(resetTimer)
  try {
    if (!navigator.clipboard) throw new Error('Clipboard API unavailable')
    await navigator.clipboard.writeText(props.text)
    state.value = 'copied'
    announcement.value = 'Config copied to the clipboard.'
    resetTimer = setTimeout(() => (state.value = 'idle'), 1800)
  } catch {
    // ponytail: no visible code plate to highlight from this generic
    // button, so the fallback selects the payload in an offscreen textarea
    // instead of the on-page block a plate-specific button could target —
    // same "text is selected, press Ctrl/Cmd+C" contract either way.
    selectFallback()
    state.value = 'failed'
    announcement.value = 'Copy failed. The text is selected — press Control C or Command C.'
  }
}

function selectFallback() {
  const el = document.createElement('textarea')
  el.value = props.text
  el.readOnly = true
  el.setAttribute('aria-hidden', 'true')
  el.style.position = 'fixed'
  el.style.top = '0'
  el.style.left = '0'
  el.style.opacity = '0.01'
  el.style.width = '1px'
  el.style.height = '1px'
  document.body.appendChild(el)
  el.focus()
  el.select()
  el.addEventListener('blur', () => el.remove(), { once: true })
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center justify-center gap-2 border px-2.5 py-2 text-center text-ui transition-colors sm:min-w-[22ch] sm:px-4"
    :class="[
      variant === 'primary' ? 'min-h-11 rounded-sm' : 'min-h-10 rounded-sm text-[0.9375rem]',
      state === 'failed'
        ? 'border-2 border-spot text-spot'
        : variant === 'primary'
          ? invert
            ? 'border-paper bg-paper text-ink hover:bg-transparent hover:text-paper'
            : 'border-ink bg-ink text-paper hover:bg-transparent hover:text-ink'
          : 'border-ink text-ink hover:bg-ink hover:text-paper',
    ]"
    :aria-label="state === 'failed' ? `${label} — copy failed, text selected` : label"
    @click="copy"
  >
    <span aria-hidden="true">{{ state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed — text selected' : label }}</span>
  </button>
  <p class="sr-only" role="status" aria-live="polite">{{ announcement }}</p>
</template>
