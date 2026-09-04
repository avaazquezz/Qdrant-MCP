<script setup lang="ts">
import { computed } from 'vue'
import tools from '~/data/tools.generated.json'
import { useToolsets } from '~/composables/useToolsets'

const { TOOLSETS, TOTAL_TOOLS, enabled, readOnly, registeredCount, configJson, forcedCoreNotice } =
  useToolsets()

// One announcement, driven entirely by state — not by which handler fired —
// so it stays correct regardless of how `enabled`/`readOnly` changed.
const announcement = computed(() =>
  forcedCoreNotice.value
    ? 'At least one toolset must be enabled; core re-enabled.'
    : `${registeredCount.value} of ${TOTAL_TOOLS} tools registered.`
)

// Per-tool dot state for the register readout below. A dot is "registered"
// exactly when its toolset is on AND (read-only mode is off, or the tool
// is itself read-only) — the same rule ToolRegistry.register applies at
// runtime. Colour: spot = a write tool currently registered (so read-only
// mode must be off); ink = an inherently read-only tool, registered;
// hollow = not registered.
const dotBands = computed(() => {
  let writeIndex = 0
  return TOOLSETS.map((ts) => ({
    name: ts.name,
    dots: tools
      .filter((t) => t.toolset === ts.name)
      .map((t) => {
        const registered = enabled[ts.name] && (!readOnly.value || t.read_only)
        // 8ms stagger across the 23 write tools, in registry order, so The
        // Strike reads as a ripple leaving the registry rather than a flat
        // colour swap — read-only dots never move, so they get none.
        const delay = t.read_only ? 0 : writeIndex++ * 8
        return { name: t.name, registered, readOnly: t.read_only, delay }
      }),
  }))
})

const configLines = computed(() => {
  const enabledNames = TOOLSETS.filter((t) => enabled[t.name]).map((t) => t.name)
  return { toolsets: enabledNames.join(','), readOnly: readOnly.value }
})
</script>

<template>
  <div class="grid gap-8 lg:grid-cols-12">
    <div class="min-w-0 lg:col-span-5">
      <!-- min-w-0: browsers give <fieldset> a default min-width: min-content,
           which otherwise refuses to let it shrink below its widest row's
           intrinsic content — the classic fieldset overflow trap. -->
      <fieldset class="min-w-0 border border-ink">
        <legend class="sr-only">Toolsets to register</legend>
        <div
          v-for="ts in TOOLSETS"
          :key="ts.name"
          class="flex items-center justify-between gap-3 border-b border-ink px-4 py-3 last:border-b-0"
        >
          <label class="flex min-w-0 flex-1 items-center gap-3">
            <input
              v-model="enabled[ts.name]"
              type="checkbox"
              class="h-6 w-10 shrink-0 cursor-pointer appearance-none rounded-sm border border-ink bg-paper transition-colors checked:bg-ink"
            />
            <span class="font-mono text-ui text-ink">{{ ts.name }}</span>
          </label>
          <span class="shrink-0 text-ui text-graphite">{{ ts.total }} · {{ ts.readOnly }} ro</span>
        </div>

        <div class="flex items-center justify-between gap-3 border-t border-ink bg-tint px-4 py-3">
          <label class="flex min-w-0 flex-1 items-center gap-3">
            <input
              v-model="readOnly"
              type="checkbox"
              class="h-6 w-10 shrink-0 cursor-pointer appearance-none rounded-sm border border-ink bg-paper transition-colors checked:bg-ink"
            />
            <span>
              <span class="block font-mono text-ui text-ink">read_only</span>
              <span class="block text-micro text-graphite">removes every tool that is not read-only from the registry</span>
            </span>
          </label>
        </div>
        <div class="border-t border-ink px-4 py-3 text-micro text-graphite">
          <span class="font-mono text-ink">admin</span> — a valid toolset name that registers
          nothing. Cluster and shard administration was scoped out.
        </div>
      </fieldset>

      <p class="mt-4 max-w-prose text-body text-ink">
        Every tool description is loaded into your model's context on every conversation. That is
        why the default is <span class="font-mono">core</span> and not all five. Turn on what the
        project needs and leave the rest off.
      </p>
    </div>

    <div class="min-w-0 lg:col-span-7">
      <div class="border border-ink">
        <div class="flex items-center justify-between gap-3 border-b border-ink bg-tint px-4 py-2">
          <p class="font-mono text-micro text-ink">.mcp.json</p>
          <UiCopyButton :text="configJson" label="Copy the .mcp.json config" />
        </div>
        <pre class="overflow-x-auto bg-tint px-4 py-3 font-mono text-micro leading-relaxed text-ink"><code>{<br>&nbsp;&nbsp;"mcpServers": {<br>&nbsp;&nbsp;&nbsp;&nbsp;"qdrant": {<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"command": "uvx",<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"args": ["mcp-qdrant"],<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"env": {<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"QDRANT_URL": "http://localhost:6333",<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"QDRANT_MCP_TOOLSETS": <span class="text-spot transition-colors">"{{ configLines.toolsets }}"</span><span v-if="configLines.readOnly">,</span><template v-if="configLines.readOnly"><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="text-spot transition-colors">"QDRANT_MCP_READ_ONLY": "1"</span></template><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}<br>&nbsp;&nbsp;&nbsp;&nbsp;}<br>&nbsp;&nbsp;}<br>}</code></pre>
      </div>

      <div class="mt-6">
        <p class="font-mono text-ordinal text-ink">REGISTERED</p>
        <p class="mt-1 flex items-baseline gap-2">
          <span class="min-w-[3ch] text-readout tabular-nums text-ink">{{ registeredCount }}</span>
          <span class="text-ui text-graphite">of {{ TOTAL_TOOLS }}</span>
        </p>

        <div class="mt-4 space-y-2">
          <div v-for="band in dotBands" :key="band.name" class="flex items-center gap-3">
            <span class="w-28 shrink-0 font-mono text-micro text-graphite">{{ band.name }}</span>
            <span class="flex flex-wrap gap-1">
              <span
                v-for="dot in band.dots"
                :key="dot.name"
                class="h-[9px] w-[9px] shrink-0 rounded-full transition-colors duration-200"
                :class="
                  !dot.registered
                    ? 'border border-ink bg-transparent'
                    : dot.readOnly
                      ? 'border border-ink bg-ink'
                      : 'border border-spot bg-spot'
                "
                :style="{ transitionDelay: `${dot.delay}ms` }"
                aria-hidden="true"
              />
            </span>
          </div>
        </div>
        <p class="mt-3 text-micro text-graphite">
          Filled = registered. Red = writes to your data. Hollow = not registered.
        </p>
      </div>
    </div>
  </div>

  <p class="sr-only" role="status" aria-live="polite">{{ announcement }}</p>
</template>
