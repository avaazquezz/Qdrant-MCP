<script setup lang="ts">
import gsap from 'gsap'

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
    <h2 class="reveal font-heading text-2xl font-semibold text-text-primary">See it run</h2>
    <p class="reveal mt-2 text-text-secondary">
      A real client session — health check, create a collection, upsert, query.
    </p>
    <div class="reveal mt-8">
      <ProductTerminalDemo />
    </div>

    <h2 class="reveal mt-16 font-heading text-2xl font-semibold text-text-primary">Every tool</h2>
    <p class="reveal mt-2 text-text-secondary">
      Generated straight from the live tool registry — never hand-maintained.
    </p>
    <div class="reveal mt-8">
      <ProductToolCatalog />
    </div>

    <h2 class="reveal mt-16 font-heading text-2xl font-semibold text-text-primary">Get it running</h2>
    <div class="reveal mt-8">
      <ProductInstallSnippets />
    </div>
  </section>
</template>
