<script setup lang="ts">
import gsap from 'gsap'
import tools from '~/data/tools.generated.json'

const toolCount = tools.length
const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap.utils.toArray<HTMLElement>('.reveal').forEach((el) => {
    gsap.from(el, {
      y: 20,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 80%', once: true },
    })
  })
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-4xl px-6 py-20">
    <div class="reveal grid gap-6 sm:grid-cols-2">
      <div class="rounded-lg border border-border bg-surface p-6">
        <p class="font-mono text-sm text-text-secondary">official qdrant-mcp-server</p>
        <p class="mt-2 font-heading text-4xl font-bold text-text-secondary">2 tools</p>
        <p class="mt-2 text-sm text-text-secondary">
          <code class="font-mono">store</code> / <code class="font-mono">find</code> — embeds
          documents for you, opinionated by design.
        </p>
      </div>
      <div class="rounded-lg border border-accent bg-surface p-6">
        <p class="font-mono text-sm text-accent">this server</p>
        <p class="mt-2 font-heading text-4xl font-bold text-text-primary">{{ toolCount }} tools</p>
        <p class="mt-2 text-sm text-text-secondary">
          Every collection, point, search, payload, snapshot, and observability operation Qdrant
          exposes. You bring your own vectors.
        </p>
      </div>
    </div>

    <div class="reveal mt-12">
      <svg viewBox="0 0 720 140" class="mx-auto w-full max-w-2xl" role="img" aria-labelledby="arch-title">
        <title id="arch-title">Architecture: your LLM client talks to this thin MCP wrapper, which talks to your own Qdrant instance — no embeddings generated in between</title>
        <g font-family="JetBrains Mono, monospace" font-size="13" fill="#F2F2F5">
          <rect x="8" y="40" width="180" height="60" rx="8" fill="#12131A" stroke="#23242E" />
          <text x="98" y="65" text-anchor="middle">Your LLM client</text>
          <text x="98" y="83" text-anchor="middle" fill="#9497A6" font-size="11">Claude, etc.</text>

          <rect x="270" y="40" width="180" height="60" rx="8" fill="#12131A" stroke="#6D5EF5" stroke-width="1.5" />
          <text x="360" y="65" text-anchor="middle">Qdrant MCP</text>
          <text x="360" y="83" text-anchor="middle" fill="#9497A6" font-size="11">thin wrapper, no RAG</text>

          <rect x="532" y="40" width="180" height="60" rx="8" fill="#12131A" stroke="#23242E" />
          <text x="622" y="65" text-anchor="middle">Your Qdrant</text>
          <text x="622" y="83" text-anchor="middle" fill="#9497A6" font-size="11">your instance, your data</text>

          <path d="M188 70 H270" stroke="#23242E" stroke-width="1.5" marker-end="url(#arrow)" />
          <path d="M450 70 H532" stroke="#23242E" stroke-width="1.5" marker-end="url(#arrow)" />
        </g>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0 0 L8 4 L0 8 Z" fill="#23242E" />
          </marker>
        </defs>
      </svg>
      <p class="mt-4 text-center text-sm text-text-secondary">
        No embeddings generated, no chunking, no vector opinions — it's not a RAG system, on
        purpose. Whatever your client wants to store or query, it brings its own vectors.
      </p>
    </div>
  </section>
</template>
