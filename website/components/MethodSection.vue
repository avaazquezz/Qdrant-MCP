<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import { useGsap } from '~/composables/useGsap'
import { useLanding } from '~/composables/useLanding'

const { copy } = useLanding()
const root = ref<HTMLElement | null>(null)

// Each step is "logged" with a wipe from the left, in reading order, as the row enters.
// A clip-path wipe, not a fade: the card is measured onto the page like a reading.
useGsap(root, ({ motion }) => {
  if (!motion || !root.value) return
  const steps = root.value.querySelectorAll<HTMLElement>('[data-step]')
  gsap.set(steps, { clipPath: 'inset(0 100% 0 0)' })
  gsap.to(steps, {
    clipPath: 'inset(0 0% 0 0)',
    duration: 0.9,
    stagger: 0.14,
    scrollTrigger: { trigger: root.value.querySelector('[data-steps]'), start: 'top 82%', once: true },
  })
})
</script>

<template>
  <section id="method" ref="root" class="section" aria-labelledby="method-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="method"
        :ordinal="`01 · ${copy.method.ordinal}`"
        :title="copy.method.title"
        :lead="copy.method.lead"
      />

      <ol data-steps class="mt-12 grid grid-cols-[minmax(0,1fr)] gap-px border border-ink bg-ink md:grid-cols-3">
        <li v-for="(step, i) in copy.method.steps" :key="step.name" data-step class="bg-paper p-6 sm:p-8">
          <p class="flex items-baseline justify-between font-mono text-ordinal uppercase text-graphite">
            <span class="measure">{{ String(i + 1).padStart(2, '0') }} / {{ String(copy.method.steps.length).padStart(2, '0') }}</span>
          </p>
          <h3 class="mt-6 text-h2 font-bold">{{ step.name }}</h3>
          <p class="mt-4 text-body text-graphite">{{ step.body }}</p>
          <p
            class="mt-6 border-l-2 border-spot pl-4 font-mono text-micro leading-relaxed text-ink [overflow-wrap:anywhere]"
            data-verified="the real example, in the log"
          >
            {{ step.example }}
          </p>
        </li>
      </ol>

      <p class="mt-8">
        <a href="#log" class="text-ui underline decoration-1 underline-offset-4 transition-colors duration-200 hover:text-spot">
          {{ copy.method.cta }} <span aria-hidden="true">↓</span>
        </a>
      </p>
    </div>
  </section>
</template>
