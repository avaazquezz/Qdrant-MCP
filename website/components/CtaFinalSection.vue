<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap.from('.cta-final-inner', {
    y: 16,
    opacity: 0,
    duration: 0.5,
    ease: 'power2.out',
    scrollTrigger: { trigger: root.value, start: 'top 85%', once: true },
  })
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-3xl px-6 py-28 text-center">
    <div class="cta-final-inner">
      <p class="font-mono text-xs uppercase tracking-[0.25em] text-dust/70">nearest neighbor: you</p>
      <h2 class="mt-4 font-display text-4xl italic text-paper">
        Point your MCP client at your Qdrant.
      </h2>
      <div class="mt-8 flex flex-wrap items-center justify-center gap-4">
        <div class="flex items-center gap-2 border border-hairline bg-graphite px-4 py-2">
          <code class="font-mono text-sm text-paper">uvx mcp-qdrant</code>
          <UiCopyButton text="uvx mcp-qdrant" />
        </div>
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP"
          target="_blank"
          rel="noopener"
          class="border border-hairline px-4 py-2 font-mono text-sm text-paper transition-colors hover:border-signal"
        >
          View on GitHub
        </a>
      </div>
    </div>
  </section>
</template>
