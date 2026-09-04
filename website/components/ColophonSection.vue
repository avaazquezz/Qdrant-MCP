<script setup lang="ts">
import { defaultConfigJson } from '~/composables/useToolsets'

const config = defaultConfigJson()
</script>

<template>
  <footer role="contentinfo" class="on-ink bg-ink py-12 text-paper lg:py-20">
    <div id="s-07" data-section="07" class="mx-auto max-w-sheet px-6">
      <div class="section-rule border-t-2 border-paper" />
      <h2 class="mt-8 max-w-prose text-h2 text-paper">
        Add it, enable core, and ask your client to list its tools.
      </h2>
      <p class="mt-4 max-w-prose text-body text-mist">
        Paste the config into <span class="font-mono">.mcp.json</span> or
        <span class="font-mono">claude_desktop_config.json</span>, restart the client, and ask it
        to list its tools. You should see 13.
      </p>
      <div class="mt-8">
        <UiCopyButton :text="config" label="Copy the config" variant="primary" invert />
      </div>

      <div class="mt-14 overflow-x-auto border-t border-mist pt-8">
        <table class="w-full min-w-[640px] border-collapse text-micro">
          <caption class="sr-only">Project colophon</caption>
          <tbody class="font-mono">
            <tr class="border-b border-mist">
              <td class="py-2 pr-6 text-mist">version</td>
              <td class="py-2 pr-6 text-paper">1.1.1</td>
              <td class="py-2 pr-6 text-mist">licence</td>
              <td class="py-2 pr-6 text-paper">MIT</td>
            </tr>
            <tr class="border-b border-mist">
              <td class="py-2 pr-6 text-mist">package</td>
              <td class="py-2 pr-6 text-paper">mcp-qdrant on PyPI</td>
              <td class="py-2 pr-6 text-mist">image</td>
              <td class="py-2 pr-6 text-paper">ghcr.io/avaazquezz/qdrant-mcp</td>
            </tr>
            <tr class="border-b border-mist">
              <td class="py-2 pr-6 text-mist">tests</td>
              <td class="py-2 pr-6 text-paper">157</td>
              <td class="py-2 pr-6 text-mist">integration</td>
              <td class="py-2 pr-6 text-paper">qdrant/qdrant:v1.19.0</td>
            </tr>
            <tr class="border-b border-mist">
              <td class="py-2 pr-6 text-mist">requires</td>
              <td class="py-2 pr-6 text-paper">Python 3.12+, Qdrant 1.19+</td>
              <td class="py-2 pr-6 text-mist">catalog</td>
              <td class="py-2 pr-6 text-paper">generated from the running registry</td>
            </tr>
            <tr>
              <td class="py-2 pr-6 text-mist">set in</td>
              <td class="py-2 pr-6 text-paper">Archivo &amp; IBM Plex Mono</td>
              <td class="py-2 pr-6 text-mist">maintained by</td>
              <td class="py-2 pr-6 text-paper">@avaazquezz</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-8 flex flex-wrap items-center justify-between gap-4 text-micro text-mist">
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP"
          target="_blank"
          rel="noopener"
          class="font-mono underline decoration-1 underline-offset-4"
        >github.com/avaazquezz/Qdrant-MCP<span class="sr-only"> (opens in a new tab)</span></a>
        <p>An independent project, not affiliated with or endorsed by Qdrant.</p>
      </div>
    </div>
  </footer>
</template>
