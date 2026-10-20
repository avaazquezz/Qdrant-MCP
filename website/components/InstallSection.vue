<script setup lang="ts">
import { useLanding } from '~/composables/useLanding'
import { TOOLSET_ORDER, TOOLSETS, useToolsets } from '~/composables/useToolsets'

const { copy } = useLanding()
const { enabled, readOnly, registeredCount, configJson, forcedCoreNotice } = useToolsets()

const DOCKER = `docker run --rm -p 8000:8000 \\
  -e QDRANT_URL=http://host.docker.internal:6333 \\
  -e QDRANT_MCP_TRANSPORT=streamable-http \\
  -e QDRANT_MCP_HTTP_HOST=0.0.0.0 \\
  -e QDRANT_MCP_SHARED_SECRET=<a long random secret> \\
  ghcr.io/avaazquezz/qdrant-mcp:latest`

const cl = copy.install
</script>

<template>
  <section id="install" class="border-t border-ink/30 pb-20 pt-14" aria-labelledby="install-title">
    <div class="mx-auto max-w-sheet px-4 sm:px-6">
      <h3 id="install-title" class="text-h2 font-bold">{{ cl.title }}</h3>
      <p class="mt-3 max-w-prose text-body text-graphite">{{ cl.lead }}</p>

      <div class="mt-8 grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <fieldset class="self-start border border-ink p-5">
          <legend class="px-2 font-mono text-ordinal uppercase tracking-[0.14em] text-graphite">{{ cl.toolsets }}</legend>
          <div class="grid grid-cols-[minmax(0,1fr)] gap-2.5">
            <label v-for="name in TOOLSET_ORDER" :key="name" class="flex items-center gap-3 text-ui">
              <input v-model="enabled[name]" type="checkbox" class="h-4 w-4 accent-ink" />
              <span class="font-mono">{{ name }}</span>
              <span class="measure ml-auto text-micro text-graphite">{{ TOOLSETS.find((s) => s.name === name)!.total }}</span>
            </label>
          </div>
          <label class="mt-5 flex items-center gap-3 border-t border-ink/25 pt-4 text-ui">
            <input v-model="readOnly" type="checkbox" class="h-4 w-4 accent-ink" />
            {{ cl.readOnly }}
          </label>
          <p class="mt-5 flex items-baseline justify-between border-t border-ink/25 pt-4 text-ui">
            {{ cl.registered }}
            <span class="measure text-h3 font-bold text-spot" aria-live="polite">{{ registeredCount }}</span>
          </p>
          <p v-if="forcedCoreNotice" class="mt-3 text-micro text-spot" role="status">{{ cl.forcedCore }}</p>
        </fieldset>

        <div class="grid grid-cols-[minmax(0,1fr)] content-start gap-6">
          <UiCodePlate
            title=".mcp.json"
            :code="configJson"
            :copy-label="cl.copyConfig"
            :copied-label="cl.copied"
            :failed-label="cl.copyFailed"
            :announce-copied="cl.announceCopied"
            :announce-failed="cl.announceFailed"
          />
          <ul class="grid grid-cols-[minmax(0,1fr)] gap-4 text-micro text-graphite">
            <li><span class="font-mono text-ink">uvx mcp-qdrant</span> · {{ cl.paths.uvx }}</li>
            <li>{{ cl.paths.mcpb }}</li>
            <li>
              {{ cl.paths.docker }}. {{ cl.paths.dockerNote }}
              <pre class="mt-2 overflow-x-auto border border-ink/30 bg-tint px-3 py-2 font-mono text-ordinal leading-relaxed text-ink">{{ DOCKER }}</pre>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
