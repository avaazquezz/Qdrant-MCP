<script setup lang="ts">
defineProps<{
  /** The header label — a filename or a short description ("docker-compose.yml", ".mcp.json"). */
  title: string
  code: string
  /** Accessible name for the copy button; defaults to a generic one built from `title`. */
  copyLabel?: string
}>()
</script>

<template>
  <div class="border border-ink">
    <div class="flex items-center justify-between gap-3 border-b border-ink bg-tint px-4 py-2">
      <p class="font-mono text-micro text-ink">{{ title }}</p>
      <UiCopyButton :text="code" :label="copyLabel ?? `Copy the ${title} snippet`" />
    </div>
    <pre class="overflow-x-auto bg-tint px-4 py-3 font-mono text-micro leading-relaxed text-ink"><code class="max-w-code [overflow-wrap:anywhere]">{{ code }}</code></pre>
  </div>
</template>
