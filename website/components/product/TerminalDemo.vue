<script setup lang="ts">
import gsap from 'gsap'

const root = ref<HTMLElement | null>(null)

const steps = [
  {
    call: 'qdrant_health_check()',
    result: '{ "ok": true }',
  },
  {
    call: 'qdrant_collection_create({"collection_name": "docs", "vector_size": 4, "distance": "Cosine"})',
    result: '{ "status": "ok" }',
  },
  {
    call: 'qdrant_points_upsert({"collection_name": "docs", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"title": "hello"}}]})',
    result: '{ "status": "ok" }',
  },
  {
    call: 'qdrant_query({"collection_name": "docs", "query_vector": [0.1, 0.2, 0.3, 0.4], "limit": 5})',
    result: '{ "results": [{ "id": 1, "score": 1.0, "payload": { "title": "hello" } }] }',
  },
]

useReveal(root, () => {
  if (!root.value) return
  const calls = root.value.querySelectorAll<HTMLElement>('.term-call')
  const results = root.value.querySelectorAll<HTMLElement>('.term-result')

  const tl = gsap.timeline({
    scrollTrigger: { trigger: root.value, start: 'top 75%', once: true },
  })

  steps.forEach((step, i) => {
    tl.to(calls[i], { opacity: 1, duration: 0.2 })
      .to(calls[i], { text: step.call, duration: Math.min(step.call.length * 0.012, 1.1), ease: 'none' })
      .to(results[i], { opacity: 1, y: 0, duration: 0.3 }, '+=0.1')
  })
})
</script>

<template>
  <div ref="root" class="border border-hairline bg-graphite p-5 font-mono text-sm">
    <div class="mb-3 flex items-center justify-between border-b border-hairline pb-3">
      <span class="text-[10px] uppercase tracking-[0.2em] text-dust/60">session.log</span>
      <span class="h-1.5 w-1.5 rounded-full bg-pulse" />
    </div>
    <div v-for="(step, i) in steps" :key="i" class="mb-3 last:mb-0">
      <p class="term-call whitespace-pre-wrap break-all text-signal opacity-0">&#8203;</p>
      <p class="term-result mt-1 translate-y-1 whitespace-pre-wrap break-all text-dust opacity-0">
        {{ step.result }}
      </p>
    </div>
  </div>
</template>
