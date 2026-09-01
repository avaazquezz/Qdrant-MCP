import type { Config } from 'tailwindcss'

export default <Partial<Config>>{
  theme: {
    extend: {
      colors: {
        ink: '#08090D',
        graphite: '#14151C',
        hairline: '#26272F',
        paper: '#ECECEF',
        dust: '#85889A',
        signal: { DEFAULT: '#7C6CFF', hover: '#9284FF' },
        pulse: '#34E2C4',
      },
      fontFamily: {
        display: ['Fraunces', 'serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
}
