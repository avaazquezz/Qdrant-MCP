<script setup lang="ts">
import { defaultConfigJson } from '~/composables/useToolsets'

const config = defaultConfigJson()
</script>

<template>
  <section id="s-01" data-section="01" class="flex min-h-[max(720px,100svh)] flex-col justify-center pb-12 pt-8 lg:pt-12">
    <div class="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-8">
      <div class="min-w-0 lg:col-span-6">
        <h1 class="text-display text-ink">
          Qdrant's API as
          <br />
          <span class="text-spot">49</span> MCP tools.
          <br />
          No embedding step.
        </h1>

        <p class="mt-6 max-w-prose text-deck text-graphite">
          The official server hands your client two tools, <code class="font-mono">qdrant-store</code>
          and <code class="font-mono">qdrant-find</code>, and runs your documents through its own
          embedding model. This one registers a tool per Qdrant operation and never touches your
          vectors.
        </p>

        <div class="mt-8 flex flex-wrap items-center gap-4">
          <UiCopyButton :text="config" label="Copy the config" variant="primary" />
          <a
            href="https://github.com/avaazquezz/Qdrant-MCP"
            target="_blank"
            rel="noopener"
            class="flex h-11 items-center rounded-sm border border-ink px-4 text-ui text-ink transition-colors hover:bg-ink hover:text-paper"
          >Read the source<span class="sr-only"> (opens in a new tab)</span></a>
        </div>

        <table class="mt-10 w-full max-w-prose border-collapse border-t border-ink text-ui">
          <caption class="sr-only">Requirements and defaults</caption>
          <tbody>
            <tr class="border-b border-ink">
              <th scope="row" class="w-40 py-2 pr-4 text-left font-normal text-graphite">requires</th>
              <td class="py-2 text-ink">Qdrant server v1.19.0 or newer</td>
            </tr>
            <tr class="border-b border-ink">
              <th scope="row" class="w-40 py-2 pr-4 text-left font-normal text-graphite">runtime</th>
              <td class="py-2 text-ink">Python 3.12 or newer</td>
            </tr>
            <tr class="border-b border-ink">
              <th scope="row" class="w-40 py-2 pr-4 text-left font-normal text-graphite">default set</th>
              <td class="py-2 text-ink"><span class="font-mono">core</span>, 13 of the 49 tools</td>
            </tr>
            <tr class="border-b border-ink">
              <th scope="row" class="w-40 py-2 pr-4 text-left font-normal text-graphite">licence</th>
              <td class="py-2 text-ink">MIT. On PyPI as <span class="font-mono">mcp-qdrant</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="min-w-0 lg:col-span-6">
        <h2 class="sr-only">All 49 tool names</h2>
        <ToolWall />
      </div>
    </div>

    <div class="section-rule mt-10 border-t-2 border-ink" />
  </section>
</template>
