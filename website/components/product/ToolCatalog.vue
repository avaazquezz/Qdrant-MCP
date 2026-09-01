<script setup lang="ts">
import tools from '~/data/tools.generated.json'

type Toolset = (typeof tools)[number]['toolset']

const toolsets = [...new Set(tools.map((t) => t.toolset))].sort() as Toolset[]
const active = ref<Toolset | 'all'>('all')

const filtered = computed(() =>
  active.value === 'all' ? tools : tools.filter((t) => t.toolset === active.value)
)

function firstParagraph(description: string) {
  return description.split('\n\n')[0]
}
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="rounded-full border px-3 py-1 font-mono text-xs transition-colors"
        :class="active === 'all' ? 'border-accent text-accent' : 'border-border text-text-secondary hover:text-text-primary'"
        @click="active = 'all'"
      >
        all ({{ tools.length }})
      </button>
      <button
        v-for="ts in toolsets"
        :key="ts"
        type="button"
        class="rounded-full border px-3 py-1 font-mono text-xs transition-colors"
        :class="active === ts ? 'border-accent text-accent' : 'border-border text-text-secondary hover:text-text-primary'"
        @click="active = ts"
      >
        {{ ts }}
      </button>
    </div>

    <ul class="mt-6 max-h-[420px] space-y-2 overflow-y-auto pr-2">
      <li
        v-for="tool in filtered"
        :key="tool.name"
        class="rounded-md border border-border bg-surface p-4"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <code class="font-mono text-sm text-text-primary">{{ tool.name }}</code>
          <div class="flex gap-1.5 font-mono text-[10px] uppercase tracking-wide text-text-secondary">
            <span v-if="tool.read_only" class="rounded border border-border px-1.5 py-0.5">read-only</span>
            <span v-if="tool.destructive" class="rounded border border-border px-1.5 py-0.5">destructive</span>
            <span v-if="tool.idempotent" class="rounded border border-border px-1.5 py-0.5">idempotent</span>
          </div>
        </div>
        <p class="mt-1.5 line-clamp-2 text-sm text-text-secondary">{{ firstParagraph(tool.description) }}</p>
      </li>
    </ul>
  </div>
</template>
