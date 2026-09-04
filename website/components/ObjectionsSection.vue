<script setup lang="ts">
const ITEMS = [
  {
    q: 'Do I need a Qdrant already running?',
    a: 'No. Set QDRANT_LOCAL_PATH to a directory and the qdrant-client SDK runs Qdrant embedded, on disk, in the same process — no server, no Docker. QDRANT_URL and QDRANT_LOCAL_PATH are mutually exclusive; if you set neither, the SDK falls back to its own default of localhost:6333.',
  },
  {
    q: 'What breaks on a Qdrant older than 1.19?',
    a: 'Two payload tools, qdrant_collection_vector_create and qdrant_collection_vector_delete, hit an endpoint that returns 404 on older servers — verified against v1.13.6 and v1.15.1. Everything else works. v1.19.0 is the only version this project tests against.',
  },
  {
    q: 'Can I stop it writing to my production data?',
    a: 'QDRANT_MCP_READ_ONLY=1 removes every tool that is not marked read-only from the registry itself. 26 tools remain, 23 are gone, and a client calling tools/list never sees them. There is no permission check to get past, because there is no code path left.',
  },
  {
    q: 'Is 49 tools going to fill my context window?',
    a: 'The default is core: 13 tools. Toolsets are opt-in through QDRANT_MCP_TOOLSETS, and admin is a valid name that registers nothing. Build the surface you want in the panel above and copy the config it produces.',
  },
  {
    q: "Is this Qdrant's project?",
    a: "No. It is independent, MIT-licensed, and not affiliated with or endorsed by Qdrant. It wraps Qdrant's own qdrant-client SDK and reuses that SDK's Pydantic models for tool input, so the schemas track the SDK version instead of a hand-maintained copy.",
  },
  {
    q: 'Is it really the whole API?',
    a: 'Not quite, and the gap is deliberate: collection aliases and cluster/shard administration are not exposed. Real resharding only exists on Qdrant Cloud and the rest only matters for a distributed deployment. Everything under collections, points, search, payload, indexing, snapshots and observability is here — 49 tools.',
  },
]
</script>

<template>
  <section id="s-06" data-section="06" class="border-t-2 border-ink py-14 lg:py-24">
    <div class="section-rule border-t-2 border-ink" />
    <h2 class="mt-8 max-w-prose text-h2 text-ink">The things that would stop me installing this.</h2>

    <div class="mt-10 max-w-prose divide-y divide-ink border-y border-ink">
      <div v-for="item in ITEMS" :key="item.q" class="py-6">
        <h3 class="text-h3 text-ink">{{ item.q }}</h3>
        <p class="mt-2 text-body text-ink">{{ item.a }}</p>
      </div>
    </div>
  </section>
</template>
