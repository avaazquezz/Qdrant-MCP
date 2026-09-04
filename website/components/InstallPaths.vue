<script setup lang="ts">
const embedded = 'QDRANT_LOCAL_PATH=./qdrant_data uvx mcp-qdrant'

const remote = `QDRANT_URL=http://localhost:6333 \\
QDRANT_MCP_TRANSPORT=streamable-http \\
QDRANT_MCP_HTTP_HOST=0.0.0.0 \\
QDRANT_MCP_SHARED_SECRET=replace-with-a-long-random-secret \\
mcp-qdrant`

const byo = `QDRANT_MCP_BYO=1 \\
QDRANT_MCP_TRANSPORT=streamable-http \\
QDRANT_MCP_HTTP_HOST=0.0.0.0 \\
mcp-qdrant`

const docker = `docker run --rm -p 8000:8000 \\
  -e QDRANT_URL=http://host.docker.internal:6333 \\
  -e QDRANT_MCP_TRANSPORT=streamable-http \\
  -e QDRANT_MCP_HTTP_HOST=0.0.0.0 \\
  -e QDRANT_MCP_SHARED_SECRET=replace-with-a-long-random-secret \\
  ghcr.io/avaazquezz/qdrant-mcp:latest`
</script>

<template>
  <div class="space-y-8">
    <div class="grid gap-3 border-b border-ink pb-8 lg:grid-cols-12 lg:gap-8">
      <h3 class="text-h3 text-ink min-w-0 lg:col-span-4">Claude Desktop, no JSON</h3>
      <p class="max-w-prose text-body text-ink min-w-0 lg:col-span-8">
        Download
        <span class="font-mono">mcp-qdrant.mcpb</span>
        from the
        <a
          href="https://github.com/avaazquezz/Qdrant-MCP/releases"
          target="_blank"
          rel="noopener"
          class="underline decoration-1 underline-offset-4"
        >latest release<span class="sr-only"> (opens in a new tab)</span></a>
        and double-click it. Claude Desktop installs the server through
        <span class="font-mono">uv</span> and asks for the Qdrant URL, API key, local path,
        toolsets and read-only mode in its own settings form.
      </p>
    </div>

    <div class="grid gap-3 border-b border-ink pb-8 lg:grid-cols-12 lg:gap-8">
      <h3 class="text-h3 text-ink min-w-0 lg:col-span-4">No Qdrant yet</h3>
      <div class="min-w-0 lg:col-span-8">
        <UiCodePlate title="shell" :code="embedded" copy-label="Copy the embedded-Qdrant command" />
        <p class="mt-3 max-w-prose text-micro text-graphite">
          Runs Qdrant embedded, on disk, in the same process. No server, no Docker, nothing to
          install beyond <span class="font-mono">uv</span>.
          <span class="font-mono">QDRANT_URL</span> and <span class="font-mono">QDRANT_LOCAL_PATH</span>
          are mutually exclusive.
        </p>
      </div>
    </div>

    <div class="grid gap-3 border-b border-ink pb-8 lg:grid-cols-12 lg:gap-8">
      <h3 class="text-h3 text-ink min-w-0 lg:col-span-4">Remote, one fixed Qdrant</h3>
      <div class="min-w-0 lg:col-span-8">
        <UiCodePlate title="shell" :code="remote" copy-label="Copy the remote command" />
        <p class="mt-3 max-w-prose text-micro text-graphite">
          For claude.ai. The shared secret is required — the server refuses to start as
          <span class="font-mono">streamable-http</span> without one. In claude.ai:
          <strong class="font-semibold text-ink">Customize → Connectors → Add custom connector</strong>,
          authentication <strong class="font-semibold text-ink">None</strong>, then add a request
          header <span class="font-mono">Authorization</span> →
          <span class="font-mono">Bearer &lt;the same secret&gt;</span>.
        </p>
      </div>
    </div>

    <div class="grid gap-3 border-b border-ink pb-8 lg:grid-cols-12 lg:gap-8">
      <h3 class="text-h3 text-ink min-w-0 lg:col-span-4">Remote, bring your own Qdrant</h3>
      <div class="min-w-0 lg:col-span-8">
        <UiCodePlate title="shell" :code="byo" copy-label="Copy the bring-your-own command" />
        <p class="mt-3 max-w-prose text-micro text-graphite">
          No backing Qdrant of its own; each caller sends theirs. Two request headers:
          <span class="font-mono">Authorization</span> = your Qdrant URL, sent verbatim with no
          <span class="font-mono">Bearer</span> prefix, and <span class="font-mono">x-api-key</span> =
          its API key if it needs one. Your Qdrant must be reachable from the public internet — the
          SSRF guard rejects private, loopback and link-local addresses.
        </p>
      </div>
    </div>

    <div class="grid gap-3 lg:grid-cols-12 lg:gap-8">
      <h3 class="text-h3 text-ink min-w-0 lg:col-span-4">Docker</h3>
      <div class="min-w-0 lg:col-span-8">
        <UiCodePlate title="shell" :code="docker" copy-label="Copy the Docker command" />
        <p class="mt-3 max-w-prose text-micro text-graphite">
          The image only makes sense with <span class="font-mono">streamable-http</span>;
          <span class="font-mono">stdio</span> needs a client that owns the process's stdin and
          stdout. On Linux <span class="font-mono">host.docker.internal</span> does not resolve —
          add <span class="font-mono">--add-host=host.docker.internal:host-gateway</span> or use
          your host's LAN address.
        </p>
      </div>
    </div>
  </div>
</template>
