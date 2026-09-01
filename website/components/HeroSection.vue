<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap
    .timeline({ defaults: { ease: 'power2.out' } })
    .from('.hero-eyebrow', { y: 16, opacity: 0, duration: 0.5 })
    .from('.hero-wordmark', { y: 40, opacity: 0, duration: 0.8 }, '-=0.25')
    .from('.hero-subtitle', { y: 20, opacity: 0, duration: 0.6 }, '-=0.4')
    .from('.hero-cta-row > *', { y: 16, opacity: 0, duration: 0.5, stagger: 0.08 }, '-=0.3')
})
</script>

<template>
  <section ref="root" class="relative overflow-hidden border-b border-hairline">
    <div class="pointer-events-none absolute inset-0 opacity-[0.35]">
      <VectorField />
    </div>
    <div
      class="pointer-events-none absolute inset-0 bg-gradient-to-b from-ink via-ink/60 to-ink"
    />

    <span class="pointer-events-none absolute left-6 top-6 font-mono text-[10px] text-dust/50 sm:left-10 sm:top-10">+</span>
    <span class="pointer-events-none absolute right-6 top-6 font-mono text-[10px] text-dust/50 sm:right-10 sm:top-10">+</span>
    <span class="pointer-events-none absolute bottom-6 left-6 font-mono text-[10px] text-dust/50 sm:bottom-10 sm:left-10">+</span>
    <span class="pointer-events-none absolute bottom-6 right-6 font-mono text-[10px] text-dust/50 sm:bottom-10 sm:right-10">+</span>

    <div class="relative mx-auto max-w-4xl px-6 pb-28 pt-36 text-center sm:pt-48">
      <p class="hero-eyebrow font-mono text-xs uppercase tracking-[0.25em] text-pulse">
        model context protocol · vector search
      </p>
      <h1
        class="hero-wordmark mt-6 font-display text-6xl italic tracking-tight text-paper sm:text-7xl"
      >
        Qdrant MCP
      </h1>
      <p class="hero-subtitle mx-auto mt-6 max-w-xl text-lg leading-relaxed text-dust">
        The full Qdrant API as MCP tools — collections, every search mode, payload,
        snapshots, observability. Not just
        <code class="font-mono text-paper">store</code>/<code class="font-mono text-paper">find</code>.
      </p>
      <div class="hero-cta-row mt-10 flex flex-wrap items-center justify-center gap-4">
        <div class="flex items-center gap-2 border border-hairline bg-graphite px-4 py-2">
          <code class="font-mono text-sm text-paper">uvx mcp-qdrant</code>
          <UiCopyButton text="uvx mcp-qdrant" />
        </div>
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP"
          target="_blank"
          rel="noopener"
          class="font-mono text-sm text-dust underline decoration-hairline underline-offset-4 transition-colors hover:text-paper"
        >
          View on GitHub →
        </a>
      </div>
    </div>
  </section>
</template>
