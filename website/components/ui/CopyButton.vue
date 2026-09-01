<script setup lang="ts">
const props = defineProps<{ text: string; label?: string }>()

const copied = ref(false)
let resetTimer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
  } catch {
    return
  }
  copied.value = true
  clearTimeout(resetTimer)
  resetTimer = setTimeout(() => (copied.value = false), 1800)
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-2 border border-hairline bg-graphite px-3 py-1.5 font-mono text-sm text-paper transition-all duration-150 hover:border-signal hover:text-signal active:scale-95"
    :class="{ 'border-pulse text-pulse': copied }"
    @click="copy"
  >
    <span>{{ copied ? 'Copied' : label ?? 'Copy' }}</span>
  </button>
</template>
