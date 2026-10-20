import gsap from 'gsap'
import { onMounted, onUnmounted, type Ref } from 'vue'

export interface MotionConditions {
  /** The visitor has not asked for reduced motion: the full choreography. */
  motion: boolean
  /** The visitor has asked for reduced motion: crossfades and state changes only. */
  reduce: boolean
  /** Wide enough for the pinned, side-by-side layouts. Below it everything stacks. */
  desktop: boolean
  /** A mouse or trackpad: cursor-following effects only make sense here. */
  finePointer: boolean
}

/**
 * Scoped GSAP setup with automatic cleanup. `gsap.matchMedia()` acts as a
 * `gsap.context()` too: every tween, ScrollTrigger and SplitText created inside `setup`
 * is reverted on unmount or when a media condition flips, so nothing leaks into the next
 * visit to the page.
 *
 * Contract for `setup`: the `reduce` branch must leave the page fully usable (content
 * visible, state changes still work) — never rely on an animation to reveal text.
 */
export function useGsap(scope: Ref<HTMLElement | null>, setup: (c: MotionConditions) => void) {
  let mm: gsap.MatchMedia | undefined
  onMounted(() => {
    mm = gsap.matchMedia()
    mm.add(
      {
        motion: '(prefers-reduced-motion: no-preference)',
        reduce: '(prefers-reduced-motion: reduce)',
        desktop: '(min-width: 1024px)',
        finePointer: '(hover: hover) and (pointer: fine)',
      },
      (ctx) => setup(ctx.conditions as unknown as MotionConditions),
      scope.value ?? undefined
    )
  })
  onUnmounted(() => mm?.revert())
}
