<script setup lang="ts">
const dockerRun = `docker run --rm -p 8000:8000 \\
  -e QDRANT_URL=http://host.docker.internal:6333 \\
  -e QDRANT_MCP_TRANSPORT=streamable-http \\
  -e QDRANT_MCP_HTTP_HOST=0.0.0.0 \\
  -e QDRANT_MCP_SHARED_SECRET=<a long random secret> \\
  ghcr.io/avaazquezz/qdrant-mcp:latest`

const claudeConfig = `{
  "mcpServers": {
    "qdrant": {
      "command": "uvx",
      "args": ["mcp-qdrant"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_MCP_TOOLSETS": "core,search"
      }
    }
  }
}`

const snippets = [
  { title: 'PyPI (recommended)', code: 'uvx mcp-qdrant' },
  { title: 'pip', code: 'pip install mcp-qdrant' },
  { title: 'Docker', code: dockerRun },
  { title: 'claude_desktop_config.json / .mcp.json', code: claudeConfig },
]
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2">
    <div v-for="s in snippets" :key="s.title" class="border border-hairline bg-graphite p-4">
      <div class="mb-2 flex items-center justify-between">
        <p class="font-mono text-xs uppercase tracking-wide text-dust">{{ s.title }}</p>
        <UiCopyButton :text="s.code" />
      </div>
      <pre class="overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs text-paper">{{ s.code }}</pre>
    </div>
  </div>
</template>
