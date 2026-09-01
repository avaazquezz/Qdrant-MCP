import type { Config } from 'tailwindcss'

export default <Partial<Config>>{
  theme: {
    extend: {
      colors: {
        bg: '#0A0A0F',
        surface: '#12131A',
        border: '#23242E',
        'text-primary': '#F2F2F5',
        'text-secondary': '#9497A6',
        accent: { DEFAULT: '#6D5EF5', hover: '#8477FF' },
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
}
