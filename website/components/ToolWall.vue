<script setup lang="ts">
import tools from '~/data/tools.generated.json'
import { computed } from 'vue'

const TOOLSET_ORDER = ['core', 'search', 'payload', 'snapshots', 'observability'] as const

const bands = computed(() => {
  let i = 0
  return TOOLSET_ORDER.map((name) => ({
    name,
    tools: tools
      .filter((t) => t.toolset === name)
      .map((t) => ({ ...t, index: i++ })),
  }))
})
</script>

<template>
  <div>
    <!-- Full specimen — every real tool name, generated straight from the
         registry dump, so this cannot drift from what the server actually
         registers without CI's own gen_tools_json.py --check failing. -->
    <div class="hidden lg:block" aria-hidden="false">
      <div v-for="(band, bandIndex) in bands" :key="band.name" class="mb-4 last:mb-0">
        <div
          class="anim-draw flex items-baseline justify-between border-t border-ink pt-1.5"
          :style="{ animationDelay: `${bandIndex * 70}ms` }"
        >
          <span class="font-mono text-ordinal text-ink">{{ band.name }}</span>
          <span class="font-mono text-ordinal text-ink">{{ band.tools.length }}</span>
        </div>
        <ul class="mt-2 columns-2 gap-x-6">
          <li v-for="t in band.tools" :key="t.name" class="mb-1.5 break-inside-avoid">
            <a
              :href="`#tool-${t.name}`"
              class="anim-stamp inline-flex items-start gap-1.5 font-mono text-micro leading-relaxed text-ink no-underline hover:underline focus-visible:underline"
              :style="{ animationDelay: `${120 + t.index * 14}ms` }"
            >
              <span
                class="mt-[3px] h-[6px] w-[6px] shrink-0"
                :class="t.read_only ? 'border border-ink' : 'bg-spot'"
                aria-hidden="true"
              />
              <span class="[overflow-wrap:anywhere]">{{ t.name }}</span>
            </a>
          </li>
        </ul>
      </div>
    </div>

    <!-- Below 1024px the specimen collapses to band headers only — the 49
         names are ~1,100px of scroll on a phone and are printed in full,
         filterable, in the register (§05) anyway. -->
    <div class="lg:hidden">
      <div v-for="band in bands" :key="band.name" class="flex items-baseline justify-between border-t border-ink py-2">
        <span class="font-mono text-ui text-ink">{{ band.name }}</span>
        <span class="font-mono text-ui text-ink">{{ band.tools.length }}</span>
      </div>
      <a href="#s-05" class="mt-4 inline-block text-ui text-ink underline decoration-1 underline-offset-4">
        Read all 49 in the register
      </a>
    </div>
  </div>
</template>
