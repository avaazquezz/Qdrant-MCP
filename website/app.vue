<script setup lang="ts">
useSeoMeta({
  title: 'Qdrant MCP',
  description:
    'MCP server exposing the full Qdrant vector database API as tools — collections, every search mode, payload, snapshots, observability. Not just store/find. MIT licensed.',
  ogTitle: 'Qdrant MCP',
  ogDescription:
    'The full Qdrant API as MCP tools — not just store/find. Full collection & point lifecycle, every search mode, snapshots, observability.',
  ogUrl: 'https://mcp-qdrant-web.vazquezlabs.com/',
})
useHead({
  htmlAttrs: { lang: 'en' },
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
    { rel: 'canonical', href: 'https://mcp-qdrant-web.vazquezlabs.com/' },
  ],
})
</script>

<template>
  <main class="min-h-screen bg-ink">
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
