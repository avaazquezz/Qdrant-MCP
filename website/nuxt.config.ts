export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/fonts'],
  css: ['~/assets/css/main.css'],
  // Two families, five faces total: every one of them is used somewhere on the page.
  fonts: {
    families: [
      { name: 'Archivo', provider: 'google', weights: ['400', '500', '700'], styles: ['normal'], subsets: ['latin'] },
      { name: 'IBM Plex Mono', provider: 'google', weights: ['400', '600'], styles: ['normal'], subsets: ['latin'] },
    ],
  },
  runtimeConfig: {
    public: {
      // Where the site is hosted. Canonical, hreflang, Open Graph URLs, the sitemap and
      // robots.txt all derive from it. NUXT_PUBLIC_SITE_URL overrides it at build time
      // (e.g. for a preview host); set it empty and those tags are omitted.
      siteUrl: 'https://vazquezdev.pro',
    },
  },
  // Two static pages, one per language. The language switcher links between them, so the
  // crawler would find both; listing them keeps the build independent of that.
  nitro: { prerender: { routes: ['/', '/es/', '/sitemap.xml', '/robots.txt'] } },
  // The page has no client-side navigation to prefetch for.
  experimental: { payloadExtraction: false },
  typescript: { typeCheck: true },
})
