<script setup lang="ts">
const props = defineProps<{ text: string; label?: string }>()

const copied = ref(false)
let resetTimer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  await navigator.clipboard.writeText(props.text)
  copied.value = true
  clearTimeout(resetTimer)
  resetTimer = setTimeout(() => (copied.value = false), 1800)
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 font-mono text-sm text-text-primary transition-colors hover:border-accent"
    @click="copy"
  >
    <span>{{ copied ? 'Copied' : label ?? 'Copy' }}</span>
  </button>
</template>
