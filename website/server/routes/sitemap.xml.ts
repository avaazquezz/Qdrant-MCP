// Prerendered at build time from the same siteUrl the page's canonical / hreflang use, so
// the domain lives in one place (nuxt.config.ts).
export default defineEventHandler((event) => {
  const base = String(useRuntimeConfig(event).public.siteUrl).replace(/\/$/, '')
  if (!base) throw createError({ statusCode: 404, statusMessage: 'siteUrl is not set' })
  setHeader(event, 'content-type', 'application/xml; charset=utf-8')

  const alternates = [
    ['en', `${base}/`],
    ['es', `${base}/es/`],
    ['x-default', `${base}/`],
  ]
    .map(([lang, href]) => `<xhtml:link rel="alternate" hreflang="${lang}" href="${href}"/>`)
    .join('')
  const urls = [`${base}/`, `${base}/es/`]
    .map((loc) => `<url><loc>${loc}</loc>${alternates}</url>`)
    .join('')

  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${urls}</urlset>\n`
})
