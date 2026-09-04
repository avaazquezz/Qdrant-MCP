<script setup lang="ts">
import { ref } from 'vue'

const active = ref<'mine' | 'official'>('mine')
</script>

<template>
  <section id="s-02" data-section="02" class="border-t-2 border-ink py-14 lg:py-24">
    <div class="section-rule border-t-2 border-ink" />
    <h2 class="mt-8 max-w-prose text-h2 text-ink">Two servers, same database. The difference is one box.</h2>
    <p class="mt-4 max-w-prose text-deck text-graphite">
      Both talk to the same Qdrant over the same HTTP API. Where they differ is what happens
      between your client and the SDK call.
    </p>

    <div role="radiogroup" aria-label="Which server to diagram" class="mt-8 inline-flex border border-ink">
      <label
        class="flex h-10 cursor-pointer items-center px-4 text-ui transition-colors"
        :class="active === 'mine' ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-tint'"
      >
        <input type="radio" name="wiring" value="mine" v-model="active" class="sr-only" />
        mcp-qdrant
      </label>
      <label
        class="flex h-10 cursor-pointer items-center border-l border-ink px-4 text-ui transition-colors"
        :class="active === 'official' ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-tint'"
      >
        <input type="radio" name="wiring" value="official" v-model="active" class="sr-only" />
        qdrant/mcp-server-qdrant
      </label>
    </div>

    <div class="mt-8">
      <WiringDiagram :active="active" />
    </div>

    <div class="mt-10 max-w-prose border-t border-ink pt-8">
      <h3 class="text-h3 text-ink">If store and find are all you need, use theirs.</h3>
      <p class="mt-3 text-body text-ink">
        The official server embeds your documents for you, which means it works with no embedding
        pipeline of your own, and two tool descriptions cost almost nothing in a context window. It
        is maintained by Qdrant. Everything on this page assumes the opposite trade: that you
        already have an embedding step you control, and you want the rest of Qdrant's API next to
        it.
      </p>
      <p class="mt-3 text-micro text-graphite">
        Two tools counted against
        <a
          href="https://github.com/qdrant/mcp-server-qdrant"
          target="_blank"
          rel="noopener"
          class="font-mono underline decoration-1 underline-offset-4"
        >qdrant/mcp-server-qdrant<span class="sr-only"> (opens in a new tab)</span></a>
        on 4 September 2026.
      </p>
    </div>

    <div class="mt-10 overflow-x-auto">
      <table class="w-full min-w-[560px] border-collapse text-ui">
        <caption class="sr-only">Feature comparison between qdrant/mcp-server-qdrant and mcp-qdrant</caption>
        <thead>
          <tr class="border-b border-ink">
            <th scope="col" class="py-2 pr-4 text-left font-normal text-graphite"></th>
            <th scope="col" class="py-2 pr-4 text-left font-mono font-normal text-ink">qdrant/mcp-server-qdrant</th>
            <th scope="col" class="py-2 text-left font-mono font-normal text-ink">mcp-qdrant</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in [
            ['tools registered', '2', '49, of which 13 by default'],
            ['generates embeddings', 'yes, with fastembed', 'no'],
            ['collection management', 'no', '6 tools'],
            ['search beyond plain kNN', 'no', '9 tools'],
            ['payload and index editing', 'no', '12 tools'],
            ['snapshots and restore', 'no', '9 tools'],
            ['server observability', 'no', '6 tools'],
            ['maintained by', 'Qdrant', 'independent, MIT'],
          ]" :key="row[0]" class="border-b border-ink" :class="i % 2 === 1 ? 'bg-tint' : ''">
            <th scope="row" class="py-2 pr-4 text-left font-normal text-graphite">{{ row[0] }}</th>
            <td class="py-2 pr-4 text-ink">{{ row[1] }}</td>
            <td class="py-2 text-ink">{{ row[2] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
