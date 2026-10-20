<script setup lang="ts">
import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { ref } from 'vue'
import { useGsap } from '~/composables/useGsap'

defineProps<{
  id: string
  /** Position and name, e.g. "02 · Architecture". The number is the section's real order. */
  ordinal: string
  title: string
  lead?: string
}>()

const root = ref<HTMLElement | null>(null)

// Section titles rise out of a mask line by line, once. (Not a fade-up: each line travels
// from below its own clipping box, so the title reads as being set, not as appearing.)
// Without motion the title is just there; the text is real DOM text either way.
useGsap(root, ({ motion }) => {
  if (!motion) return
  const title = root.value?.querySelector<HTMLElement>('[data-title]')
  if (!title) return
  SplitText.create(title, {
    type: 'lines',
    mask: 'lines',
    autoSplit: true,
    onSplit: (self) =>
      gsap.from(self.lines, {
        yPercent: 110,
        stagger: 0.09,
        duration: 0.9,
        scrollTrigger: { trigger: title, start: 'top 88%', once: true },
      }),
  })
})
</script>

<template>
  <header ref="root" class="max-w-4xl">
    <p class="ordinal">{{ ordinal }}</p>
    <h2
      :id="`${id}-title`"
      data-title
      class="mt-4 text-[clamp(1.9rem,4.4vw,3.6rem)] font-bold leading-[1.02] tracking-[-0.025em]"
    >
      {{ title }}
    </h2>
    <p v-if="lead" class="mt-5 max-w-prose text-deck text-graphite">{{ lead }}</p>
  </header>
</template>
