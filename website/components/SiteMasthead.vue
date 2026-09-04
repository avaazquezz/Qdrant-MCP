<script setup lang="ts">
import { useSectionRules } from '~/composables/useSectionRules'
import { defaultConfigJson } from '~/composables/useToolsets'

const NAV = [
  { href: '#s-02', label: 'two servers', id: '02' },
  { href: '#s-03', label: 'what it buys', id: '03' },
  { href: '#s-04', label: 'toolsets', id: '04' },
  { href: '#s-05', label: 'register', id: '05' },
  { href: '#s-06', label: 'objections', id: '06' },
] as const

// All seven — SiteSpine's desktop rail shows the same set; this is the
// mobile equivalent. It lives here, not in SiteSpine, because it has to be
// a full-width row of the masthead's own flow — as a flex sibling of
// <main> inside the page's content-field wrapper (where SiteSpine's
// desktop rail sits) it would fight main for a share of that row's width
// instead of spanning the viewport on its own line.
const SECTIONS = [
  { id: '01', label: 'Hero — the top of the page' },
  { id: '02', label: 'Two servers, same database' },
  { id: '03', label: 'What the other 36 are for' },
  { id: '04', label: 'You choose the surface' },
  { id: '05', label: 'All 49, printed' },
  { id: '06', label: 'The things that would stop me installing this' },
  { id: '07', label: 'Add it, enable core, and ask your client to list its tools' },
] as const

// SiteSpine already runs the section-tracking observer; a second instance
// here would double the IntersectionObserver work for the same data, so
// the masthead's nav underline reads the same activeId instead.
const { activeId } = useSectionRules()

const config = defaultConfigJson()
</script>

<template>
  <header class="sticky top-0 z-50 border-b-2 border-ink bg-paper">
    <div class="mx-auto flex h-14 max-w-sheet items-center justify-between gap-4 px-6">
      <a href="#s-01" class="flex items-center gap-2 shrink-0">
        <span class="flex h-[18px] w-[18px] items-center justify-center border border-ink" aria-hidden="true">
          <span class="h-[6px] w-[6px] rounded-full bg-spot" />
        </span>
        <span class="font-mono text-ui font-semibold text-ink">mcp-qdrant</span>
        <span class="hidden text-ui text-graphite xl:inline">unofficial MCP server for Qdrant</span>
      </a>

      <nav aria-label="Primary" class="hidden items-center gap-6 lg:flex">
        <a
          v-for="item in NAV"
          :key="item.id"
          :href="item.href"
          :aria-current="activeId === item.id ? 'true' : undefined"
          class="border-b-2 py-1 text-ui text-ink transition-colors"
          :class="activeId === item.id ? 'border-spot' : 'border-transparent hover:border-ink'"
        >{{ item.label }}</a>
      </nav>

      <div class="flex shrink-0 items-center gap-4">
        <span class="hidden font-mono text-micro text-graphite xl:inline">v1.1.1</span>
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP"
          target="_blank"
          rel="noopener"
          class="hidden text-ui text-ink underline decoration-1 underline-offset-4 hover:no-underline xl:inline"
        >Source<span class="sr-only"> (opens in a new tab)</span></a>
        <UiCopyButton :text="config" label="Copy the config" variant="primary" />
      </div>
    </div>
    <p class="px-6 pb-2 text-micro text-graphite xl:hidden">unofficial MCP server for Qdrant</p>

    <nav aria-label="Sections" class="overflow-x-auto border-t border-ink px-6 py-2 lg:hidden">
      <ol class="flex w-max gap-2">
        <li v-for="s in SECTIONS" :key="s.id">
          <a
            :href="`#s-${s.id}`"
            :aria-current="activeId === s.id ? 'true' : undefined"
            :aria-label="`Section ${s.id}: ${s.label}`"
            class="flex h-9 w-9 items-center justify-center border border-ink font-mono text-ordinal transition-colors"
            :class="activeId === s.id ? 'bg-ink text-paper' : 'bg-paper text-ink'"
          >{{ s.id }}</a>
        </li>
      </ol>
    </nav>
  </header>
</template>
