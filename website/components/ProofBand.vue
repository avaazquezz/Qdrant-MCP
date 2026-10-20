<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import { useGsap } from '~/composables/useGsap'
import { useLanding } from '~/composables/useLanding'

const { copy, t, stats, lang } = useLanding()
const numbers = new Intl.NumberFormat(lang)

// Every figure comes from website/data/stats.generated.json: nothing here is typed in.
const items = [
  { key: 'tools', value: stats.tools, label: copy.proof.tools, sub: t(copy.proof.toolsSub) },
  { key: 'tests', value: stats.tests, label: copy.proof.tests, sub: copy.proof.testsSub },
  {
    key: 'changelog',
    value: stats.releases.length,
    label: copy.proof.changelog,
    sub: t(copy.proof.changelogSub),
  },
  { key: 'code', value: stats.source_lines, label: copy.proof.code, sub: t(copy.proof.codeSub) },
  { key: 'schema', value: stats.core_schema_kb, label: copy.proof.schema, sub: copy.proof.schemaSub },
]

const root = ref<HTMLElement | null>(null)

// A reading that settles: each number wobbles around its value with a shrinking error and
// then locks onto it, the way an instrument's display stabilizes. Only the first time the
// band scrolls into view; under reduced motion the final values are simply there.
useGsap(root, ({ motion }) => {
  if (!motion || !root.value) return
  root.value.querySelectorAll<HTMLElement>('[data-count]').forEach((el) => {
    const target = Number(el.dataset.count)
    const state = { progress: 0 }
    gsap.to(state, {
      progress: 1,
      duration: 1.3,
      ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 92%', once: true },
      onUpdate: () => {
        const error = (1 - state.progress) * (Math.random() - 0.5) * target * 0.22
        el.textContent = numbers.format(Math.max(0, Math.round(target * state.progress + error)))
      },
      onComplete: () => {
        el.textContent = numbers.format(target)
      },
    })
  })
})
</script>

<template>
  <section ref="root" class="border-y-2 border-ink" :aria-label="copy.proof.note">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <ul class="grid grid-cols-2 divide-ink/25 md:grid-cols-5 md:divide-x">
        <li
          v-for="item in items"
          :key="item.key"
          class="px-1 py-6 md:px-5 md:first:pl-0"
          data-verified="scripts/gen_site_stats.py"
        >
          <p class="measure text-[clamp(2rem,4vw,3rem)] font-bold leading-none tracking-[-0.02em]">
            <span :data-count="item.value">{{ numbers.format(item.value) }}</span>
          </p>
          <p class="mt-2 text-micro font-semibold">{{ item.label }}</p>
          <p class="mt-1 text-micro text-graphite">{{ item.sub }}</p>
        </li>
      </ul>
      <p class="border-t border-ink/25 py-3 font-mono text-ordinal text-graphite">
        {{ copy.proof.note }}
      </p>
    </div>
  </section>
</template>
