<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

const benefits = [
  {
    title: 'Full control, not a shim',
    body: 'Complete collection & point lifecycle plus every Qdrant search mode — hybrid, grouped, recommend, discover, distance matrices.',
  },
  {
    title: 'Production-grade safety',
    body: 'A read-only guard removes every mutating tool from the registry, Pydantic validates every input, and BYO mode re-resolves DNS on each request to defeat SSRF.',
  },
  {
    title: 'Runs how you need it',
    body: 'PyPI, Docker, or the Claude Desktop .mcpb bundle. Toolsets are opt-in, and bring-your-own-Qdrant mode needs no database of its own.',
  },
  {
    title: 'Observable',
    body: 'Telemetry, Prometheus metrics, resource quotas, and self-diagnosed issues — know what your Qdrant deployment is doing, not flying blind.',
  },
]

useReveal(root, () => {
  gsap.from('.benefit-card', {
    y: 20,
    opacity: 0,
    duration: 0.6,
    ease: 'power2.out',
    stagger: 0.1,
    scrollTrigger: { trigger: root.value, start: 'top 80%', once: true },
  })
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-5xl px-6 py-20">
    <div class="grid gap-6 sm:grid-cols-2">
      <div v-for="b in benefits" :key="b.title" class="benefit-card rounded-lg border border-border bg-surface p-6">
        <h3 class="font-heading text-lg font-semibold text-text-primary">{{ b.title }}</h3>
        <p class="mt-2 text-sm text-text-secondary">{{ b.body }}</p>
      </div>
    </div>
  </section>
</template>
