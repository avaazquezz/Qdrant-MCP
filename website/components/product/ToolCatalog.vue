<script setup lang="ts">
import gsap from 'gsap'
import tools from '~/data/tools.generated.json'

type Toolset = (typeof tools)[number]['toolset']

const toolsets = [...new Set(tools.map((t) => t.toolset))].sort() as Toolset[]
const active = ref<Toolset | 'all'>('all')
const listEl = ref<HTMLElement | null>(null)

const filtered = computed(() =>
  active.value === 'all' ? tools : tools.filter((t) => t.toolset === active.value)
)

function firstParagraph(description: string) {
  return description.split('\n\n')[0]
}

function select(value: Toolset | 'all') {
  if (value === active.value || !listEl.value) {
    active.value = value
    return
  }
  gsap.to(listEl.value, {
    opacity: 0,
    y: 6,
    duration: 0.12,
    ease: 'power1.in',
    onComplete: () => {
      active.value = value
      requestAnimationFrame(() => {
        gsap.fromTo(listEl.value, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.25, ease: 'power2.out' })
      })
    },
  })
}
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="border px-3 py-1 font-mono text-xs transition-colors"
        :class="active === 'all' ? 'border-signal text-signal' : 'border-hairline text-dust hover:text-paper'"
        @click="select('all')"
      >
        all ({{ tools.length }})
      </button>
      <button
        v-for="ts in toolsets"
        :key="ts"
        type="button"
        class="border px-3 py-1 font-mono text-xs transition-colors"
        :class="active === ts ? 'border-signal text-signal' : 'border-hairline text-dust hover:text-paper'"
        @click="select(ts)"
      >
        {{ ts }}
      </button>
    </div>

    <ul
      ref="listEl"
      class="mt-6 max-h-[420px] divide-y divide-hairline overflow-y-auto border-t border-hairline pr-2"
    >
      <li
        v-for="tool in filtered"
        :key="tool.name"
        class="group py-3 transition-colors hover:bg-graphite"
      >
        <div class="flex flex-wrap items-center justify-between gap-2 px-1">
          <code class="font-mono text-sm text-paper transition-colors group-hover:text-pulse">{{ tool.name }}</code>
          <div class="flex gap-1.5 font-mono text-[10px] uppercase tracking-wide text-dust">
            <span v-if="tool.read_only" class="border border-hairline px-1.5 py-0.5">read-only</span>
            <span v-if="tool.destructive" class="border border-hairline px-1.5 py-0.5">destructive</span>
            <span v-if="tool.idempotent" class="border border-hairline px-1.5 py-0.5">idempotent</span>
          </div>
        </div>
        <p class="mt-1.5 line-clamp-2 px-1 text-sm text-dust">{{ firstParagraph(tool.description) }}</p>
      </li>
    </ul>
  </div>
</template>
