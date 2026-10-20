<script setup lang="ts">
import gsap from 'gsap'
import { ref } from 'vue'
import { useGsap } from '~/composables/useGsap'
import { AUTHOR, REPO_URL, useLanding } from '~/composables/useLanding'

const { copy } = useLanding()
const root = ref<HTMLElement | null>(null)

// Every call-to-action marked `data-magnetic` leans a little toward a fine pointer and
// springs back on leave. The same single action, in the masthead, the hero, the end of the
// log and here, so the one thing we want done is always within reach.
useGsap(root, ({ motion, finePointer }) => {
  if (!motion || !finePointer) return
  document.querySelectorAll<HTMLElement>('[data-magnetic]').forEach((button) => {
    const x = gsap.quickTo(button, 'x', { duration: 0.5, ease: 'elastic.out(1, 0.5)' })
    const y = gsap.quickTo(button, 'y', { duration: 0.5, ease: 'elastic.out(1, 0.5)' })
    const move = (e: PointerEvent) => {
      const box = button.getBoundingClientRect()
      x((e.clientX - (box.left + box.width / 2)) * 0.22)
      y((e.clientY - (box.top + box.height / 2)) * 0.3)
    }
    const leave = () => {
      x(0)
      y(0)
    }
    button.addEventListener('pointermove', move)
    button.addEventListener('pointerleave', leave)
  })
})
</script>

<template>
  <section id="contact" ref="root" class="on-panel bg-panel text-panel-ink" aria-labelledby="contact-title">
    <div class="mx-auto max-w-sheet px-4 py-20 sm:px-6 sm:py-28">
      <p class="font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">08 · {{ copy.contact.ordinal }}</p>
      <h2 id="contact-title" class="mt-4 max-w-4xl text-[clamp(2.4rem,7vw,6rem)] font-bold leading-[0.96] tracking-[-0.03em]">
        {{ copy.contact.title }}
      </h2>
      <p class="mt-6 max-w-prose text-deck text-panel-dim">{{ copy.contact.lead }}</p>

      <div class="mt-10 flex flex-wrap items-center gap-6">
        <a
          :href="REPO_URL"
          target="_blank"
          rel="noopener"
          data-magnetic
          class="inline-flex min-h-14 items-center gap-2 rounded-sm border border-panel-ink bg-panel-ink px-8 text-ui font-semibold text-panel transition-colors duration-200 hover:bg-transparent hover:text-panel-ink"
        >
          {{ copy.contact.cta }} <span aria-hidden="true">↗</span>
          <span class="sr-only">{{ copy.a11y.opensNewTab }}</span>
        </a>
      </div>

      <div class="mt-16 grid grid-cols-[minmax(0,1fr)] gap-6 border-t border-panel-line pt-8 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p class="font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">{{ copy.contact.author }}</p>
          <p class="mt-2 text-h3 font-bold">{{ AUTHOR.name }}</p>
        </div>
        <div>
          <p class="font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">{{ copy.contact.github }}</p>
          <a :href="AUTHOR.github" target="_blank" rel="noopener" class="mt-2 inline-block text-ui underline decoration-1 underline-offset-4 hover:text-white">github.com/avaazquezz</a>
        </div>
        <div>
          <p class="font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">{{ copy.contact.linkedin }}</p>
          <a :href="AUTHOR.linkedin" target="_blank" rel="noopener" class="mt-2 inline-block text-ui underline decoration-1 underline-offset-4 hover:text-white">linkedin.com/in/adrivaz</a>
        </div>
        <div>
          <p class="font-mono text-ordinal uppercase tracking-[0.14em] text-panel-dim">{{ copy.contact.email }}</p>
          <a :href="`mailto:${AUTHOR.email}`" class="mt-2 inline-block text-ui underline decoration-1 underline-offset-4 [overflow-wrap:anywhere] hover:text-white">{{ AUTHOR.email }}</a>
        </div>
      </div>
    </div>
  </section>
</template>
