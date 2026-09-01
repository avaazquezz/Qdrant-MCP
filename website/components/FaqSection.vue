<script setup lang="ts">
const items = reactive([
  {
    q: 'How is this different from the official Qdrant MCP server?',
    a: "The official server (qdrant/mcp-server-qdrant) exposes two tools — store and find — and generates embeddings for you. This server covers the rest of Qdrant's surface: collections, points, every search mode, payload, indexing, snapshots, and observability. It never embeds anything.",
    open: true,
  },
  {
    q: 'Does it generate embeddings for me?',
    a: "No, on purpose. It's a thin wrapper around the Qdrant API, not a RAG system — whatever your client wants to store or query, it brings its own vectors.",
    open: false,
  },
  {
    q: 'Do I need my own Qdrant instance?',
    a: 'Yes, always. Even in bring-your-own-Qdrant (BYO) mode, every caller supplies their own instance per request — this server never stores data of its own.',
    open: false,
  },
  {
    q: 'Is it safe to expose remotely?',
    a: 'The personal streamable-http mode refuses to start without a shared secret. BYO mode re-resolves DNS on every request to reject private, loopback, and cloud-metadata addresses, defeating DNS rebinding.',
    open: false,
  },
  {
    q: 'Which clients does it work with?',
    a: 'Claude Desktop and Claude Code over stdio, or Claude.ai as a custom connector over streamable-http — any MCP client that speaks either transport.',
    open: false,
  },
  {
    q: 'Is it free?',
    a: 'Yes — MIT licensed, fully open source.',
    open: false,
  },
])

function toggle(i: number) {
  items[i].open = !items[i].open
}
</script>

<template>
  <section class="mx-auto max-w-3xl px-6 py-20">
    <h2 class="font-heading text-2xl font-semibold text-text-primary">FAQ</h2>
    <div class="mt-8 divide-y divide-border border-y border-border">
      <div v-for="(item, i) in items" :key="item.q" class="py-4">
        <button
          type="button"
          class="flex w-full items-center justify-between text-left font-heading text-base text-text-primary"
          @click="toggle(i)"
        >
          <span>{{ item.q }}</span>
          <span class="ml-4 text-text-secondary">{{ item.open ? '−' : '+' }}</span>
        </button>
        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          leave-active-class="transition-all duration-150 ease-in"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-40"
          leave-from-class="opacity-100 max-h-40"
          leave-to-class="opacity-0 max-h-0"
        >
          <p v-if="item.open" class="mt-2 overflow-hidden text-sm text-text-secondary">{{ item.a }}</p>
        </Transition>
      </div>
    </div>
  </section>
</template>
