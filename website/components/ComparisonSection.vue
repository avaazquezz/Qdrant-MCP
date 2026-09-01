<script setup lang="ts">
import gsap from 'gsap'
import tools from '~/data/tools.generated.json'

const toolCount = tools.length
const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap.utils.toArray<HTMLElement>('.reveal').forEach((el) => {
    gsap.from(el, {
      y: 16,
      opacity: 0,
      duration: 0.5,
      ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 80%', once: true },
    })
  })
})
</script>

<template>
  <section ref="root" class="mx-auto max-w-4xl px-6 py-24">
    <p class="reveal font-mono text-xs uppercase tracking-[0.25em] text-dust/70">the surface</p>

    <div class="reveal mt-4 flex flex-wrap items-end gap-x-6 gap-y-2">
      <span class="font-mono text-sm text-dust/60 line-through decoration-hairline">
        official qdrant-mcp-server · 2 tools
      </span>
    </div>

    <div class="reveal mt-2 flex flex-col gap-8 sm:flex-row sm:items-center">
      <p class="font-display text-7xl italic text-paper sm:text-8xl">{{ toolCount }}</p>
      <div class="max-w-sm">
        <p class="font-mono text-sm uppercase tracking-[0.15em] text-pulse">tools, not two</p>
        <p class="mt-2 text-sm leading-relaxed text-dust">
          Every collection, point, search, payload, snapshot, and observability operation Qdrant
          exposes. You bring your own vectors — it never embeds anything for you.
        </p>
      </div>
      <div class="hidden h-32 flex-1 sm:block">
        <VectorField :animated="false" />
      </div>
    </div>

    <div class="reveal mt-16 border-t border-hairline pt-6">
      <p class="flex flex-wrap items-center gap-3 font-mono text-sm text-dust">
        <span class="text-paper">your llm client</span>
        <span class="text-hairline">──▶</span>
        <span class="border border-signal/40 px-2 py-0.5 text-signal">qdrant mcp — thin wrapper</span>
        <span class="text-hairline">──▶</span>
        <span class="text-paper">your qdrant</span>
      </p>
      <p class="mt-4 max-w-xl text-sm leading-relaxed text-dust">
        No embeddings generated, no chunking, no vector opinions — it's not a RAG system, on
        purpose. Whatever your client wants to store or query, it brings its own vectors.
      </p>
    </div>
  </section>
</template>
