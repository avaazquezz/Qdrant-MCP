<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    text: string
    /** Accessible name AND visible label: every copy button names its own payload, never a
     * bare "Copy", so two buttons never share an accessible name. */
    label: string
    copiedLabel?: string
    failedLabel?: string
    announceCopied?: string
    announceFailed?: string
    /** 'primary' = the ink-filled button; 'plate' = the small outlined one in a code header. */
    variant?: 'primary' | 'plate'
  }>(),
  {
    variant: 'plate',
    copiedLabel: 'Copied',
    failedLabel: 'Copy failed. The text is selected',
    announceCopied: 'Copied to the clipboard.',
    announceFailed: 'Copy failed. The text is selected: press Control C or Command C.',
  }
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
    announcement.value = props.announceCopied
    resetTimer = setTimeout(() => (state.value = 'idle'), 1800)
  } catch {
    // No on-page block to highlight from this generic button, so the fallback selects the
    // payload in an offscreen textarea: the same "text is selected, press Ctrl/Cmd+C" contract.
    selectFallback()
    state.value = 'failed'
    announcement.value = props.announceFailed
  }
}

function selectFallback() {
  const el = document.createElement('textarea')
  el.value = props.text
  el.readOnly = true
  el.setAttribute('aria-hidden', 'true')
  Object.assign(el.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    opacity: '0.01',
    width: '1px',
    height: '1px',
  })
  document.body.appendChild(el)
  el.focus()
  el.select()
  el.addEventListener('blur', () => el.remove(), { once: true })
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center justify-center gap-2 border px-3 py-2 text-center text-ui transition-colors duration-200"
    :class="[
      variant === 'primary' ? 'min-h-11 rounded-sm' : 'min-h-10 rounded-sm text-[0.9375rem]',
      state === 'failed'
        ? 'border-2 border-spot text-spot'
        : variant === 'primary'
          ? 'border-ink bg-ink text-paper hover:bg-transparent hover:text-ink'
          : 'border-ink text-ink hover:bg-ink hover:text-paper',
    ]"
    :aria-label="state === 'failed' ? `${label} (${failedLabel})` : label"
    @click="copy"
  >
    <span aria-hidden="true">{{ state === 'copied' ? copiedLabel : state === 'failed' ? failedLabel : label }}</span>
  </button>
  <p class="sr-only" role="status" aria-live="polite">{{ announcement }}</p>
</template>
