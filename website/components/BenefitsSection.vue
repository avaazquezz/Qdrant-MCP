<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

const benefits = [
  {
    tag: 'control',
    title: 'Full control, not a shim',
    body: 'Complete collection & point lifecycle plus every Qdrant search mode — hybrid, grouped, recommend, discover, distance matrices.',
  },
  {
    tag: 'safety',
    title: 'Production-grade safety',
    body: 'A read-only guard removes every mutating tool from the registry, Pydantic validates every input, and BYO mode re-resolves DNS on each request to defeat SSRF.',
  },
  {
    tag: 'deploy',
    title: 'Runs how you need it',
    body: 'PyPI, Docker, or the Claude Desktop .mcpb bundle. Toolsets are opt-in, and bring-your-own-Qdrant mode needs no database of its own.',
  },
  {
    tag: 'observability',
    title: 'Observable',
    body: 'Telemetry, Prometheus metrics, resource quotas, and self-diagnosed issues — know what your Qdrant deployment is doing, not flying blind.',
  },
]

useReveal(root, () => {
  gsap.from('.benefit-row', {
    y: 16,
    opacity: 0,
    duration: 0.5,
    ease: 'power2.out',
    stagger: 0.08,
    scrollTrigger: { trigger: root.value, start: 'top 80%', once: true },
  })
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-4xl px-6 py-24">
    <p class="font-mono text-xs uppercase tracking-[0.25em] text-dust/70">why this one</p>
    <div class="mt-6 divide-y divide-hairline border-y border-hairline">
      <div
        v-for="b in benefits"
        :key="b.title"
        class="benefit-row grid gap-2 py-6 sm:grid-cols-[120px_1fr] sm:gap-8"
      >
        <span class="font-mono text-xs uppercase tracking-[0.15em] text-pulse">[{{ b.tag }}]</span>
        <div>
          <h3 class="font-display text-xl italic text-paper">{{ b.title }}</h3>
          <p class="mt-1.5 max-w-2xl text-sm leading-relaxed text-dust">{{ b.body }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
