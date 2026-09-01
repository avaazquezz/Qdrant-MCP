<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap
    .timeline({ defaults: { ease: 'power2.out' } })
    .from('.hero-wordmark', { y: 40, opacity: 0, duration: 0.8 })
    .from('.hero-subtitle', { y: 20, opacity: 0, duration: 0.6 }, '-=0.35')
    .from('.hero-cta-row > *', { y: 16, opacity: 0, duration: 0.5, stagger: 0.08 }, '-=0.3')
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-4xl px-6 pb-24 pt-32 text-center sm:pt-40">
    <h1 class="hero-wordmark font-heading text-5xl font-bold tracking-tight text-text-primary sm:text-6xl">
      Qdrant MCP
    </h1>
    <p class="hero-subtitle mx-auto mt-6 max-w-2xl text-lg text-text-secondary">
      The full Qdrant API as MCP tools — collections, every search mode, payload,
      snapshots, observability. Not just <code class="font-mono text-text-primary">store</code>/<code class="font-mono text-text-primary">find</code>.
    </p>
    <div class="hero-cta-row mt-10 flex flex-wrap items-center justify-center gap-4">
      <div class="flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2">
        <code class="font-mono text-sm text-text-primary">uvx mcp-qdrant</code>
        <UiCopyButton text="uvx mcp-qdrant" />
      </div>
      <a
        href="https://github.com/avaazquezz/Qdrant-MCP"
        target="_blank"
        rel="noopener"
        class="rounded-md px-4 py-2 text-sm text-text-secondary underline decoration-border underline-offset-4 transition-colors hover:text-text-primary"
      >
        View on GitHub
      </a>
    </div>
  </section>
</template>
