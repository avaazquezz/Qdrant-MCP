<script setup lang="ts">
defineProps<{ active: 'mine' | 'official' }>()
</script>

<template>
  <div class="relative">
    <!-- Both diagrams exist in the SSR'd DOM at all times; only `hidden`
         toggles. Every id is suffixed per state so two <svg> in one
         document never collide. -->
    <svg
      :hidden="active !== 'mine'"
      viewBox="0 0 460 340"
      class="h-auto w-full max-w-md"
      role="img"
      aria-hidden="true"
    >
      <defs>
        <marker id="arrow-mine" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#15171C" />
        </marker>
      </defs>
      <rect x="20" y="10" width="240" height="56" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="34" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">Claude Desktop / Code /</text>
      <text x="30" y="52" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">claude.ai</text>

      <path
        class="anim-draw-wire"
        d="M140,66 L140,116"
        stroke="#15171C"
        stroke-width="1.5"
        marker-end="url(#arrow-mine)"
        fill="none"
      />
      <text x="152" y="98" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">vector + payload</text>
      <text x="152" y="114" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">your vector, from whatever</text>
      <text x="152" y="130" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">model you already use.</text>
      <text x="152" y="146" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">Passed through, never read.</text>

      <rect x="20" y="120" width="240" height="80" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="144" font-family="'IBM Plex Mono', monospace" font-size="13" fill="#15171C">mcp-qdrant</text>
      <text x="30" y="164" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">validate (Pydantic)</text>
      <text x="30" y="182" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">qdrant-client SDK</text>

      <path
        class="anim-draw-wire"
        d="M140,200 L140,250"
        stroke="#15171C"
        stroke-width="1.5"
        marker-end="url(#arrow-mine)"
        fill="none"
        style="animation-delay: 80ms"
      />
      <text x="152" y="230" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">HTTP</text>

      <rect x="20" y="254" width="240" height="56" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="286" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">your Qdrant v1.19+</text>
    </svg>
    <p v-if="active === 'mine'" class="sr-only">
      Diagram: Claude Desktop, Code or claude.ai sends a vector and payload — your vector, from
      whatever model you already use, passed through and never read — to mcp-qdrant, which
      validates it with Pydantic and calls the qdrant-client SDK. The SDK talks HTTP to your own
      Qdrant, v1.19 or newer.
    </p>

    <svg
      :hidden="active !== 'official'"
      viewBox="0 0 460 340"
      class="h-auto w-full max-w-md"
      role="img"
      aria-hidden="true"
    >
      <defs>
        <marker id="arrow-official" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#15171C" />
        </marker>
      </defs>
      <rect x="20" y="10" width="240" height="56" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="34" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">Claude Desktop / Code /</text>
      <text x="30" y="52" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">claude.ai</text>

      <path
        class="anim-draw-wire"
        d="M140,66 L140,116"
        stroke="#15171C"
        stroke-width="1.5"
        marker-end="url(#arrow-official)"
        fill="none"
      />
      <text x="152" y="94" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">text</text>

      <rect x="20" y="120" width="240" height="106" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="140" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">mcp-server-qdrant</text>
      <rect class="anim-stamp" x="28" y="150" width="150" height="26" fill="#C2172F" style="animation-delay: 320ms" />
      <text x="36" y="167" font-family="'IBM Plex Mono', monospace" font-size="11" fill="#F2EFE7">embed (fastembed)</text>
      <text x="30" y="200" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">qdrant-client SDK</text>
      <text x="270" y="160" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">the server picks the</text>
      <text x="270" y="176" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">embedding model. Two</text>
      <text x="270" y="192" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">tools: qdrant-store,</text>
      <text x="270" y="208" font-family="Archivo, sans-serif" font-size="12" fill="#C2172F">qdrant-find.</text>

      <path
        class="anim-draw-wire"
        d="M140,226 L140,250"
        stroke="#15171C"
        stroke-width="1.5"
        marker-end="url(#arrow-official)"
        fill="none"
        style="animation-delay: 80ms"
      />
      <text x="152" y="246" font-family="Archivo, sans-serif" font-size="12" fill="#5C6070">HTTP</text>

      <rect x="20" y="254" width="240" height="56" fill="#E7E2D6" stroke="#15171C" />
      <text x="30" y="286" font-family="Archivo, sans-serif" font-size="14" fill="#15171C">your Qdrant</text>
    </svg>
    <p v-if="active === 'official'" class="sr-only">
      Diagram: Claude Desktop, Code or claude.ai sends text to mcp-server-qdrant, which embeds it
      itself using fastembed — the server picks the embedding model, and exposes exactly two
      tools, qdrant-store and qdrant-find — then calls the qdrant-client SDK, which talks HTTP to
      your Qdrant.
    </p>
  </div>
</template>

<style scoped>
@media (prefers-reduced-motion: no-preference) {
  .anim-draw-wire {
    stroke-dasharray: 60;
    stroke-dashoffset: 60;
    animation: draw-wire 300ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }
  @keyframes draw-wire {
    to {
      stroke-dashoffset: 0;
    }
  }
}
</style>
