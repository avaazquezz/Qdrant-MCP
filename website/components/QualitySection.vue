<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import { useGsap } from '~/composables/useGsap'
import { useLanding } from '~/composables/useLanding'

const { copy, t } = useLanding()
const root = ref<HTMLElement | null>(null)

// The pipeline's wire draws itself once, left to right, as the section arrives: a push
// travelling to a published release. A transform on a full-width bar, no layout work.
useGsap(root, ({ motion }) => {
  if (!motion || !root.value) return
  const wire = root.value.querySelector<HTMLElement>('[data-wire]')
  const stops = root.value.querySelectorAll<HTMLElement>('[data-stop]')
  if (!wire) return
  gsap.set(wire, { scaleX: 0, transformOrigin: 'left center' })
  gsap.set(stops, { opacity: 0.25 })
  const timeline = gsap.timeline({
    scrollTrigger: { trigger: wire, start: 'top 85%', once: true },
  })
  timeline.to(wire, { scaleX: 1, duration: 1.4, ease: 'power2.inOut' })
  timeline.to(stops, { opacity: 1, stagger: 0.2, duration: 0.4 }, 0.1)
})
</script>

<template>
  <section id="quality" ref="root" class="section border-t-2 border-ink" aria-labelledby="quality-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="quality"
        :ordinal="`06 · ${copy.quality.ordinal}`"
        :title="copy.quality.title"
        :lead="copy.quality.lead"
      />

      <div class="mt-12">
        <ol class="relative grid grid-cols-2 gap-y-6 md:grid-cols-6">
          <span class="absolute left-0 right-0 top-[0.6rem] hidden h-px bg-ink/20 md:block" aria-hidden="true" />
          <span data-wire class="absolute left-0 right-0 top-[0.6rem] hidden h-[2px] -translate-y-px bg-spot md:block" aria-hidden="true" />
          <li v-for="(stop, i) in copy.quality.pipeline" :key="stop" data-stop class="relative">
            <span class="relative z-10 block h-[1.2rem] w-[1.2rem] rounded-full border-2 border-spot bg-paper" aria-hidden="true" />
            <p class="measure mt-3 font-mono text-ordinal text-graphite">{{ String(i + 1).padStart(2, '0') }}</p>
            <p class="mt-1 pr-3 font-mono text-micro">{{ stop }}</p>
          </li>
        </ol>
      </div>

      <div class="mt-14 grid grid-cols-[minmax(0,1fr)] gap-px border border-ink bg-ink md:grid-cols-3">
        <article v-for="card in copy.quality.cards" :key="card.title" class="bg-paper p-6 sm:p-8">
          <h3 class="text-h3 font-bold">{{ card.title }}</h3>
          <p class="mt-3 text-body text-graphite">{{ t(card.body) }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
