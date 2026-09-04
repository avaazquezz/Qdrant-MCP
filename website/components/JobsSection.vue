<script setup lang="ts">
const ROWS = [
  {
    outcome: 'Run hybrid search without writing the fusion yourself.',
    tools: ['qdrant_query', 'qdrant_query_groups', 'qdrant_query_batch'],
    mechanism: 'One call carries several prefetch stages and the RRF or DBSF fusion step. Grouped queries return the best hits per source document instead of per chunk.',
  },
  {
    outcome: 'Search by example, or steer between examples.',
    tools: ['qdrant_recommend', 'qdrant_discover', 'qdrant_distance_matrix_pairs'],
    mechanism: 'Positive and negative examples instead of a query vector, and a pairwise distance matrix over a sample when you want the shape of the space rather than a ranking.',
  },
  {
    outcome: 'Fix the data in place instead of re-ingesting it.',
    tools: ['qdrant_payload_set', 'qdrant_payload_index_create', 'qdrant_payload_facet', 'qdrant_vectors_update', 'qdrant_points_batch_update'],
    mechanism: 'Add an index to a live collection, count facets over a field, replace vectors by id, or run a batch of point operations atomically in the order given.',
  },
  {
    outcome: 'Back up before a migration and restore after it goes wrong.',
    tools: ['qdrant_snapshot_create', 'qdrant_snapshot_recover', 'qdrant_storage_snapshot_create'],
    mechanism: 'Per collection or whole storage. The two download tools confirm a snapshot exists and return the URL to fetch it from; they do not transfer the file.',
  },
]
</script>

<template>
  <section id="s-03" data-section="03" class="border-t-2 border-ink py-14 lg:py-16">
    <div class="section-rule border-t-2 border-ink" />
    <h2 class="mt-8 max-w-prose text-h2 text-ink">What the other 36 are for.</h2>
    <p class="mt-4 max-w-prose text-deck text-graphite">
      <span class="font-mono">core</span> is 13 tools and it is a complete MCP server on its own.
      These are the reasons to turn the rest on.
    </p>

    <div class="mt-10 divide-y divide-ink border-y border-ink">
      <div v-for="row in ROWS" :key="row.outcome" class="grid gap-3 py-6 lg:grid-cols-12 lg:gap-8">
        <h3 class="text-h3 text-ink min-w-0 lg:col-span-5">{{ row.outcome }}</h3>
        <div class="min-w-0 lg:col-span-7">
          <p class="font-mono text-micro leading-relaxed text-ink [overflow-wrap:anywhere]">
            <span v-for="(t, i) in row.tools" :key="t">{{ t }}<template v-if="i < row.tools.length - 1">, </template></span>
          </p>
          <p class="mt-2 text-micro text-graphite">{{ row.mechanism }}</p>
        </div>
      </div>
    </div>

    <p class="mt-8 max-w-prose text-body text-ink">
      <strong class="font-semibold">Errors come back as Qdrant's errors.</strong> Every call goes
      through retry-with-backoff and returns Qdrant's own message. Your model reads
      <span class="font-mono">collection not found</span>, not
      <span class="font-mono">Error executing tool</span>.
    </p>
  </section>
</template>
