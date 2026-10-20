<script setup lang="ts">
import gsap from 'gsap'
import { Flip } from 'gsap/Flip'
import { computed, nextTick, ref } from 'vue'
import tools from '~/data/tools.generated.json'
import type { ToolsetId } from '~/content/copy'
import { useLanding } from '~/composables/useLanding'
import { TOOLSET_ORDER, TOOLSETS } from '~/composables/useToolsets'

const { copy, t, stats } = useLanding()

const query = ref('')
// Opens on `core`: the 13 tools a client gets by default. "All" is one click away.
const toolset = ref<ToolsetId | 'all'>('core')
const readOnlyOnly = ref(false)
const expanded = ref<string | null>(null)
const list = ref<HTMLElement | null>(null)

const firstSentence = (text: string) => text.split(/\n\n/)[0]!.replace(/\s+/g, ' ').trim()

const rows = tools.map((tool) => ({
  ...tool,
  summary: firstSentence(tool.description),
  details: tool.description.split(/\n\n/).slice(0, 2).join('\n\n').trim(),
}))

function matches(row: (typeof rows)[number]): boolean {
  if (toolset.value !== 'all' && row.toolset !== toolset.value) return false
  if (readOnlyOnly.value && !row.read_only) return false
  const q = query.value.trim().toLowerCase()
  return !q || row.name.toLowerCase().includes(q) || row.description.toLowerCase().includes(q)
}

const visible = computed(() => new Set(rows.filter(matches).map((r) => r.name)))

/** Capture positions, change the filter, then let Flip glide every card to where it lands.
 * Cards are hidden with `hidden` (display:none), not removed, because Flip needs them in
 * the DOM to animate their exit. */
async function refilter(change: () => void) {
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const items = list.value ? Array.from(list.value.children) : []
  const state = Flip.getState(items)
  change()
  await nextTick()
  if (calm || !items.length) return
  Flip.from(state, {
    duration: 0.55,
    ease: 'instrument',
    absolute: true,
    nested: true,
    onEnter: (els) => gsap.fromTo(els, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.45 }),
    onLeave: (els) => gsap.to(els, { opacity: 0, scale: 0.96, duration: 0.3 }),
  })
}

const setToolset = (id: ToolsetId | 'all') => refilter(() => (toolset.value = id))
const setQuery = (value: string) => refilter(() => (query.value = value))
const toggleReadOnly = () => refilter(() => (readOnlyOnly.value = !readOnlyOnly.value))
const toggle = (name: string) => (expanded.value = expanded.value === name ? null : name)
const count = computed(() => visible.value.size)
</script>

<template>
  <section id="tools" class="section border-t-2 border-ink" aria-labelledby="tools-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="tools"
        :ordinal="`04 · ${copy.tools.ordinal}`"
        :title="copy.tools.title"
        :lead="t(copy.tools.lead)"
      />

      <!-- Filters -->
      <div class="mt-10 grid grid-cols-[minmax(0,1fr)] gap-4 border-y border-ink py-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div class="flex flex-wrap items-center gap-2" role="group" :aria-label="copy.tools.searchLabel">
          <button
            type="button"
            class="min-h-10 border px-3 text-micro transition-colors duration-200"
            :class="toolset === 'all' ? 'border-ink bg-ink text-paper' : 'border-ink/40 hover:border-ink'"
            :aria-pressed="toolset === 'all'"
            @click="setToolset('all')"
          >
            {{ copy.tools.all }} <span class="measure ml-1 opacity-70">{{ stats.tools }}</span>
          </button>
          <button
            v-for="name in TOOLSET_ORDER"
            :key="name"
            type="button"
            class="min-h-10 border px-3 font-mono text-micro transition-colors duration-200"
            :class="toolset === name ? 'border-ink bg-ink text-paper' : 'border-ink/40 hover:border-ink'"
            :aria-pressed="toolset === name"
            @click="setToolset(name)"
          >
            {{ name }}
            <span class="measure ml-1 opacity-70">{{ TOOLSETS.find((s) => s.name === name)!.total }}</span>
            <span v-if="name === 'core'" class="ml-1 text-spot" :title="copy.tools.onByDefault" aria-hidden="true">●</span>
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-4">
          <label class="flex items-center gap-2 text-micro">
            <input
              type="checkbox"
              class="h-4 w-4 accent-ink"
              :checked="readOnlyOnly"
              @change="toggleReadOnly"
            />
            {{ copy.tools.readOnlyOnly }}
          </label>
          <label class="block">
            <span class="sr-only">{{ copy.tools.searchLabel }}</span>
            <input
              type="search"
              class="min-h-10 w-full min-w-[14rem] border border-ink bg-transparent px-3 font-mono text-micro placeholder:text-mist"
              :placeholder="copy.tools.searchPlaceholder"
              :value="query"
              @input="setQuery(($event.target as HTMLInputElement).value)"
            />
          </label>
        </div>
      </div>

      <p class="mt-3 font-mono text-micro text-graphite" role="status" aria-live="polite">
        {{ t(copy.tools.showing, { n: count, total: stats.tools }) }}
      </p>

      <ul ref="list" class="mt-4 grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-2">
        <li
          v-for="row in rows"
          :key="row.name"
          :data-flip-id="row.name"
          :class="{ hidden: !visible.has(row.name) }"
          class="border border-ink/40 bg-paper"
        >
          <button
            type="button"
            class="flex w-full flex-col gap-2 p-4 text-left transition-colors duration-200 hover:bg-tint"
            :aria-expanded="expanded === row.name"
            :aria-controls="`details-${row.name}`"
            @click="toggle(row.name)"
          >
            <span class="flex flex-wrap items-center gap-2">
              <span class="font-mono text-ui font-semibold [overflow-wrap:anywhere]">{{ row.name }}</span>
              <span class="border border-ink/30 px-1.5 py-0.5 font-mono text-ordinal text-graphite">{{ row.toolset }}</span>
              <span v-if="row.read_only" class="border border-ink/30 px-1.5 py-0.5 text-ordinal text-graphite">{{ copy.tools.badges.readOnly }}</span>
              <span v-if="row.destructive" class="border border-spot px-1.5 py-0.5 text-ordinal text-spot">{{ copy.tools.badges.destructive }}</span>
              <span v-if="row.idempotent" class="border border-ink/30 px-1.5 py-0.5 text-ordinal text-graphite">{{ copy.tools.badges.idempotent }}</span>
            </span>
            <span class="line-clamp-2 text-micro text-graphite">{{ row.summary }}</span>
          </button>
          <div
            :id="`details-${row.name}`"
            class="border-t border-ink/20 bg-tint px-4 py-3"
            :hidden="expanded !== row.name"
          >
            <p class="whitespace-pre-line text-micro leading-relaxed">{{ row.details }}</p>
          </div>
        </li>
      </ul>
      <p v-if="count === 0" class="mt-6 text-body text-graphite">{{ copy.tools.noResults }}</p>

      <!-- What each toolset is for. -->
      <dl class="mt-12 grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-5 border-t border-ink pt-6 md:grid-cols-2 lg:grid-cols-3">
        <div v-for="name in TOOLSET_ORDER" :key="name">
          <dt class="font-mono text-ui font-semibold">
            {{ name }}
            <span v-if="name === 'core'" class="ml-1 font-sans text-micro font-normal text-spot">● {{ copy.tools.onByDefault }}</span>
          </dt>
          <dd class="mt-1 text-micro text-graphite">{{ copy.tools.toolsets[name] }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>
