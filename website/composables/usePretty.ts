/**
 * A compact, human-readable rendering of a JSON value for the demo console. Differences
 * from `JSON.stringify(v, null, 2)`, all to keep a real call readable on one screen:
 *  - arrays of scalars stay on one line (`[0.9, 0.1, 0.1, 0]`, not one number per line);
 *  - a long array of objects shows its first `maxItems` and then a marker, `… +N more`.
 * The marker is explicit and is the only place anything is left out; it makes the output
 * not valid JSON, which is why it is displayed, never parsed.
 */
export function pretty(value: unknown, maxItems = 2, depth = 0): string {
  const pad = '  '.repeat(depth)
  const inner = '  '.repeat(depth + 1)

  if (Array.isArray(value)) {
    if (value.length === 0) return '[]'
    if (value.every((item) => item === null || typeof item !== 'object')) {
      const shown = value.slice(0, 14).map((item) => JSON.stringify(item))
      return `[${shown.join(', ')}${value.length > 14 ? ', …' : ''}]`
    }
    const shown = value.slice(0, maxItems).map((item) => `${inner}${pretty(item, maxItems, depth + 1)}`)
    const more = value.length - shown.length
    if (more > 0) shown.push(`${inner}… +${more} more`)
    return `[\n${shown.join(',\n')}\n${pad}]`
  }

  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return '{}'
    const lines = entries.map(([key, item]) => `${inner}${JSON.stringify(key)}: ${pretty(item, maxItems, depth + 1)}`)
    return `{\n${lines.join(',\n')}\n${pad}}`
  }

  return JSON.stringify(value)
}
