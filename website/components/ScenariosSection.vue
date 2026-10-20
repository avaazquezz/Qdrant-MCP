<script setup lang="ts">
import { computed, ref } from 'vue'
import scenarioData from '~/data/scenarios.generated.json'
import type { ScenarioId } from '~/content/copy'
import type { Step } from '~/content/types'
import { useLanding } from '~/composables/useLanding'

const { copy, t } = useLanding()

const scenarios = scenarioData.scenarios as unknown as { id: ScenarioId; steps: Step[] }[]
const selected = ref<ScenarioId>(scenarios[0]!.id)
const tabs = ref<HTMLButtonElement[]>([])

const current = computed(() => scenarios.find((s) => s.id === selected.value)!)
const text = computed(() => copy.scenarios.tabs[selected.value])

// Keyboard: arrows move between tabs, Home/End jump (the WAI-ARIA tabs pattern).
function onKey(event: KeyboardEvent, index: number) {
  const last = scenarios.length - 1
  const target =
    event.key === 'ArrowRight' ? (index + 1) % scenarios.length
    : event.key === 'ArrowLeft' ? (index - 1 + scenarios.length) % scenarios.length
    : event.key === 'Home' ? 0
    : event.key === 'End' ? last
    : -1
  if (target < 0) return
  event.preventDefault()
  selected.value = scenarios[target]!.id
  tabs.value[target]?.focus()
}
</script>

<template>
  <section id="scenarios" class="section border-t-2 border-ink" aria-labelledby="scenarios-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="scenarios"
        :ordinal="`03 · ${copy.scenarios.ordinal}`"
        :title="copy.scenarios.title"
        :lead="copy.scenarios.lead"
      />

      <div class="mt-10" role="tablist" :aria-label="copy.scenarios.title">
        <div class="flex gap-1 overflow-x-auto border-b border-ink">
          <button
            v-for="(scenario, i) in scenarios"
            :id="`tab-${scenario.id}`"
            :key="scenario.id"
            :ref="(el) => { if (el) tabs[i] = el as HTMLButtonElement }"
            type="button"
            role="tab"
            :aria-selected="selected === scenario.id"
            :aria-controls="`panel-${scenario.id}`"
            :tabindex="selected === scenario.id ? 0 : -1"
            class="shrink-0 border border-b-0 px-4 py-3 text-ui transition-colors duration-200"
            :class="selected === scenario.id ? 'border-ink bg-ink text-paper' : 'border-transparent text-graphite hover:text-ink'"
            @click="selected = scenario.id"
            @keydown="onKey($event, i)"
          >
            {{ copy.scenarios.tabs[scenario.id].tab }}
          </button>
        </div>
      </div>

      <div
        :id="`panel-${selected}`"
        role="tabpanel"
        :aria-labelledby="`tab-${selected}`"
        tabindex="0"
        class="pt-8"
      >
        <h3 class="text-h2 font-bold">{{ text.title }}</h3>
        <p class="mt-3 max-w-prose text-body text-graphite">{{ text.intro }}</p>
        <div class="mt-8">
          <ScenarioPlayer :steps="current.steps" :captions="text.steps" />
        </div>
        <p class="mt-4 font-mono text-micro text-graphite" data-verified="scripts/record_scenarios.py">
          {{ t(copy.scenarios.recorded) }}
        </p>
      </div>
    </div>
  </section>
</template>
