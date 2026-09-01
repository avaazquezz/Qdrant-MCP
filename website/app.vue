<script setup lang="ts">
useSeoMeta({
  title: 'Qdrant MCP',
  description:
    'MCP server exposing the full Qdrant vector database API as tools — collections, every search mode, payload, snapshots, observability. Not just store/find. MIT licensed.',
  ogTitle: 'Qdrant MCP',
  ogDescription:
    'The full Qdrant API as MCP tools — not just store/find. Full collection & point lifecycle, every search mode, snapshots, observability.',
})
useHead({
  htmlAttrs: { lang: 'en' },
})
</script>

<template>
  <main class="min-h-screen bg-bg">
    <HeroSection />
    <TrustBar />
    <ComparisonSection />
    <BenefitsSection />
    <ProductSection />
    <FaqSection />
    <CtaFinalSection />
    <SiteFooter />
  </main>
</template>
