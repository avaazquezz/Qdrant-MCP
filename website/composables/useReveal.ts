import gsap from 'gsap'
import { onBeforeUnmount, onMounted, type Ref } from 'vue'

/**
 * The one reduced-motion-aware GSAP entrance/reveal helper every animated
 * section uses. `animate` must build its tweens with gsap.from() (never
 * gsap.to()) — if `prefers-reduced-motion: no-preference` never matches,
 * the tween is simply never created and elements stay at their final CSS
 * state, satisfying reduced motion with no extra per-component branch.
 */
export function useReveal(scope: Ref<HTMLElement | null>, animate: () => void) {
  let ctx: gsap.Context | undefined

  onMounted(() => {
    ctx = gsap.context(() => {
      gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', animate)
    }, scope.value ?? undefined)
  })

  onBeforeUnmount(() => ctx?.revert())
}
