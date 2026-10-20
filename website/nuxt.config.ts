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
      // Where the site is hosted, e.g. https://example.com — set NUXT_PUBLIC_SITE_URL at
      // build time. Left empty, canonical / hreflang / Open Graph URLs are omitted instead
      // of pointing at an address nobody chose.
      siteUrl: '',
    },
  },
  // Two static pages, one per language. The language switcher links between them, so the
  // crawler would find both; listing them keeps the build independent of that.
  nitro: { prerender: { routes: ['/', '/es/'] } },
  // The page has no client-side navigation to prefetch for.
  experimental: { payloadExtraction: false },
  typescript: { typeCheck: true },
})
