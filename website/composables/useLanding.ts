import { inject, provide, type InjectionKey } from 'vue'
import { COPY, type Copy, type Lang } from '~/content/copy'
import stats from '~/data/stats.generated.json'
import scenarios from '~/data/scenarios.generated.json'

export const REPO_URL = 'https://github.com/avaazquezz/Qdrant-MCP'
export const AUTHOR = {
  name: 'Adrián Vázquez',
  github: 'https://github.com/avaazquezz',
  linkedin: 'https://www.linkedin.com/in/adrivaz/',
  email: 'adrian@vazquezdev.pro',
}

/** `{name}` placeholders → values. An unknown placeholder is left visible on purpose:
 * a missing figure should look broken in review, not silently render as "undefined". */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) => String(vars[key] ?? whole))
}

export interface Landing {
  lang: Lang
  copy: Copy
  /** Fill `{placeholders}` from the generated stats (plus any extra values). */
  t: (template: string, extra?: Record<string, string | number>) => string
  stats: typeof stats
  recordedWith: { mcp_qdrant: string; qdrant: string }
  /** The other language's path, for the switcher. */
  alternate: { lang: Lang; href: string; label: string }
}

const KEY: InjectionKey<Landing> = Symbol('landing')

export function provideLanding(lang: Lang): Landing {
  const numbers = new Intl.NumberFormat(lang)
  const vars: Record<string, string | number> = {
    tools: stats.tools,
    readOnly: stats.read_only_tools,
    tests: numbers.format(stats.tests),
    version: stats.version,
    src: numbers.format(stats.source_lines),
    testLines: numbers.format(stats.test_lines),
    coreKb: stats.core_schema_kb,
    catalogKb: stats.catalog_schema_kb,
    sets: Object.keys(stats.toolsets).length,
    core: stats.toolsets.core,
    qdrant: scenarios.recorded_with.qdrant,
    mcp: scenarios.recorded_with.mcp_qdrant,
  }
  const landing: Landing = {
    lang,
    copy: COPY[lang],
    t: (template, extra = {}) => fmt(template, { ...vars, ...extra }),
    stats,
    recordedWith: scenarios.recorded_with,
    alternate:
      lang === 'en'
        ? { lang: 'es', href: '/es/', label: 'ES' }
        : { lang: 'en', href: '/', label: 'EN' },
  }
  provide(KEY, landing)
  return landing
}

export function useLanding(): Landing {
  const landing = inject(KEY)
  if (!landing) throw new Error('useLanding() called outside <LandingPage>')
  return landing
}
