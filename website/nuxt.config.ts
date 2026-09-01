export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/fonts'],
  css: ['~/assets/css/main.css'],
  fonts: {
    families: [
      { name: 'Space Grotesk', provider: 'google', weights: ['500', '600', '700'] },
      { name: 'Inter', provider: 'google', weights: ['400', '500', '600'] },
      { name: 'JetBrains Mono', provider: 'google', weights: ['400', '500'] },
    ],
  },
})
