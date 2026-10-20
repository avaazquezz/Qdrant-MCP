<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import scenarioData from '~/data/scenarios.generated.json'
import type { Step } from '~/content/types'
import { pretty } from '~/composables/usePretty'
import { useGsap } from '~/composables/useGsap'
import { REPO_URL, useLanding } from '~/composables/useLanding'

const { copy, t } = useLanding()
const nodes = copy.architecture.nodes

// What travels along the wire is the REAL fused hybrid-search call from the recorded
// scenarios, so the page follows one actual request from the client to Qdrant and back.
const fusedQuery = scenarioData.scenarios
  .find((s) => s.id === 'hybrid-search')!
  .steps.at(-1) as unknown as Step
const queryArgs = fusedQuery.arguments as { collection_name: string; limit: number }
const vars = { limit: queryArgs.limit, cap: 1000, collection: queryArgs.collection_name }

const payloads = nodes.map((node, i) => {
  if (i === 0) {
    return pretty(
      { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: fusedQuery.tool, arguments: fusedQuery.arguments } },
      2
    )
  }
  if (i === nodes.length - 1) return pretty(fusedQuery.result, 4)
  return node.payloadLines.map((line) => t(line, vars)).join('\n')
})

const root = ref<HTMLElement | null>(null)
const stage = ref<HTMLElement | null>(null)
const track = ref<HTMLElement | null>(null)
const line = ref<HTMLElement | null>(null)
const packet = ref<HTMLElement | null>(null)
const active = ref(0)

const sourceUrl = (source: string) => `${REPO_URL}/blob/main/${source.split(' ')[0]}`

// On wide screens the section pins for about two screens of scroll, and a packet travels
// the five hops as you scroll: each node lights as the call reaches it. That is the one
// scrubbed sequence on the page. Below the desktop breakpoint, and under reduced motion,
// nothing is pinned: every hop is a card with its explanation already visible, and on
// desktop the nodes are buttons, so the sequence works without scrolling.
useGsap(root, ({ motion, desktop }) => {
  if (!motion || !desktop || !stage.value || !track.value || !line.value || !packet.value) return

  const travel = () => track.value!.offsetWidth
  const timeline = gsap.timeline({
    defaults: { ease: 'none' },
    scrollTrigger: {
      trigger: stage.value,
      start: 'center center+=40',
      end: '+=230%',
      pin: true,
      scrub: 0.6,
      anticipatePin: 1,
      invalidateOnRefresh: true,
      onUpdate: (self) => {
        active.value = Math.min(nodes.length - 1, Math.floor(self.progress * nodes.length))
      },
    },
  })
  timeline
    .fromTo(line.value, { scaleX: 0 }, { scaleX: 1, transformOrigin: 'left center' }, 0)
    .fromTo(packet.value, { x: 0 }, { x: travel }, 0)
})
</script>

<template>
  <section id="architecture" ref="root" class="section border-t-2 border-ink" aria-labelledby="architecture-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="architecture"
        :ordinal="`02 · ${copy.architecture.ordinal}`"
        :title="copy.architecture.title"
        :lead="copy.architecture.lead"
      />
    </div>

    <div ref="stage" class="mx-auto mt-12 max-w-sheet px-4 sm:px-6">
      <p class="mb-4 hidden font-mono text-ordinal uppercase tracking-[0.14em] text-graphite lg:block">
        {{ copy.architecture.caption }} <span aria-hidden="true">↓</span>
      </p>

      <ol class="grid grid-cols-[minmax(0,1fr)] gap-3 lg:grid-cols-5 lg:gap-4">
        <li v-for="(node, i) in nodes" :key="node.name">
          <button
            type="button"
            class="block w-full border p-4 text-left transition-colors duration-300 lg:h-full lg:min-h-[7.5rem]"
            :class="
              i === active
                ? 'border-ink bg-ink text-paper'
                : i < active
                  ? 'border-ink/50 bg-tint text-ink'
                  : 'border-ink/30 text-ink'
            "
            :aria-current="i === active ? 'step' : undefined"
            @click="active = i"
            @focus="active = i"
          >
            <span class="flex items-center justify-between font-mono text-ordinal uppercase tracking-[0.12em]">
              <span class="measure">{{ String(i + 1).padStart(2, '0') }}</span>
              <span
                class="h-1.5 w-1.5 rounded-full transition-colors duration-300"
                :class="i <= active ? 'bg-spot' : 'bg-ink/20'"
                aria-hidden="true"
              />
            </span>
            <span class="mt-3 block font-mono text-ui font-semibold">{{ node.name }}</span>
            <span class="mt-1 block text-micro" :class="i === active ? 'text-paper/75' : 'text-graphite'">
              {{ node.tag }}
            </span>
          </button>

          <!-- Below the desktop breakpoint every hop explains itself in place. -->
          <div class="mt-3 border-l-2 border-ink/30 pl-4 lg:hidden">
            <p class="text-body text-graphite">{{ t(node.why) }}</p>
            <a
              :href="sourceUrl(node.source)"
              target="_blank"
              rel="noopener"
              class="mt-2 inline-block font-mono text-micro underline decoration-1 underline-offset-4"
              :data-verified="node.source"
            >
              {{ node.source }}
            </a>
          </div>
        </li>
      </ol>

      <!-- The wire between the hops, with the packet that travels it. -->
      <div ref="track" class="relative mt-6 hidden h-px bg-ink/25 lg:block" aria-hidden="true">
        <span ref="line" class="absolute inset-y-0 left-0 block h-[2px] w-full -translate-y-px bg-spot" style="transform: scaleX(0); transform-origin: left center" />
        <span ref="packet" class="absolute -top-[5px] left-0 block h-[11px] w-[11px] -translate-x-1/2 rounded-full border-2 border-spot bg-paper" />
      </div>

      <!-- Desktop: the explanation of the hop the call has reached, and what travels there. -->
      <div class="mt-8 hidden gap-10 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]" aria-live="polite">
        <div class="min-h-[18rem]">
          <div v-for="(node, i) in nodes" v-show="i === active" :key="node.name" class="max-w-xl">
            <p class="text-deck">{{ t(node.why) }}</p>
            <a
              :href="sourceUrl(node.source)"
              target="_blank"
              rel="noopener"
              class="mt-4 inline-block font-mono text-micro underline decoration-1 underline-offset-4 transition-colors duration-200 hover:text-spot"
              :data-verified="node.source"
            >
              {{ node.source }}
            </a>
          </div>
        </div>
        <div class="on-panel bg-panel text-panel-ink">
          <div v-for="(node, i) in nodes" v-show="i === active" :key="node.name">
            <p class="border-b border-panel-line px-4 py-3 font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">
              {{ node.payloadTitle }}
            </p>
            <pre class="max-h-[19rem] overflow-auto px-4 py-4 font-mono text-micro leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]" data-lenis-prevent>{{ payloads[i] }}</pre>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
