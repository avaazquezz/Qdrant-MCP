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
  <section ref="root" class="mx-auto max-w-3xl px-6 py-24 text-center">
    <div class="cta-final-inner">
      <h2 class="font-heading text-3xl font-bold text-text-primary">
        Point your MCP client at your Qdrant. Get the whole API.
      </h2>
      <div class="mt-8 flex flex-wrap items-center justify-center gap-4">
        <div class="flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2">
          <code class="font-mono text-sm text-text-primary">uvx mcp-qdrant</code>
          <UiCopyButton text="uvx mcp-qdrant" />
        </div>
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP"
          target="_blank"
          rel="noopener"
          class="rounded-md border border-border px-4 py-2 text-sm text-text-primary transition-colors hover:border-accent"
        >
          View on GitHub
        </a>
      </div>
    </div>
  </section>
</template>
