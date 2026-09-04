import { onMounted, ref } from 'vue'

export const SECTION_IDS = ['01', '02', '03', '04', '05', '06', '07'] as const
export type SectionId = (typeof SECTION_IDS)[number]

/**
 * The page's entire scroll vocabulary, in one hook: which section is
 * "current" (for the spine/masthead nav), and a one-time replay of each
 * section's top rule as it arrives. Content itself never fades or slides —
 * only a 2px rule and a spine swatch move. Every section this drives is
 * findable by `data-section="<id>"`.
 *
 * Contract: every element this touches is already at its correct, final
 * appearance in plain CSS with no JS running at all — this composable only
 * ever adds a temporary reset-then-transition replay on top of that state,
 * gated on `prefers-reduced-motion: no-preference`. A JS failure, a blocked
 * script, or reduced motion all leave the page identical to its resting
 * state; nothing is ever hidden in markup and revealed by script here.
 *
 * Module-level singleton: both SiteMasthead and SiteSpine call this to read
 * the same activeId, but the actual observers are set up once — a second
 * caller just gets the shared ref, not a second pair of observers.
 */
const activeId = ref<SectionId>('01')
let started = false

function start() {
  if (started) return
  started = true

  const sections = Array.from(document.querySelectorAll<HTMLElement>('[data-section]'))
  const reduced = !window.matchMedia('(prefers-reduced-motion: no-preference)').matches

  const arrivalObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        if (!reduced) {
          const rule = entry.target.querySelector<HTMLElement>('.section-rule')
          if (rule) {
            rule.style.transition = 'none'
            rule.style.transform = 'scaleX(0)'
            // Force a reflow so the reset above is committed before the
            // transition below is allowed to animate from it.
            void rule.offsetWidth
            rule.style.transition = 'transform 380ms cubic-bezier(0.22,1,0.36,1)'
            rule.style.transform = 'scaleX(1)'
          }
        }
        arrivalObserver.unobserve(entry.target)
      })
    },
    { threshold: 0, rootMargin: '0px 0px -15% 0px' }
  )

  const activeObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeId.value = entry.target.getAttribute('data-section') as SectionId
        }
      })
    },
    { threshold: 0, rootMargin: '-50% 0px -50% 0px' }
  )

  sections.forEach((el) => {
    arrivalObserver.observe(el)
    activeObserver.observe(el)
  })
}

export function useSectionRules() {
  onMounted(start)
  return { activeId }
}
