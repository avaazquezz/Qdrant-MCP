<script setup lang="ts">
import gsap from 'gsap'

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
    <p class="reveal font-mono text-xs uppercase tracking-[0.25em] text-dust/70">see it run</p>
    <h2 class="reveal mt-4 font-display text-3xl italic text-paper">A real client session</h2>
    <p class="reveal mt-2 text-dust">Health check, create a collection, upsert, query.</p>
    <div class="reveal mt-8">
      <ProductTerminalDemo />
    </div>

    <p class="reveal mt-20 font-mono text-xs uppercase tracking-[0.25em] text-dust/70">every tool</p>
    <h2 class="reveal mt-4 font-display text-3xl italic text-paper">Generated, not hand-written</h2>
    <p class="reveal mt-2 text-dust">Straight from the live tool registry.</p>
    <div class="reveal mt-8">
      <ProductToolCatalog />
    </div>

    <p class="reveal mt-20 font-mono text-xs uppercase tracking-[0.25em] text-dust/70">get it running</p>
    <div class="reveal mt-8">
      <ProductInstallSnippets />
    </div>
  </section>
</template>
