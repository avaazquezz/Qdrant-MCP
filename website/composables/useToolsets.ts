import { computed, reactive, ref, watch } from 'vue'
import tools from '~/data/tools.generated.json'

export type ToolsetName = 'core' | 'search' | 'payload' | 'snapshots' | 'observability'

export interface Toolset {
  name: ToolsetName
  total: number
  readOnly: number
}

// Derived once from the generated registry dump, never hand-maintained —
// if the registry drifts, `scripts/gen_tools_json.py --check` fails CI
// before this ever ships a wrong count.
const TOOLSET_ORDER: ToolsetName[] = ['core', 'search', 'payload', 'snapshots', 'observability']

const TOOLSETS: Toolset[] = TOOLSET_ORDER.map((name) => {
  const inSet = tools.filter((t) => t.toolset === name)
  return { name, total: inSet.length, readOnly: inSet.filter((t) => t.read_only).length }
})

const TOTAL_TOOLS = tools.length

/**
 * Single source of truth for the §04 registry panel: which toolsets are
 * enabled, whether QDRANT_MCP_READ_ONLY is on, and every value derived from
 * that (the registered count, the per-toolset dot state, and the literal
 * .mcp.json string). Shared so the masthead/hero CTA and the panel's own
 * readout can never disagree about what "the config" currently is.
 */
export function useToolsets() {
  const enabled = reactive<Record<ToolsetName, boolean>>({
    core: true,
    search: false,
    payload: false,
    snapshots: false,
    observability: false,
  })
  const readOnly = ref(false)

  // Checkboxes here bind with v-model, not a bare :checked + @change — a
  // plain :checked binding on a native checkbox is a known Vue SSR/
  // hydration trap (the SSR-rendered `checked` attribute is correct, but
  // the client's post-hydration `.checked` DOM property silently ends up
  // false), which v-model's dedicated checkbox directive is hardened
  // against. The "at least one toolset" invariant is enforced here instead
  // of in a click handler, so it holds no matter how `enabled` changes.
  const forcedCoreNotice = ref(false)
  watch(
    enabled,
    () => {
      if (TOOLSET_ORDER.every((n) => !enabled[n])) {
        enabled.core = true
        forcedCoreNotice.value = true
      } else {
        forcedCoreNotice.value = false
      }
    },
    { flush: 'sync' }
  )

  const enabledNames = computed(() => TOOLSET_ORDER.filter((n) => enabled[n]))

  const registeredCount = computed(() =>
    TOOLSETS.reduce((sum, ts) => {
      if (!enabled[ts.name]) return sum
      return sum + (readOnly.value ? ts.readOnly : ts.total)
    }, 0)
  )

  const configJson = computed(() => {
    const env: Record<string, string> = {
      QDRANT_URL: 'http://localhost:6333',
      QDRANT_MCP_TOOLSETS: enabledNames.value.join(','),
    }
    if (readOnly.value) env.QDRANT_MCP_READ_ONLY = '1'
    return JSON.stringify(
      { mcpServers: { qdrant: { command: 'uvx', args: ['mcp-qdrant'], env } } },
      null,
      2
    )
  })

  return {
    TOOLSETS,
    TOTAL_TOOLS,
    enabled,
    readOnly,
    enabledNames,
    registeredCount,
    configJson,
    forcedCoreNotice,
  }
}

/** The fixed default `.mcp.json` — `core` only, no read-only flag. This is
 * "the config" the masthead and hero CTAs copy; it is deliberately not
 * wired to the §04 panel's live state, so it means the same thing no
 * matter how far a visitor has scrolled or what they have toggled. */
export function defaultConfigJson(): string {
  return JSON.stringify(
    {
      mcpServers: {
        qdrant: {
          command: 'uvx',
          args: ['mcp-qdrant'],
          env: { QDRANT_URL: 'http://localhost:6333', QDRANT_MCP_TOOLSETS: 'core' },
        },
      },
    },
    null,
    2
  )
}
