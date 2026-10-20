/** One recorded step of a demo scenario (website/data/scenarios.generated.json): either a
 * tool call or an MCP method (`tools/list`), with what the real server answered. */
export interface Step {
  tool?: string
  method?: string
  arguments?: Record<string, unknown>
  environment?: Record<string, string>
  ok: boolean
  result?: unknown
  error?: string
}
