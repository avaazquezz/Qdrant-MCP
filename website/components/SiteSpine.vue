<script setup lang="ts">
import { useSectionRules } from '~/composables/useSectionRules'

const SECTIONS = [
  { id: '01', label: 'Hero — the top of the page' },
  { id: '02', label: 'Two servers, same database' },
  { id: '03', label: 'What the other 36 are for' },
  { id: '04', label: 'You choose the surface' },
  { id: '05', label: 'All 49, printed' },
  { id: '06', label: 'The things that would stop me installing this' },
  { id: '07', label: 'Add it, enable core, and ask your client to list its tools' },
] as const

const { activeId } = useSectionRules()
</script>

<template>
  <!-- Desktop only — a sticky ordinal rail outside the content field. The
       mobile equivalent (the same seven ordinals as a horizontally
       scrolling row) lives in SiteMasthead, not here: as a flex sibling
       of <main> in this component's own row, a full-width mobile bar
       would fight main for space instead of spanning the viewport. -->
  <nav aria-label="Sections" class="hidden w-[88px] shrink-0 lg:block">
    <ol class="sticky top-24 flex flex-col gap-3">
      <li v-for="s in SECTIONS" :key="s.id">
        <a
          :href="`#s-${s.id}`"
          :aria-current="activeId === s.id ? 'true' : undefined"
          :aria-label="`Section ${s.id}: ${s.label}`"
          class="flex h-5 w-5 items-center justify-center border border-ink font-mono text-ordinal transition-colors"
          :class="activeId === s.id ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-tint'"
        >{{ s.id }}</a>
      </li>
    </ol>
  </nav>
</template>
