<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import { LOG, REPO } from '~/content/log'
import { useGsap } from '~/composables/useGsap'
import { REPO_URL, useLanding } from '~/composables/useLanding'

const { copy, lang } = useLanding()
const labels = copy.log.labels
const root = ref<HTMLElement | null>(null)

const rows = ['claim', 'probe', 'result', 'fix'] as const
const rowLabel = { claim: labels.claim, probe: labels.probe, result: labels.result, fix: labels.fix }

// Each entry has a rail with four stations (claim → probe → result → fix). As the entry
// crosses the viewport the rail fills and the stations light in order: the sequence a finding
// goes through, drawn as the thing you scroll along. Lightweight transforms only; under
// reduced motion the rail simply renders full.
useGsap(root, ({ motion, desktop }) => {
  if (!motion || !desktop || !root.value) return
  root.value.querySelectorAll<HTMLElement>('[data-entry]').forEach((entry) => {
    const fill = entry.querySelector<HTMLElement>('[data-fill]')
    const stations = entry.querySelectorAll<HTMLElement>('[data-station]')
    if (!fill) return
    gsap.set(fill, { scaleY: 0, transformOrigin: 'top center' })
    gsap.set(stations, { backgroundColor: 'transparent' })
    gsap.to(fill, {
      scaleY: 1,
      ease: 'none',
      scrollTrigger: {
        trigger: entry,
        start: 'top 62%',
        end: 'bottom 58%',
        scrub: 0.5,
        onUpdate: (self) => {
          stations.forEach((station, i) => {
            const lit = self.progress >= (i + 0.35) / stations.length
            gsap.to(station, { backgroundColor: lit ? '#C2172F' : 'transparent', duration: 0.3, overwrite: true })
          })
        },
      },
    })
  })
})
</script>

<template>
  <section id="log" ref="root" class="section border-t-2 border-ink" aria-labelledby="log-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <SectionHeading
        id="log"
        :ordinal="`05 · ${copy.log.ordinal}`"
        :title="copy.log.title"
        :lead="copy.log.lead"
      />

      <ol class="mt-12">
        <li v-for="(entry, index) in LOG" :key="entry.id">
          <article
            :id="`log-${entry.id}`"
            data-entry
            class="grid grid-cols-[minmax(0,1fr)] gap-6 border-t border-ink py-10 lg:grid-cols-[2.5rem_minmax(0,1fr)] lg:gap-8"
            :aria-labelledby="`log-${entry.id}-title`"
          >
            <!-- The rail: claim, probe, result, fix. -->
            <div class="relative hidden lg:block" aria-hidden="true">
              <span class="absolute bottom-2 left-[0.6875rem] top-2 w-px bg-ink/20" />
              <span data-fill class="absolute bottom-2 left-[0.6875rem] top-2 w-px bg-spot" />
              <span
                v-for="n in 4"
                :key="n"
                data-station
                class="absolute left-[0.1875rem] block h-3 w-3 rounded-full border-[1.5px] border-spot"
                :style="{ top: `${(n - 1) * 31 + 1}%` }"
              />
            </div>

            <div class="max-w-4xl">
              <p class="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-ordinal uppercase tracking-[0.12em] text-graphite">
                <span class="measure">{{ String(index + 1).padStart(2, '0') }} / {{ String(LOG.length).padStart(2, '0') }}</span>
                <span
                  v-if="entry.review"
                  class="border border-spot px-1.5 py-0.5 normal-case tracking-normal text-spot"
                >
                  {{ labels.review }}
                </span>
              </p>
              <h3 :id="`log-${entry.id}-title`" class="mt-3 text-h2 font-bold">{{ entry.text[lang].title }}</h3>

              <dl class="mt-8 grid grid-cols-[minmax(0,1fr)] gap-6">
                <div v-for="row in rows" :key="row" class="grid grid-cols-[minmax(0,1fr)] gap-1 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-6">
                  <dt class="font-mono text-ordinal uppercase tracking-[0.12em]" :class="row === 'result' ? 'text-spot' : 'text-graphite'">
                    {{ rowLabel[row] }}
                  </dt>
                  <dd class="text-body" :class="row === 'result' ? 'font-medium' : 'text-graphite'">
                    {{ entry.text[lang][row] }}
                  </dd>
                </div>
              </dl>

              <div class="mt-8 flex flex-wrap items-start gap-x-10 gap-y-4 border-t border-ink/25 pt-4 font-mono text-micro">
                <p>
                  <span class="mr-2 text-graphite">{{ labels.fixedIn }}</span>
                  <a
                    v-for="v in entry.versions"
                    :key="v"
                    :href="`${REPO}/releases/tag/v${v}`"
                    target="_blank"
                    rel="noopener"
                    class="mr-2 underline decoration-1 underline-offset-4 hover:text-spot"
                    data-verified="a published release"
                  >v{{ v }}</a>
                  <a
                    v-for="pr in entry.prs"
                    :key="pr"
                    :href="`${REPO}/pull/${pr}`"
                    target="_blank"
                    rel="noopener"
                    class="mr-2 underline decoration-1 underline-offset-4 hover:text-spot"
                    data-verified="a merged pull request"
                  >#{{ pr }}</a>
                </p>
                <p v-for="test in entry.tests" :key="test.name" class="min-w-0">
                  <span class="mr-2 text-graphite">{{ labels.pinnedBy }}</span>
                  <a
                    :href="`${REPO}/blob/main/${test.file}`"
                    target="_blank"
                    rel="noopener"
                    class="underline decoration-1 underline-offset-4 [overflow-wrap:anywhere] hover:text-spot"
                    :data-verified="`this test exists — ${test.file}`"
                  >{{ test.name }}</a>
                </p>
              </div>
            </div>
          </article>
        </li>
      </ol>

      <div class="border-t-2 border-ink pt-8">
        <a
          :href="REPO_URL"
          target="_blank"
          rel="noopener"
          data-magnetic
          class="inline-flex min-h-12 items-center gap-2 rounded-sm border border-ink bg-ink px-6 text-ui font-semibold text-paper transition-colors duration-200 hover:bg-transparent hover:text-ink"
        >
          {{ copy.log.cta }} <span aria-hidden="true">↗</span>
          <span class="sr-only">{{ copy.a11y.opensNewTab }}</span>
        </a>
      </div>
    </div>
  </section>
</template>
