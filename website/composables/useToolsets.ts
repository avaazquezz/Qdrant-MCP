import { computed, reactive, ref, watch } from 'vue'
import tools from '~/data/tools.generated.json'
import type { ToolsetId } from '~/content/copy'

export interface Toolset {
  name: ToolsetId
  total: number
  readOnly: number
}

// Derived once from the generated registry dump, never hand-maintained: if the registry
// drifts, `scripts/gen_tools_json.py --check` fails CI before this ships a wrong count.
export const TOOLSET_ORDER: ToolsetId[] = [
  'core',
  'search',
  'payload',
  'snapshots',
  'admin',
  'observability',
]

export const TOOLSETS: Toolset[] = TOOLSET_ORDER.map((name) => {
  const inSet = tools.filter((t) => t.toolset === name)
  return { name, total: inSet.length, readOnly: inSet.filter((t) => t.read_only).length }
})

export const TOTAL_TOOLS = tools.length

/**
 * Which toolsets are enabled and whether read-only mode is on, plus everything derived
 * from that: the registered-tool count and the literal `.mcp.json` string. One source of
 * truth so the count and the config text can never disagree.
 */
export function useToolsets() {
  const enabled = reactive<Record<ToolsetId, boolean>>({
    core: true,
    search: false,
    payload: false,
    snapshots: false,
    admin: false,
    observability: false,
  })
  const readOnly = ref(false)

  // Checkboxes bind with v-model, not a bare :checked + @change: a plain :checked binding
  // on a native checkbox is a known Vue SSR/hydration trap (the server-rendered attribute is
  // right but the client's post-hydration `.checked` property ends up false). The
  // "at least one toolset" invariant lives here, not in a click handler, so it holds
  // however `enabled` changes.
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

  return { enabled, readOnly, enabledNames, registeredCount, configJson, forcedCoreNotice }
}
