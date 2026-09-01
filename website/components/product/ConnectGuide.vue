<script setup lang="ts">
import gsap from 'gsap'

const composeSnippet = `services:
  qdrant:
    image: qdrant/qdrant:latest
    restart: unless-stopped
    environment:
      QDRANT__SERVICE__API_KEY: \${QDRANT_API_KEY}
    volumes:
      - ./qdrant_storage:/qdrant/storage`

const claudeCodeSnippet = `{
  "mcpServers": {
    "qdrant": {
      "command": "uvx",
      "args": ["mcp-qdrant"],
      "env": {
        "QDRANT_URL": "https://your-qdrant.example.com:6333",
        "QDRANT_API_KEY": "\${QDRANT_API_KEY}",
        "QDRANT_MCP_TOOLSETS": "core,search"
      }
    }
  }
}`

const steps = [
  {
    n: '01',
    title: 'Run your own Qdrant',
    body: "docker compose up on your server. The API key is Qdrant's own auth — nothing to do with this MCP server yet.",
    code: composeSnippet,
    lang: 'docker-compose.yml',
  },
  {
    n: '02',
    title: 'Point Claude Code at it',
    body: 'Local/stdio — the simplest path. Works as long as Claude Code can reach your Qdrant URL directly.',
    code: claudeCodeSnippet,
    lang: '.mcp.json',
  },
]

const root = ref<HTMLElement | null>(null)

useReveal(root, () => {
  gsap.from('.connect-step', {
    opacity: 0,
    x: -16,
    duration: 0.5,
    ease: 'power2.out',
    stagger: 0.15,
    scrollTrigger: { trigger: root.value, start: 'top 75%', once: true },
  })
})
</script>

<template>
  <div ref="root" class="mt-8 divide-y divide-hairline border-y border-hairline">
    <div v-for="s in steps" :key="s.n" class="connect-step grid gap-4 py-8 sm:grid-cols-[80px_1fr]">
      <span class="font-display text-4xl italic text-dust/40">{{ s.n }}</span>
      <div>
        <h3 class="font-display text-xl italic text-paper">{{ s.title }}</h3>
        <p class="mt-1.5 max-w-xl text-sm leading-relaxed text-dust">{{ s.body }}</p>
        <div class="mt-4 border border-hairline bg-graphite p-4 transition-colors hover:border-signal/40">
          <div class="mb-2 flex items-center justify-between">
            <p class="font-mono text-xs uppercase tracking-wide text-dust">{{ s.lang }}</p>
            <UiCopyButton :text="s.code" />
          </div>
          <pre class="overflow-x-auto whitespace-pre font-mono text-xs text-paper">{{ s.code }}</pre>
        </div>
      </div>
    </div>

    <div class="connect-step grid gap-4 py-8 sm:grid-cols-[80px_1fr]">
      <span class="font-display text-4xl italic text-dust/40">03</span>
      <div>
        <h3 class="font-display text-xl italic text-paper">Connect claude.ai</h3>
        <p class="mt-1.5 max-w-xl text-sm leading-relaxed text-dust">
          claude.ai only reaches remote servers — deploy this MCP once in
          <code class="font-mono text-paper">QDRANT_MCP_BYO=1</code> mode, then add a custom
          connector with authentication <span class="text-paper">None</span> and two request
          headers:
        </p>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <div class="border border-hairline bg-graphite p-4 transition-colors hover:border-signal/40">
            <p class="font-mono text-xs uppercase tracking-wide text-dust">Authorization</p>
            <p class="mt-2 break-all font-mono text-xs text-paper">https://your-qdrant.example.com:6333</p>
            <p class="mt-2 text-xs text-dust">Your Qdrant URL — sent as-is, no Bearer prefix.</p>
          </div>
          <div class="border border-hairline bg-graphite p-4 transition-colors hover:border-signal/40">
            <p class="font-mono text-xs uppercase tracking-wide text-dust">x-api-key</p>
            <p class="mt-2 break-all font-mono text-xs text-paper">your QDRANT_API_KEY</p>
            <p class="mt-2 text-xs text-dust">Only needed if your instance requires one.</p>
          </div>
        </div>
        <p class="mt-3 text-xs text-dust">
          Your Qdrant must be reachable over public HTTPS for this path — the SSRF guard rejects
          private/internal addresses.
        </p>
      </div>
    </div>
  </div>
</template>
