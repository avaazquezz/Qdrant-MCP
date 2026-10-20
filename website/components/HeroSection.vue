<script setup lang="ts">
import { REPO_URL, useLanding } from '~/composables/useLanding'

const { copy, t } = useLanding()
</script>

<template>
  <section class="pb-10 pt-8 sm:pt-12 lg:pt-14" aria-labelledby="hero-title">
    <div class="mx-auto grid max-w-sheet grid-cols-[minmax(0,1fr)] gap-10 px-4 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-center lg:gap-14">
      <div>
        <p class="anim-settle font-mono text-micro uppercase tracking-[0.14em] text-graphite">
          {{ copy.hero.kicker }}
        </p>
        <!-- The LCP element. Revealed by CSS only (`anim-rise`), so it never waits for JavaScript. -->
        <h1
          id="hero-title"
          class="anim-rise mt-5 text-[clamp(2.2rem,5vw,4.5rem)] font-bold leading-[0.97] tracking-[-0.03em]"
        >
          {{ t(copy.hero.title) }}
        </h1>
        <p class="anim-settle mt-6 max-w-prose text-deck text-graphite" style="animation-delay: 200ms">
          {{ copy.hero.deck }}
        </p>
        <div class="anim-settle mt-8 flex flex-wrap items-center gap-x-6 gap-y-4" style="animation-delay: 320ms">
          <a
            :href="REPO_URL"
            target="_blank"
            rel="noopener"
            data-magnetic
            class="inline-flex min-h-12 items-center gap-2 rounded-sm border border-ink bg-ink px-6 text-ui font-semibold text-paper transition-colors duration-200 hover:bg-transparent hover:text-ink"
          >
            {{ copy.hero.ctaPrimary }}
            <span aria-hidden="true">↗</span>
            <span class="sr-only">{{ copy.a11y.opensNewTab }}</span>
          </a>
          <a
            href="#log"
            class="text-ui text-graphite underline decoration-1 underline-offset-4 transition-colors duration-200 hover:text-ink"
          >
            {{ copy.hero.ctaSecondary }}
          </a>
        </div>
      </div>

      <div class="anim-settle" style="animation-delay: 420ms">
        <ClientOnly>
          <VectorField
            :label="copy.hero.canvasLabel"
            :caption="copy.hero.canvasCaption"
            :nearest="copy.hero.nearest"
            :pause="copy.a11y.pauseAnimation"
            :play="copy.a11y.playAnimation"
          />
          <!-- Same box before hydration, so the page does not jump when the canvas arrives. -->
          <template #fallback>
            <div class="aspect-[5/4] w-full bg-panel sm:aspect-[4/3] lg:aspect-[1/1]" aria-hidden="true" />
          </template>
        </ClientOnly>
      </div>
    </div>
  </section>
</template>
