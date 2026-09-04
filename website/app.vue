<script setup lang="ts">
const SITE_URL = 'https://mcp-qdrant-web.vazquezlabs.com/'
const REPO_URL = 'https://github.com/avaazquezz/Qdrant-MCP'

useSeoMeta({
  title: 'Qdrant MCP — 49 MCP tools for the Qdrant API, no embedding step',
  description:
    'An unofficial, MIT-licensed MCP server that registers one tool per Qdrant operation: 49 tools across collections, every search mode, payload, snapshots and observability. It never generates embeddings — you bring your own vectors. The official server has two tools.',
  ogTitle: 'Qdrant MCP — 49 MCP tools for the Qdrant API',
  ogDescription:
    '49 tools across five toolsets, 13 by default. Never embeds anything. MIT, on PyPI as mcp-qdrant. Not affiliated with Qdrant.',
  ogType: 'website',
  ogUrl: SITE_URL,
  ogImage: `${SITE_URL}og.png`,
  ogImageWidth: 1200,
  ogImageHeight: 630,
  ogImageAlt: "Qdrant's API as 49 MCP tools. No embedding step.",
  twitterCard: 'summary_large_image',
  twitterTitle: 'Qdrant MCP — 49 MCP tools for the Qdrant API',
  twitterDescription:
    '49 tools across five toolsets, 13 by default. Never embeds anything. MIT, on PyPI as mcp-qdrant. Not affiliated with Qdrant.',
  twitterImage: `${SITE_URL}og.png`,
  themeColor: '#F2EFE7',
  colorScheme: 'light',
})

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'SoftwareApplication',
      name: 'Qdrant MCP',
      alternateName: 'mcp-qdrant',
      applicationCategory: 'DeveloperApplication',
      operatingSystem: 'Linux, macOS, Windows',
      softwareVersion: '1.1.1',
      license: 'https://opensource.org/licenses/MIT',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      downloadUrl: 'https://pypi.org/project/mcp-qdrant/',
      softwareRequirements: 'Python 3.12+; Qdrant server v1.19.0 or newer',
      isAccessibleForFree: true,
      url: SITE_URL,
    },
    {
      '@type': 'SoftwareSourceCode',
      codeRepository: REPO_URL,
      programmingLanguage: 'Python',
      license: 'https://opensource.org/licenses/MIT',
      author: { '@type': 'Person', name: 'avaazquezz' },
    },
    {
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'Do I need a Qdrant already running?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'No. Set QDRANT_LOCAL_PATH to a directory and the qdrant-client SDK runs Qdrant embedded, on disk, in the same process — no server, no Docker. QDRANT_URL and QDRANT_LOCAL_PATH are mutually exclusive; if you set neither, the SDK falls back to its own default of localhost:6333.',
          },
        },
        {
          '@type': 'Question',
          name: 'What breaks on a Qdrant older than 1.19?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Two payload tools, qdrant_collection_vector_create and qdrant_collection_vector_delete, hit an endpoint that returns 404 on older servers — verified against v1.13.6 and v1.15.1. Everything else works. v1.19.0 is the only version this project tests against.',
          },
        },
        {
          '@type': 'Question',
          name: 'Can I stop it writing to my production data?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'QDRANT_MCP_READ_ONLY=1 removes every tool that is not marked read-only from the registry itself. 26 tools remain, 23 are gone, and a client calling tools/list never sees them. There is no permission check to get past, because there is no code path left.',
          },
        },
        {
          '@type': 'Question',
          name: 'Is 49 tools going to fill my context window?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'The default is core: 13 tools. Toolsets are opt-in through QDRANT_MCP_TOOLSETS, and admin is a valid name that registers nothing. Build the surface you want in the panel and copy the config it produces.',
          },
        },
        {
          '@type': 'Question',
          name: "Is this Qdrant's project?",
          acceptedAnswer: {
            '@type': 'Answer',
            text: "No. It is independent, MIT-licensed, and not affiliated with or endorsed by Qdrant. It wraps Qdrant's own qdrant-client SDK and reuses that SDK's Pydantic models for tool input, so the schemas track the SDK version instead of a hand-maintained copy.",
          },
        },
        {
          '@type': 'Question',
          name: 'Is it really the whole API?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Not quite, and the gap is deliberate: collection aliases and cluster/shard administration are not exposed. Real resharding only exists on Qdrant Cloud and the rest only matters for a distributed deployment. Everything under collections, points, search, payload, indexing, snapshots and observability is here — 49 tools.',
          },
        },
      ],
    },
  ],
}

useHead({
  htmlAttrs: { lang: 'en' },
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
    { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
    { rel: 'manifest', href: '/site.webmanifest' },
    { rel: 'canonical', href: SITE_URL },
  ],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonLd) }],
})
</script>

<template>
  <SiteMasthead />
  <div class="mx-auto flex max-w-sheet gap-8 px-6">
    <SiteSpine />
    <main class="min-w-0 flex-1">
      <HeroSection />
      <ProofBand />
      <ComparisonSection />
      <JobsSection />
      <ToolsetSection />
      <RegisterSection />
      <ObjectionsSection />
    </main>
  </div>
  <ColophonSection />
</template>
