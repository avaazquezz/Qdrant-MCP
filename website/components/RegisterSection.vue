<script setup lang="ts">
import { computed, ref } from 'vue'
import tools from '~/data/tools.generated.json'

const TOOLSET_ORDER = ['core', 'search', 'payload', 'snapshots', 'observability'] as const
type Filter = 'all' | (typeof TOOLSET_ORDER)[number]

const query = ref('')
const filter = ref<Filter>('all')

function firstSentence(description: string) {
  return description.split('\n\n')[0]
}

const matches = computed(() => {
  const q = query.value.trim().toLowerCase()
  return tools.filter((t) => {
    if (filter.value !== 'all' && t.toolset !== filter.value) return false
    if (!q) return true
    return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
  })
})

const bands = computed(() =>
  TOOLSET_ORDER.map((name) => ({ name, tools: matches.value.filter((t) => t.toolset === name) })).filter(
    (b) => b.tools.length > 0
  )
)

function markerClass(t: (typeof tools)[number]) {
  if (t.read_only) return 'border border-ink bg-transparent'
  if (t.destructive) return 'border border-spot bg-spot'
  return 'border border-ink bg-ink'
}
</script>

<template>
  <section id="s-05" data-section="05" class="border-t-2 border-ink py-14 lg:py-24">
    <div class="section-rule border-t-2 border-ink" />
    <h2 class="mt-8 max-w-prose text-h2 text-ink">All 49, printed.</h2>

    <div class="mt-8 flex flex-col gap-4">
      <div>
        <label for="tool-filter" class="mb-2 block text-ui text-graphite">Filter 49 tools</label>
        <input
          id="tool-filter"
          v-model="query"
          type="search"
          placeholder="Filter by name or description…"
          class="h-10 w-full max-w-sm rounded-sm border border-ink bg-paper px-3 text-ui text-ink placeholder:text-graphite"
        />
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="f in (['all', ...TOOLSET_ORDER] as Filter[])"
          :key="f"
          type="button"
          :aria-pressed="filter === f"
          class="flex h-10 items-center rounded-sm border border-ink px-3 font-mono text-ui transition-colors"
          :class="filter === f ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-tint'"
          @click="filter = f"
        >{{ f }}</button>
      </div>
      <p class="sr-only" role="status" aria-live="polite">{{ matches.length }} of 49 shown</p>
      <p class="text-micro text-graphite">{{ matches.length }} of 49 shown</p>
    </div>

    <div class="mt-8">
      <div v-for="band in bands" :key="band.name" class="mb-8 last:mb-0">
        <div class="flex items-baseline justify-between border-t border-ink pt-1.5">
          <span class="font-mono text-ordinal text-ink">{{ band.name }}</span>
          <span class="font-mono text-ordinal text-ink">{{ band.tools.length }}</span>
        </div>
        <ul class="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <li v-for="t in band.tools" :key="t.name" :id="`tool-${t.name}`" class="min-w-0 scroll-mt-20">
            <div class="flex items-start gap-2">
              <span class="mt-[5px] h-2 w-2 shrink-0 rounded-full" :class="markerClass(t)" aria-hidden="true" />
              <div class="min-w-0">
                <p class="font-mono text-micro text-ink [overflow-wrap:anywhere]">
                  {{ t.name }}
                  <span v-if="t.destructive" class="ml-1 font-mono text-ordinal text-spot">destructive</span>
                </p>
                <p class="mt-1 text-micro text-graphite">{{ firstSentence(t.description) }}</p>
              </div>
            </div>
          </li>
        </ul>
      </div>
      <p v-if="matches.length === 0" class="border-t border-ink py-8 text-body text-graphite">
        No tool matches “{{ query }}”.
      </p>
    </div>

    <p class="mt-8 text-micro text-graphite">
      Generated from the running tool registry by
      <a
        href="https://github.com/avaazquezz/Qdrant-MCP/blob/main/scripts/gen_tools_json.py"
        target="_blank"
        rel="noopener"
        class="font-mono underline decoration-1 underline-offset-4"
      >scripts/gen_tools_json.py<span class="sr-only"> (opens in a new tab)</span></a>. CI fails if
      this page and the server disagree.
    </p>
  </section>
</template>
