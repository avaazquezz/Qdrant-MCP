import gsap from 'gsap'
import { CustomEase } from 'gsap/CustomEase'
import { Flip } from 'gsap/Flip'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SplitText } from 'gsap/SplitText'
import Lenis from 'lenis'

// Only the plugins the page actually uses: ScrollTrigger (pins, reveals, progress),
// Flip (the tool filter), SplitText (section titles by line), CustomEase (the brand ease).
export default defineNuxtPlugin((nuxtApp) => {
  gsap.registerPlugin(ScrollTrigger, Flip, SplitText, CustomEase)

  // The page's one ease: a dry start and a long settle, like a needle coming to rest.
  // Mirrors --ease-instrument in main.css so CSS and GSAP motion feel like one hand.
  CustomEase.create('instrument', '0.16,1,0.3,1')
  gsap.defaults({ ease: 'instrument', duration: 0.7 })
  ScrollTrigger.config({ ignoreMobileResize: true })

  nuxtApp.hook('app:mounted', () => {
    // Fonts change the height of every headline; triggers measured before they load fire
    // at the wrong scroll position.
    document.fonts.ready.then(() => ScrollTrigger.refresh())

    // Smooth scrolling is polish, not content: skipped entirely under reduced motion.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const lenis = new Lenis({ autoRaf: false, anchors: { offset: -80 } })
    lenis.on('scroll', ScrollTrigger.update)
    // One render loop for everything: GSAP's ticker drives Lenis, the canvas and the tweens.
    gsap.ticker.add((time) => lenis.raf(time * 1000))
    gsap.ticker.lagSmoothing(0)
    nuxtApp.provide('lenis', lenis)
  })
})
