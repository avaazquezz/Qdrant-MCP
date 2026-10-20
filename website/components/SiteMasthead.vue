<script setup lang="ts">
import { REPO_URL, useLanding } from '~/composables/useLanding'

const { copy, alternate, lang } = useLanding()

const links = [
  { id: 'method', label: copy.nav.method },
  { id: 'architecture', label: copy.nav.architecture },
  { id: 'scenarios', label: copy.nav.scenarios },
  { id: 'tools', label: copy.nav.tools },
  { id: 'log', label: copy.nav.log },
  { id: 'quality', label: copy.nav.quality },
]
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-ink bg-paper/95 backdrop-blur-sm">
    <div class="mx-auto flex max-w-sheet items-center gap-4 px-4 py-2.5 sm:px-6">
      <a
        :href="lang === 'en' ? '/' : '/es/'"
        class="flex shrink-0 items-center gap-2.5 font-mono text-ui font-semibold"
        aria-label="mcp-qdrant"
      >
        <span class="grid h-5 w-5 place-items-center border-[1.5px] border-ink" aria-hidden="true">
          <span class="h-1.5 w-1.5 rounded-full bg-spot" />
        </span>
        mcp-qdrant
      </a>

      <nav :aria-label="copy.a11y.sections" class="hidden flex-1 justify-center md:flex">
        <ul class="flex items-center gap-1">
          <li v-for="link in links" :key="link.id">
            <a
              :href="`#${link.id}`"
              class="px-3 py-2 text-micro text-graphite transition-colors duration-200 hover:text-ink"
            >
              {{ link.label }}
            </a>
          </li>
        </ul>
      </nav>
      <div class="flex-1 md:hidden" />

      <a
        :href="alternate.href"
        :hreflang="alternate.lang"
        :lang="alternate.lang"
        class="grid h-9 min-w-9 place-items-center border border-ink px-2 font-mono text-micro font-semibold transition-colors duration-200 hover:bg-ink hover:text-paper"
        :aria-label="`${copy.a11y.langSwitch}: ${alternate.lang === 'es' ? 'Español' : 'English'}`"
      >
        {{ alternate.label }}
      </a>

      <a
        :href="REPO_URL"
        target="_blank"
        rel="noopener"
        data-magnetic
        class="inline-flex min-h-10 items-center gap-2 rounded-sm border border-ink bg-ink px-3.5 text-ui text-paper transition-colors duration-200 hover:bg-transparent hover:text-ink"
      >
        {{ copy.nav.github }}
        <span aria-hidden="true">↗</span>
        <span class="sr-only">{{ copy.a11y.opensNewTab }}</span>
      </a>
    </div>

    <!-- On small screens the section links become a scrollable row: nothing is hidden behind a menu. -->
    <nav :aria-label="copy.a11y.sections" class="border-t border-ink/20 md:hidden">
      <ul class="flex gap-1 overflow-x-auto px-3 py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <li v-for="link in links" :key="link.id" class="shrink-0">
          <a :href="`#${link.id}`" class="block px-2.5 py-2 text-micro text-graphite">
            {{ link.label }}
          </a>
        </li>
      </ul>
    </nav>
  </header>
</template>
