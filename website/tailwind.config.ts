import type { Config } from 'tailwindcss'

export default <Partial<Config>>{
  theme: {
    extend: {
      colors: {
        // Two-plate datasheet: paper/ink is the whole page, spot is the
        // only accent and it has exactly one meaning (see main.css comment
        // above ::selection) — this writes to your data, or this is a live
        // value. tint/mist are texture, never a second accent.
        paper: '#F2EFE7',
        ink: '#15171C',
        graphite: '#5C6070',
        spot: '#C2172F',
        tint: '#E7E2D6',
        mist: '#A2A6B4',
      },
      fontFamily: {
        sans: ['Archivo', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      // Named roles, not t-shirt sizes: every text on the page picks one of
      // these by what it IS (a heading, a readout, a tool identifier), not
      // by eyeballing a scale. clamp() rows fluid between the mobile and
      // desktop figure named alongside them.
      fontSize: {
        display: ['clamp(2.125rem,4.4vw,3.8125rem)', { lineHeight: '0.98', letterSpacing: '-0.025em', fontWeight: '700' }], // 34 -> 61
        h2: ['clamp(1.625rem,2.9vw,2.4375rem)', { lineHeight: '1.05', letterSpacing: '-0.02em', fontWeight: '700' }], // 26 -> 39
        readout: ['clamp(1.625rem,2.4vw,1.9375rem)', { lineHeight: '1.15', letterSpacing: '-0.01em', fontWeight: '700' }], // 26 -> 31
        h3: ['clamp(1.3125rem,1.8vw,1.5625rem)', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '700' }], // 21 -> 25
        deck: ['clamp(1.25rem,1.6vw,1.5625rem)', { lineHeight: '1.45', letterSpacing: '-0.005em', fontWeight: '400' }], // 20 -> 25
        body: ['clamp(1.125rem,1vw,1.25rem)', { lineHeight: '1.6', letterSpacing: '0', fontWeight: '400' }], // 18 -> 20
        ui: ['1rem', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '400' }], // 16
        micro: ['0.8125rem', { lineHeight: '1.45', letterSpacing: '0', fontWeight: '400' }], // 13
        ordinal: ['0.6875rem', { lineHeight: '1', letterSpacing: '0.04em', fontWeight: '600' }], // 11
      },
      maxWidth: {
        sheet: '1360px',
        prose: '62ch',
        code: '78ch',
      },
    },
  },
}
