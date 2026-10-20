<script setup lang="ts">
import type { Lang } from '~/content/copy'
import { AUTHOR, REPO_URL, provideLanding } from '~/composables/useLanding'

const props = defineProps<{ lang: Lang }>()

const landing = provideLanding(props.lang)
const { copy, t, alternate } = landing

// The canonical site URL is not known to the repository: it depends on where the site is
// hosted. When NUXT_PUBLIC_SITE_URL is set at build time, canonical / hreflang / Open Graph
// URLs are emitted with it; when it is not, those tags are left out rather than invented.
const siteUrl = (useRuntimeConfig().public.siteUrl as string).replace(/\/$/, '')
const self = props.lang === 'en' ? '/' : '/es/'
const title = t(copy.meta.title)
const description = t(copy.meta.description)

useHead({
  htmlAttrs: { lang: copy.htmlLang },
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
    { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
    { rel: 'manifest', href: '/site.webmanifest' },
    ...(siteUrl
      ? [
          { rel: 'canonical', href: `${siteUrl}${self}` },
          { rel: 'alternate', hreflang: 'en', href: `${siteUrl}/` },
          { rel: 'alternate', hreflang: 'es', href: `${siteUrl}/es/` },
          { rel: 'alternate', hreflang: 'x-default', href: `${siteUrl}/` },
        ]
      : []),
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@graph': [
          {
            '@type': 'SoftwareSourceCode',
            name: 'Qdrant MCP',
            alternateName: 'mcp-qdrant',
            codeRepository: REPO_URL,
            programmingLanguage: 'Python',
            license: 'https://opensource.org/licenses/MIT',
            description,
            author: { '@type': 'Person', name: AUTHOR.name },
          },
          {
            '@type': 'Person',
            name: AUTHOR.name,
            url: AUTHOR.github,
            sameAs: [AUTHOR.github, AUTHOR.linkedin],
          },
        ],
      }),
    },
  ],
})

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogType: 'website',
  ogLocale: props.lang === 'en' ? 'en_US' : 'es_ES',
  twitterCard: 'summary_large_image',
  twitterTitle: title,
  twitterDescription: description,
  themeColor: '#F2EFE7',
  ...(siteUrl
    ? {
        ogUrl: `${siteUrl}${self}`,
        ogImage: `${siteUrl}/og.png`,
        ogImageWidth: 1200,
        ogImageHeight: 630,
        ogImageAlt: t(copy.meta.ogAlt),
        twitterImage: `${siteUrl}/og.png`,
      }
    : {}),
})
void alternate
</script>

<template>
  <div>
    <a
      href="#main"
      class="sr-only z-[70] bg-ink px-4 py-3 text-ui text-paper focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
    >
      {{ copy.a11y.skip }}
    </a>
    <SiteMasthead />
    <ClientOnly>
      <RulerSpine />
      <ProbeCursor />
    </ClientOnly>
    <main id="main">
      <HeroSection />
      <ProofBand />
      <MethodSection />
      <ArchitectureSection />
      <ScenariosSection />
      <ToolExplorer />
      <InstallSection />
      <EngineeringLog />
      <QualitySection />
      <FaqSection />
      <ContactSection />
    </main>
    <SiteFooter />
  </div>
</template>
