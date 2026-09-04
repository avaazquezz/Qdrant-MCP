export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/fonts'],
  css: ['~/assets/css/main.css'],
  // Two families, five faces total — every one of them used somewhere on
  // the page. Trimmed from three families / 32 shipped woff2 files, most
  // of which no component ever referenced.
  fonts: {
    families: [
      { name: 'Archivo', provider: 'google', weights: ['400', '500', '700'], styles: ['normal'], subsets: ['latin'] },
      { name: 'IBM Plex Mono', provider: 'google', weights: ['400', '600'], styles: ['normal'], subsets: ['latin'] },
    ],
  },
  // Drops the extra _payload.json round trip on a page with no client-side
  // navigation to prefetch for.
  experimental: { payloadExtraction: false },
  typescript: { typeCheck: true },
})
