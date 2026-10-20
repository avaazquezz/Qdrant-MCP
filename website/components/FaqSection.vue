<script setup lang="ts">
import { useLanding } from '~/composables/useLanding'

const { copy } = useLanding()
</script>

<template>
  <section id="questions" class="section border-t-2 border-ink" aria-labelledby="questions-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading id="questions" :ordinal="`07 · ${copy.faq.ordinal}`" :title="copy.faq.title" />

      <div class="mt-10 max-w-4xl divide-y divide-ink/25 border-y border-ink">
        <details v-for="item in copy.faq.items" :key="item.q" class="group py-5">
          <summary class="flex cursor-pointer list-none items-baseline justify-between gap-6 text-h3 font-bold marker:hidden [&::-webkit-details-marker]:hidden">
            {{ item.q }}
            <span class="shrink-0 font-mono text-ui font-normal transition-transform duration-300 group-open:rotate-45" aria-hidden="true">+</span>
          </summary>
          <p class="mt-4 max-w-prose text-body text-graphite">{{ item.a }}</p>
        </details>
      </div>
    </div>
  </section>
</template>
