// All visible text, in both languages, in one typed place. `es` must satisfy the same
// `Copy` shape as `en`, so a missing or extra key is a type error rather than a half-
// translated page.
//
// Placeholders in {braces} are filled at render time from the generated stats
// (website/data/stats.generated.json) — figures are never typed in here.
//
// Voice: impersonal on purpose ("what went wrong", not "what I got wrong"). The log
// records what the repository records; the first person is reserved for nothing.

export type Lang = 'en' | 'es'
export type ScenarioId =
  | 'text-search'
  | 'search-advisor'
  | 'hybrid-search'
  | 'zero-downtime-reindex'
  | 'know-the-payload'
  | 'safety-rails'
export type ToolsetId = 'core' | 'search' | 'payload' | 'snapshots' | 'admin' | 'observability'

export interface Copy {
  htmlLang: string
  meta: { title: string; description: string; ogAlt: string }
  a11y: {
    skip: string
    pauseAnimation: string
    playAnimation: string
    langSwitch: string
    opensNewTab: string
    sections: string
  }
  nav: {
    method: string
    architecture: string
    scenarios: string
    tools: string
    log: string
    quality: string
    github: string
  }
  hero: {
    kicker: string
    title: string
    deck: string
    ctaPrimary: string
    ctaSecondary: string
    canvasLabel: string
    canvasCaption: string
    nearest: string
  }
  proof: {
    tools: string
    toolsSub: string
    tests: string
    testsSub: string
    changelog: string
    changelogSub: string
    code: string
    codeSub: string
    schema: string
    schemaSub: string
    note: string
  }
  method: {
    ordinal: string
    title: string
    lead: string
    steps: { name: string; body: string; example: string }[]
    cta: string
  }
  architecture: {
    ordinal: string
    title: string
    lead: string
    caption: string
    nodes: {
      name: string
      tag: string
      why: string
      source: string
      payloadTitle: string
      /** Text shown in the payload panel; empty when the hop shows recorded JSON instead. */
      payloadLines: string[]
    }[]
  }
  scenarios: {
    ordinal: string
    title: string
    lead: string
    play: string
    pause: string
    replay: string
    step: string
    arguments: string
    result: string
    refused: string
    recorded: string
    tabs: Record<ScenarioId, { tab: string; title: string; intro: string; steps: string[] }>
  }
  tools: {
    ordinal: string
    title: string
    lead: string
    searchLabel: string
    searchPlaceholder: string
    all: string
    readOnlyOnly: string
    showing: string
    noResults: string
    details: string
    hide: string
    badges: { readOnly: string; destructive: string; idempotent: string }
    onByDefault: string
    toolsets: Record<ToolsetId, string>
  }
  install: {
    title: string
    lead: string
    toolsets: string
    readOnly: string
    registered: string
    forcedCore: string
    copyConfig: string
    copied: string
    copyFailed: string
    announceCopied: string
    announceFailed: string
    paths: { uvx: string; mcpb: string; docker: string; dockerNote: string }
  }
  log: {
    ordinal: string
    title: string
    lead: string
    labels: {
      claim: string
      probe: string
      result: string
      fix: string
      fixedIn: string
      pinnedBy: string
      review: string
    }
    cta: string
  }
  quality: {
    ordinal: string
    title: string
    lead: string
    pipeline: string[]
    cards: { title: string; body: string }[]
  }
  faq: { ordinal: string; title: string; items: { q: string; a: string }[] }
  contact: {
    ordinal: string
    title: string
    lead: string
    cta: string
    author: string
    github: string
    linkedin: string
    email: string
  }
  footer: { license: string; independent: string; version: string; builtWith: string }
}

const en: Copy = {
  htmlLang: 'en',
  meta: {
    title: 'Qdrant MCP — {tools} MCP tools, every claim tested against a real server',
    description:
      "A Model Context Protocol server that exposes Qdrant's API as {tools} tools: a portfolio project by Adrián Vázquez, with the public engineering log of what went wrong and how it was found. Python, {tests} tests, CI against a real Qdrant.",
    ogAlt: "Qdrant's whole API as MCP tools. Every claim tested against a real server.",
  },
  a11y: {
    skip: 'Skip to the content',
    pauseAnimation: 'Pause animation',
    playAnimation: 'Play animation',
    langSwitch: 'Language',
    opensNewTab: '(opens in a new tab)',
    sections: 'Sections',
  },
  nav: {
    method: 'Method',
    architecture: 'Architecture',
    scenarios: 'In action',
    tools: 'Tools',
    log: 'Log',
    quality: 'Quality',
    github: 'GitHub',
  },
  hero: {
    kicker: 'Portfolio project · Adrián Vázquez',
    title: "Qdrant's whole API as {tools} MCP tools. Every claim tested against a real server.",
    deck: 'A Model Context Protocol server in Python that lets an LLM manage a Qdrant vector database, search it in plain text, and diagnose and tune it. Its engineering log is public: what went wrong, how it was found, and the test that now stands guard.',
    ctaPrimary: 'Open the repository',
    ctaSecondary: 'Read the engineering log',
    canvasLabel:
      'Illustrative three-dimensional vector space. Move the pointer over it to probe: the five nearest points light up, with their distances computed in your browser.',
    canvasCaption: 'illustrative projection · distances computed live',
    nearest: 'nearest',
  },
  proof: {
    tools: 'MCP tools',
    toolsSub: '{readOnly} of them read-only',
    tests: 'tests',
    testsSub: 'unit and integration, as pytest collects them',
    changelog: 'changelog entries',
    changelogSub: 'latest: v{version}',
    code: 'lines of Python',
    codeSub: '{src} of source, {testLines} of tests',
    schema: 'KB of tool schemas',
    schemaSub: 'default toolset, loaded into the model’s context',
    note: 'Every figure here that looks like a measurement is generated from the repository by a script that CI re-runs. Hover one to see which.',
  },
  method: {
    ordinal: 'The method',
    title: 'Nothing is written down until it has been run.',
    lead: "Qdrant's behavior is easy to assume and expensive to get wrong. Every claim in this project's tool descriptions goes through the same three steps.",
    steps: [
      {
        name: 'Probe',
        body: 'Run the scenario against a real Qdrant server, the failure path first. Read the state afterwards, not just the response.',
        example:
          'A valid alias operation followed by a failing one, then list the aliases. On Qdrant 1.19 the first was still applied, so the tool did not say "atomic".',
      },
      {
        name: 'Pin',
        body: 'Turn what was observed into an integration test, so a future Qdrant release that changes it fails CI instead of silently making the documentation stale.',
        example:
          'test_alias_batch_is_all_or_nothing — it failed in CI the day Qdrant 1.20 made those batches all-or-nothing, and the description changed with it.',
      },
      {
        name: 'Review',
        body: 'An independent reader with no knowledge of the reasoning is told to reproduce, not speculate. Every finding is reproduced a second time before anyone acts on it.',
        example: 'One such review found that an empty filter deleted a whole collection. It is in the log.',
      },
    ],
    cta: 'Read the whole log',
  },
  architecture: {
    ordinal: 'Architecture',
    title: 'How a tool call travels.',
    lead: 'Five hops between a model and the database. Each one is a decision, not a default.',
    caption: 'scroll to follow a call',
    nodes: [
      {
        name: 'MCP client',
        tag: 'Claude, Cursor, any MCP client',
        why: 'It receives {tools} tool definitions. The advertised schemas are compact — {coreKb} KB for the default toolset instead of about 150 KB — because they are loaded into the model’s context on every conversation.',
        source: 'tests/unit/test_schemas.py',
        payloadTitle: 'tools/call, as the client sends it',
        payloadLines: [],
      },
      {
        name: 'Transport',
        tag: 'stdio · streamable-http',
        why: 'stdio by default. The remote transport refuses to start without a shared secret, and there is no hosted instance: this is a project you run, not a service.',
        source: 'src/mcp_qdrant/cli.py',
        payloadTitle: 'On the wire',
        payloadLines: [
          'stdio: one JSON-RPC message per line, on stdin and stdout',
          'streamable-http: POST /mcp',
          '  Authorization: Bearer <shared secret>   (required to start)',
        ],
      },
      {
        name: 'ToolRegistry',
        tag: 'toolsets · read-only · result cap',
        why: 'One choke point. It filters toolsets, removes every mutating tool in read-only mode ({readOnly} of {tools} survive) and caps results per call. A tool cannot bypass it by registering itself differently.',
        source: 'src/mcp_qdrant/tools/registry.py',
        payloadTitle: 'What the registry checks',
        payloadLines: [
          '✓ toolset core is enabled',
          '✓ read-only mode is off (qdrant_query is read-only, so it would pass anyway)',
          '✓ limit {limit} ≤ cap {cap} (QDRANT_MCP_MAX_LIMIT)',
          '✓ the arguments validate against the tool’s Pydantic model',
        ],
      },
      {
        name: 'call_qdrant',
        tag: 'retry · translated errors',
        why: 'Only a request that never reached Qdrant is retried: after a timeout, a write may already have happened, so the model is told to check instead of the call being repeated. A Qdrant error reaches the model as Qdrant’s own message, never as a generic "Error executing tool".',
        source: 'src/mcp_qdrant/tools/errors.py',
        payloadTitle: 'What goes to Qdrant',
        payloadLines: [
          'POST /collections/{collection}/points/query',
          '',
          'connection refused → retried with backoff',
          'timeout after send → "may have been applied", not retried',
          'Qdrant error       → ToolError(Qdrant’s own message)',
        ],
      },
      {
        name: 'Qdrant',
        tag: 'qdrant-client over REST',
        why: 'The official SDK, so tool inputs reuse its models and track its version. The client brings vectors — or plain text, embedded locally with the model the collection declares in its own metadata.',
        source: 'ROADMAP.md · principle 1',
        payloadTitle: 'Qdrant’s answer, summarized',
        payloadLines: [],
      },
    ],
  },
  scenarios: {
    ordinal: 'In action',
    title: 'Six things a model can do with it.',
    lead: 'These are not mock-ups. Every call below was executed through the MCP server against a real Qdrant, and the response is what came back.',
    play: 'Play',
    pause: 'Pause',
    replay: 'Replay',
    step: 'Step {n} of {total}',
    arguments: 'Arguments',
    result: 'Result',
    refused: 'Refused',
    recorded:
      'Recorded against Qdrant {qdrant} with mcp-qdrant {mcp}. CI re-records it on every pull request and fails if it changes.',
    tabs: {
      'text-search': {
        tab: 'Search in plain text',
        title: 'Search by meaning, by keywords, or both',
        intro:
          'Six help-center articles stored as plain text. The collection declares its embedding model in its own metadata, so every query and every write uses that same model; keyword search needs no model at all.',
        steps: [
          'Create a text collection: a multilingual embedding model for meaning, and a BM25 index (English stemming) for keywords.',
          'Write six articles as plain text. One text is one point: the server embeds it and keeps the text in the payload.',
          'A question that shares no word with the answer: "Reset your password" ranks first.',
          'The same question in Spanish finds the same article: the model is multilingual.',
          'Keywords, ranked by BM25 inside Qdrant: only the billing article mentions an invoice.',
          'Both at once, fused with Reciprocal Rank Fusion: "Set up single sign-on" for a question about signing in with a company account.',
        ],
      },
      'search-advisor': {
        tab: 'Diagnose and measure',
        title: 'A doctor and a ruler for search quality',
        intro:
          'Two hundred random vectors with int8 quantization, prepared beforehand. The index is built on a single thread so this recording is reproducible: the numbers below come back identical on every run.',
        steps: [
          'The collection, as it was prepared: scalar int8 quantization, an HNSW index built single-threaded.',
          'The doctor checks status, index, memory, aliases and text setup. One finding, with the exact call that acts on it.',
          'Apply that call as given, with a real alias name in place of the placeholder.',
          'The doctor again: nothing left to report.',
          'Measure every point as a query against an exact search. Quantized without rescoring, some true neighbors are lost; rescoring brings recall to 1.0. A search setting, not a rebuild.',
        ],
      },
      'hybrid-search': {
        tab: 'Hybrid search',
        title: 'Hybrid search, and why fusing matters',
        intro:
          'The same idea with vectors you bring yourself: six articles, each with a dense vector and a sparse (keyword) vector, hand-made and tiny so you can read them.',
        steps: [
          'Create a collection with one named dense vector and one sparse vector.',
          'Write six articles. The tool takes named dense and sparse vectors in the same point.',
          'Dense vectors only: "Set up single sign-on" ranks first. It is close in meaning, but it is not the answer.',
          'Sparse (keyword) vectors only: "Reset your password" ranks first, because the words match.',
          'Both, fused with Reciprocal Rank Fusion in a single call: the right article is first.',
        ],
      },
      'zero-downtime-reindex': {
        tab: 'Zero-downtime reindex',
        title: "Change a collection's distance without downtime",
        intro:
          'Qdrant cannot change a collection’s distance metric in place. The way out is a new collection and an alias switch, plus a copy that runs on the server so the vectors never pass through the model.',
        steps: [
          'Create the first collection (cosine).',
          'Write four points.',
          'Point the alias demo_docs at it. Clients use the alias from now on.',
          'Create the replacement with another distance (Euclid) and a different HNSW setting.',
          'Copy the points between the collections, addressing the source through its alias. It runs entirely on the server.',
          'Re-point the alias with a single operation.',
          'The alias now answers from the new collection: Euclid, the same four points.',
        ],
      },
      'know-the-payload': {
        tab: 'Know the payload',
        title: 'Write filters against keys that exist',
        intro:
          'The commonest way a model misuses a vector database is by inventing a payload key. This tool reports the keys that are really there, written the way Qdrant’s filter syntax wants them.',
        steps: [
          'Create a collection.',
          'Write four points whose payloads include a key with a space ("user id"), a nested object and an array.',
          'Index one field.',
          'Profile a random sample: value types, which keys are arrays or indexed, and the most frequent values of indexed ones. Note the key printed as "user id" with its quotes, as Qdrant requires.',
          'Use the reported key exactly as printed, in a filter.',
        ],
      },
      'safety-rails': {
        tab: 'Guard rails',
        title: 'Guard rails',
        intro:
          'Two things that stop a model from doing damage. One of them exists because a review found a hole.',
        steps: [
          'The collection has four points.',
          'A filter with no conditions selects every point. This call is refused. Before this guard it deleted the entire collection (see the log).',
          'Still four points.',
          'In read-only mode the registry itself drops every mutating tool: a client that lists the tools never sees them, so there is nothing to talk it into.',
        ],
      },
    },
  },
  tools: {
    ordinal: 'Tools',
    title: 'Every tool, from the live registry.',
    lead: '{tools} tools in {sets} toolsets. Only core ({core}) is on by default; the rest is opt-in, so a client is not handed everything at once.',
    searchLabel: 'Filter the tools',
    searchPlaceholder: 'Name or description',
    all: 'All',
    readOnlyOnly: 'Read-only only',
    showing: 'Showing {n} of {total}',
    noResults: 'No tool matches that filter.',
    details: 'Details',
    hide: 'Hide',
    badges: { readOnly: 'read-only', destructive: 'destructive', idempotent: 'idempotent' },
    onByDefault: 'on by default',
    toolsets: {
      core: 'Collection and point CRUD, qdrant_query (vectors or plain text) and a health check. A complete server on its own.',
      search: 'Batched and grouped queries, recommend, discover, distance matrices.',
      payload: 'Payload editing and indexing, named vectors, ordered batch operations.',
      snapshots: 'Backup and restore, per collection and for the whole storage.',
      admin: 'Aliases, shard layout, optimizer progress, collection copy, payload profiling, and the advisor: a collection doctor and a search-quality evaluation.',
      observability: 'Telemetry, metrics, quotas, self-diagnosed issues.',
    },
  },
  install: {
    title: 'Try it in two minutes.',
    lead: 'Pick the toolsets and copy the config. It runs locally; there is nothing to sign up for.',
    toolsets: 'Toolsets',
    readOnly: 'Read-only mode',
    registered: 'Registered tools',
    forcedCore: 'At least one toolset is required, so core stays on.',
    copyConfig: 'Copy the config',
    copied: 'Copied',
    copyFailed: 'Copy failed. The text is selected',
    announceCopied: 'Config copied to the clipboard.',
    announceFailed: 'Copy failed. The text is selected: press Control C or Command C.',
    paths: {
      uvx: "Claude Code or any MCP client: uvx runs it without installing (for search by meaning, uvx --from 'mcp-qdrant[embeddings]' mcp-qdrant)",
      mcpb: 'Claude Desktop: download mcp-qdrant.mcpb from the latest release and double-click it',
      docker: 'Docker, for streamable-http',
      dockerNote:
        'streamable-http refuses to start without a shared secret. The image only makes sense in this mode.',
    },
  },
  log: {
    ordinal: 'The log',
    title: 'The engineering log.',
    lead: 'What went wrong, how it was found, and the test that now stands guard. Each entry links the pull request and the release that fixed it.',
    labels: {
      claim: 'What was claimed',
      probe: 'What was run',
      result: 'What actually happens',
      fix: 'What changed',
      fixedIn: 'Fixed in',
      pinnedBy: 'Pinned by',
      review: 'found by an independent review',
    },
    cta: 'Open the repository',
  },
  quality: {
    ordinal: 'Quality',
    title: 'What keeps it honest.',
    lead: 'None of this is promised on the page. It is enforced by the repository.',
    pipeline: ['push', 'lint · types · generators', 'tests · real Qdrant', 'merge', 'tag', 'PyPI · GHCR · .mcpb', 'MCP Registry'],
    cards: [
      {
        title: 'Continuous integration',
        body: 'Every pull request runs lint, formatting, strict type checking and the whole test suite, with the integration tests against a real Qdrant {qdrant} service. Three generators (the README table, the data behind this page, the demo transcripts) fail the build if they drift.',
      },
      {
        title: 'Releases',
        body: 'A tag publishes to PyPI with Trusted Publishing (no stored token), pushes the Docker image to GHCR and attaches the .mcpb bundle to the release; once PyPI has it, the MCP Registry entry follows, authenticated by GitHub itself. Four workflows, checked after every tag.',
      },
      {
        title: 'Roadmap',
        body: 'Each phase has its own branch and pull request. ROADMAP.md keeps the decisions and the verified findings, including the features that were discarded and why.',
      },
    ],
  },
  faq: {
    ordinal: 'Questions',
    title: 'Questions a reviewer asks.',
    items: [
      {
        q: 'Is this affiliated with Qdrant?',
        a: 'No. It is an independent, MIT-licensed project that wraps Qdrant’s own qdrant-client SDK.',
      },
      {
        q: 'Does it create embeddings?',
        a: 'Only to search or store plain text, and only with the optional embeddings extra: the text is embedded locally with fastembed, using the model the collection declares in its own metadata — never a guessed one. It still never parses or splits documents: one text is one point. Keyword search (BM25) needs no model at all; Qdrant 1.20 ranks a text index.',
      },
      {
        q: 'Is there a hosted version?',
        a: 'No, by design. An earlier phase added a multi-tenant public mode and it was removed again: this is a project you run (uvx mcp-qdrant), not a service someone has to operate.',
      },
      {
        q: 'How was it built?',
        a: 'Python 3.12 with uv, on top of the official MCP Python SDK and qdrant-client, with Pydantic validating every input, tenacity retrying transport failures and fastembed for local embeddings. Quality is enforced by pytest against a real Qdrant in CI, strict mypy, ruff and pre-commit; GitHub Actions publishes to PyPI (Trusted Publishing), to GHCR and as a Claude Desktop bundle. Claude Code assisted the work and the commits carry its Co-Authored-By trailer; what decides what is true is the toolchain, not the assistant. This page is Nuxt, Tailwind, GSAP and Lenis, served by nginx in Docker.',
      },
      {
        q: 'Which Qdrant versions does it support?',
        a: 'CI tests it against v1.20.0, and every claim in the tool descriptions is pinned against that version. Text search needs v1.16 or newer and its BM25 mode v1.20; two vector tools need an endpoint that servers older than v1.19 answer with 404.',
      },
      {
        q: 'What does it not cover?',
        a: 'Distributed-cluster administration: shard keys and resharding need a cluster, and the project targets a single node. The roadmap records that decision and what was verified.',
      },
    ],
  },
  contact: {
    ordinal: 'Contact',
    title: 'See the code.',
    lead: 'The repository has the whole history: every phase, every pull request, every finding.',
    cta: 'Open the repository',
    author: 'Author',
    github: 'GitHub',
    linkedin: 'LinkedIn',
    email: 'Email',
  },
  footer: {
    license: 'MIT licensed.',
    independent: 'Independent project, not affiliated with Qdrant.',
    version: 'Version {version}',
    builtWith: 'Built with Nuxt, GSAP and Lenis, served as static files.',
  },
}

const es: Copy = {
  htmlLang: 'es',
  meta: {
    title: 'Qdrant MCP — {tools} herramientas MCP, cada afirmación probada contra un servidor real',
    description:
      'Un servidor del Model Context Protocol que expone la API de Qdrant como {tools} herramientas: proyecto de portfolio de Adrián Vázquez, con el registro de ingeniería público de lo que falló y cómo se descubrió. Python, {tests} tests, CI contra un Qdrant real.',
    ogAlt: 'Toda la API de Qdrant como herramientas MCP. Cada afirmación, probada contra un servidor real.',
  },
  a11y: {
    skip: 'Saltar al contenido',
    pauseAnimation: 'Pausar la animación',
    playAnimation: 'Reanudar la animación',
    langSwitch: 'Idioma',
    opensNewTab: '(se abre en una pestaña nueva)',
    sections: 'Secciones',
  },
  nav: {
    method: 'Método',
    architecture: 'Arquitectura',
    scenarios: 'En acción',
    tools: 'Herramientas',
    log: 'Bitácora',
    quality: 'Calidad',
    github: 'GitHub',
  },
  hero: {
    kicker: 'Proyecto de portfolio · Adrián Vázquez',
    title: 'Toda la API de Qdrant como {tools} herramientas MCP. Cada afirmación, probada contra un servidor real.',
    deck: 'Un servidor del Model Context Protocol en Python que permite a un LLM gestionar una base de datos vectorial Qdrant, buscar en ella con texto normal, y diagnosticarla y afinarla. Su bitácora de ingeniería es pública: qué falló, cómo se descubrió y el test que ahora hace guardia.',
    ctaPrimary: 'Abrir el repositorio',
    ctaSecondary: 'Leer la bitácora de ingeniería',
    canvasLabel:
      'Espacio vectorial tridimensional ilustrativo. Mueve el puntero sobre él para sondearlo: los cinco puntos más cercanos se iluminan, con sus distancias calculadas en tu navegador.',
    canvasCaption: 'proyección ilustrativa · distancias calculadas en vivo',
    nearest: 'más cercanos',
  },
  proof: {
    tools: 'herramientas MCP',
    toolsSub: '{readOnly} de ellas de solo lectura',
    tests: 'tests',
    testsSub: 'unitarios y de integración, tal como los recoge pytest',
    changelog: 'entradas del changelog',
    changelogSub: 'última: v{version}',
    code: 'líneas de Python',
    codeSub: '{src} de código y {testLines} de tests',
    schema: 'KB de schemas de herramientas',
    schemaSub: 'toolset por defecto, cargado en el contexto del modelo',
    note: 'Cada cifra de aquí que parece una medición la genera desde el repositorio un script que CI vuelve a ejecutar. Pasa el cursor por una para ver cuál.',
  },
  method: {
    ordinal: 'El método',
    title: 'Nada se escribe hasta que se ha ejecutado.',
    lead: 'El comportamiento de Qdrant es fácil de suponer y caro de equivocar. Cada afirmación de las descripciones de las herramientas de este proyecto pasa por los mismos tres pasos.',
    steps: [
      {
        name: 'Probar',
        body: 'Ejecutar el escenario contra un servidor Qdrant real, empezando por el camino de fallo. Leer el estado después, no solo la respuesta.',
        example:
          'Una operación de alias válida seguida de otra que falla, y luego listar los alias. En Qdrant 1.19 la primera seguía aplicada, así que la herramienta no decía "atómico".',
      },
      {
        name: 'Fijar',
        body: 'Convertir lo observado en un test de integración, de modo que una versión futura de Qdrant que lo cambie rompa el CI en lugar de dejar la documentación obsoleta en silencio.',
        example:
          'test_alias_batch_is_all_or_nothing — falló en CI el día que Qdrant 1.20 hizo esos lotes todo o nada, y la descripción cambió con él.',
      },
      {
        name: 'Revisar',
        body: 'A un lector independiente, sin conocer el razonamiento, se le pide reproducir y no especular. Cada hallazgo se reproduce una segunda vez antes de actuar sobre él.',
        example: 'Una de esas revisiones encontró que un filtro vacío borraba una colección entera. Está en la bitácora.',
      },
    ],
    cta: 'Leer la bitácora completa',
  },
  architecture: {
    ordinal: 'Arquitectura',
    title: 'Cómo viaja una llamada a una herramienta.',
    lead: 'Cinco saltos entre un modelo y la base de datos. Cada uno es una decisión, no un valor por defecto.',
    caption: 'haz scroll para seguir una llamada',
    nodes: [
      {
        name: 'Cliente MCP',
        tag: 'Claude, Cursor, cualquier cliente MCP',
        why: 'Recibe {tools} definiciones de herramientas. Los schemas que se anuncian son compactos —{coreKb} KB para el toolset por defecto en vez de unos 150 KB— porque se cargan en el contexto del modelo en cada conversación.',
        source: 'tests/unit/test_schemas.py',
        payloadTitle: 'tools/call, tal como lo envía el cliente',
        payloadLines: [],
      },
      {
        name: 'Transporte',
        tag: 'stdio · streamable-http',
        why: 'stdio por defecto. El transporte remoto se niega a arrancar sin un secreto compartido, y no existe ninguna instancia alojada: es un proyecto que se ejecuta, no un servicio.',
        source: 'src/mcp_qdrant/cli.py',
        payloadTitle: 'Por el cable',
        payloadLines: [
          'stdio: un mensaje JSON-RPC por línea, por stdin y stdout',
          'streamable-http: POST /mcp',
          '  Authorization: Bearer <secreto compartido>   (obligatorio para arrancar)',
        ],
      },
      {
        name: 'ToolRegistry',
        tag: 'toolsets · solo lectura · tope de resultados',
        why: 'Un único punto de control. Filtra toolsets, elimina toda herramienta que escribe en modo solo lectura (sobreviven {readOnly} de {tools}) y limita los resultados por llamada. Una herramienta no puede saltárselo registrándose de otra forma.',
        source: 'src/mcp_qdrant/tools/registry.py',
        payloadTitle: 'Qué comprueba el registro',
        payloadLines: [
          '✓ el toolset core está activo',
          '✓ el modo solo lectura está desactivado (qdrant_query es de solo lectura, así que pasaría igualmente)',
          '✓ limit {limit} ≤ tope {cap} (QDRANT_MCP_MAX_LIMIT)',
          '✓ los argumentos validan contra el modelo Pydantic de la herramienta',
        ],
      },
      {
        name: 'call_qdrant',
        tag: 'reintentos · errores traducidos',
        why: 'Solo se reintenta una petición que no llegó a Qdrant: tras un timeout, una escritura puede haberse aplicado ya, así que al modelo se le pide comprobarlo en vez de repetir la llamada. Un error de Qdrant llega al modelo como el mensaje propio de Qdrant, nunca como un genérico "Error executing tool".',
        source: 'src/mcp_qdrant/tools/errors.py',
        payloadTitle: 'Qué se envía a Qdrant',
        payloadLines: [
          'POST /collections/{collection}/points/query',
          '',
          'conexión rechazada   → se reintenta con backoff',
          'timeout tras enviar  → "puede haberse aplicado", sin reintento',
          'error de Qdrant      → ToolError(el mensaje propio de Qdrant)',
        ],
      },
      {
        name: 'Qdrant',
        tag: 'qdrant-client sobre REST',
        why: 'El SDK oficial, de modo que las entradas de las herramientas reutilizan sus modelos y siguen su versión. El cliente trae vectores, o texto normal, que se incrusta en local con el modelo que la colección declara en sus propios metadatos.',
        source: 'ROADMAP.md · principio 1',
        payloadTitle: 'La respuesta de Qdrant, resumida',
        payloadLines: [],
      },
    ],
  },
  scenarios: {
    ordinal: 'En acción',
    title: 'Seis cosas que un modelo puede hacer con él.',
    lead: 'No son maquetas. Cada llamada de abajo se ejecutó a través del servidor MCP contra un Qdrant real, y la respuesta es la que devolvió.',
    play: 'Reproducir',
    pause: 'Pausar',
    replay: 'Repetir',
    step: 'Paso {n} de {total}',
    arguments: 'Argumentos',
    result: 'Resultado',
    refused: 'Rechazada',
    recorded:
      'Grabado contra Qdrant {qdrant} con mcp-qdrant {mcp}. CI lo vuelve a grabar en cada pull request y falla si cambia.',
    tabs: {
      'text-search': {
        tab: 'Buscar con texto',
        title: 'Buscar por significado, por palabras clave o por ambas',
        intro:
          'Seis artículos de un centro de ayuda guardados como texto normal. La colección declara su modelo de embeddings en sus propios metadatos, así que cada consulta y cada escritura usan ese mismo modelo; la búsqueda por palabras clave no necesita modelo.',
        steps: [
          'Crear una colección de texto: un modelo de embeddings multilingüe para el significado y un índice BM25 (con stemming en inglés) para las palabras clave.',
          'Escribir seis artículos como texto normal. Un texto es un punto: el servidor lo incrusta y guarda el texto en el payload.',
          'Una pregunta que no comparte ninguna palabra con la respuesta: "Reset your password" queda primero.',
          'La misma pregunta en español encuentra el mismo artículo: el modelo es multilingüe.',
          'Palabras clave, ordenadas por BM25 dentro de Qdrant: solo el artículo de facturación menciona una factura.',
          'Las dos a la vez, fusionadas con Reciprocal Rank Fusion: "Set up single sign-on" para una pregunta sobre entrar con la cuenta de la empresa.',
        ],
      },
      'search-advisor': {
        tab: 'Diagnosticar y medir',
        title: 'Un médico y una regla para la calidad de búsqueda',
        intro:
          'Doscientos vectores aleatorios con cuantización int8, preparados de antemano. El índice se construye en un solo hilo para que esta grabación sea reproducible: las cifras de abajo salen idénticas en cada ejecución.',
        steps: [
          'La colección tal como se preparó: cuantización escalar int8 y un índice HNSW construido en un solo hilo.',
          'El doctor revisa estado, índice, memoria, aliases y configuración de texto. Un hallazgo, con la llamada exacta que lo resuelve.',
          'Aplicar esa llamada tal cual, con un nombre de alias real en lugar del marcador.',
          'El doctor otra vez: ya no queda nada que señalar.',
          'Medir cada punto como consulta frente a una búsqueda exacta. Cuantizado sin rescore se pierden algunos vecinos de verdad; con rescore el recall llega a 1,0. Un ajuste de búsqueda, no una reconstrucción.',
        ],
      },
      'hybrid-search': {
        tab: 'Búsqueda híbrida',
        title: 'Búsqueda híbrida, y por qué importa fusionar',
        intro:
          'La misma idea con vectores que traes tú: seis artículos, cada uno con un vector denso y un vector disperso (de palabras clave), artesanales y diminutos para que se puedan leer.',
        steps: [
          'Crear una colección con un vector denso con nombre y un vector disperso.',
          'Escribir seis artículos. La herramienta acepta vectores densos y dispersos con nombre en el mismo punto.',
          'Solo vectores densos: "Set up single sign-on" queda primero. Se parece en significado, pero no es la respuesta.',
          'Solo vectores dispersos (palabras clave): "Reset your password" queda primero, porque las palabras coinciden.',
          'Ambos, fusionados con Reciprocal Rank Fusion en una sola llamada: el artículo correcto queda primero.',
        ],
      },
      'zero-downtime-reindex': {
        tab: 'Reindexar sin downtime',
        title: 'Cambiar la distancia de una colección sin downtime',
        intro:
          'Qdrant no puede cambiar la métrica de distancia de una colección in situ. La salida es una colección nueva y un cambio de alias, más una copia que se ejecuta en el servidor para que los vectores nunca pasen por el modelo.',
        steps: [
          'Crear la primera colección (coseno).',
          'Escribir cuatro puntos.',
          'Apuntar el alias demo_docs a ella. Desde ahora los clientes usan el alias.',
          'Crear la colección de reemplazo con otra distancia (Euclid) y otro ajuste de HNSW.',
          'Copiar los puntos entre las colecciones, direccionando el origen por su alias. Se ejecuta entero en el servidor.',
          'Reapuntar el alias con una sola operación.',
          'El alias ahora responde desde la colección nueva: Euclid, los mismos cuatro puntos.',
        ],
      },
      'know-the-payload': {
        tab: 'Conocer el payload',
        title: 'Escribir filtros con claves que existen',
        intro:
          'La forma más común en que un modelo usa mal una base de datos vectorial es inventándose una clave de payload. Esta herramienta informa de las claves que de verdad hay, escritas como las quiere la sintaxis de filtros de Qdrant.',
        steps: [
          'Crear una colección.',
          'Escribir cuatro puntos cuyos payloads incluyen una clave con un espacio ("user id"), un objeto anidado y un array.',
          'Indexar un campo.',
          'Perfilar una muestra aleatoria: tipos de valor, qué claves son arrays o están indexadas y los valores más frecuentes de las indexadas. Fíjate en la clave impresa como "user id" con sus comillas, como exige Qdrant.',
          'Usar la clave informada tal cual aparece impresa, en un filtro.',
        ],
      },
      'safety-rails': {
        tab: 'Barreras de seguridad',
        title: 'Barreras de seguridad',
        intro:
          'Dos cosas que impiden que un modelo haga daño. Una de ellas existe porque una revisión encontró un agujero.',
        steps: [
          'La colección tiene cuatro puntos.',
          'Un filtro sin condiciones selecciona todos los puntos. Esta llamada se rechaza. Antes de esta barrera borraba la colección entera (véase la bitácora).',
          'Siguen siendo cuatro puntos.',
          'En modo solo lectura el propio registro elimina toda herramienta que escribe: un cliente que lista las herramientas no las ve nunca, así que no hay nada a lo que convencerle.',
        ],
      },
    },
  },
  tools: {
    ordinal: 'Herramientas',
    title: 'Todas las herramientas, desde el registro vivo.',
    lead: '{tools} herramientas en {sets} toolsets. Solo core ({core}) está activo por defecto; el resto es opcional, para no entregar todo al cliente de golpe.',
    searchLabel: 'Filtrar las herramientas',
    searchPlaceholder: 'Nombre o descripción',
    all: 'Todas',
    readOnlyOnly: 'Solo lectura',
    showing: 'Mostrando {n} de {total}',
    noResults: 'Ninguna herramienta coincide con ese filtro.',
    details: 'Detalles',
    hide: 'Ocultar',
    badges: { readOnly: 'solo lectura', destructive: 'destructiva', idempotent: 'idempotente' },
    onByDefault: 'activo por defecto',
    toolsets: {
      core: 'CRUD de colecciones y puntos, qdrant_query (con vectores o con texto) y una comprobación de salud. Un servidor completo por sí solo.',
      search: 'Consultas por lotes y agrupadas, recommend, discover, matrices de distancia.',
      payload: 'Edición e indexado de payload, vectores con nombre, operaciones por lotes ordenadas.',
      snapshots: 'Copia y restauración, por colección y de todo el almacenamiento.',
      admin: 'Aliases, disposición de shards, progreso del optimizador, copia de colecciones, perfilado de payload y el asesor: un doctor de colecciones y una evaluación de la calidad de búsqueda.',
      observability: 'Telemetría, métricas, cuotas, incidencias autodiagnosticadas.',
    },
  },
  install: {
    title: 'Pruébalo en dos minutos.',
    lead: 'Elige los toolsets y copia la configuración. Se ejecuta en local; no hay que registrarse en nada.',
    toolsets: 'Toolsets',
    readOnly: 'Modo solo lectura',
    registered: 'Herramientas registradas',
    forcedCore: 'Hace falta al menos un toolset, así que core se queda activo.',
    copyConfig: 'Copiar la configuración',
    copied: 'Copiado',
    copyFailed: 'Falló la copia. El texto queda seleccionado',
    announceCopied: 'Configuración copiada al portapapeles.',
    announceFailed: 'Falló la copia. El texto queda seleccionado: pulsa Control C o Comando C.',
    paths: {
      uvx: "Claude Code o cualquier cliente MCP: uvx lo ejecuta sin instalar (para buscar por significado, uvx --from 'mcp-qdrant[embeddings]' mcp-qdrant)",
      mcpb: 'Claude Desktop: descarga mcp-qdrant.mcpb de la última release y haz doble clic',
      docker: 'Docker, para streamable-http',
      dockerNote:
        'streamable-http se niega a arrancar sin un secreto compartido. La imagen solo tiene sentido en este modo.',
    },
  },
  log: {
    ordinal: 'La bitácora',
    title: 'La bitácora de ingeniería.',
    lead: 'Qué falló, cómo se descubrió y el test que ahora hace guardia. Cada entrada enlaza el pull request y la release que lo corrigió.',
    labels: {
      claim: 'Qué se afirmó',
      probe: 'Qué se ejecutó',
      result: 'Qué ocurre de verdad',
      fix: 'Qué cambió',
      fixedIn: 'Corregido en',
      pinnedBy: 'Fijado por',
      review: 'descubierto por una revisión independiente',
    },
    cta: 'Abrir el repositorio',
  },
  quality: {
    ordinal: 'Calidad',
    title: 'Lo que lo mantiene honesto.',
    lead: 'Nada de esto se promete en la página. Lo impone el repositorio.',
    pipeline: ['push', 'lint · tipos · generadores', 'tests · Qdrant real', 'merge', 'tag', 'PyPI · GHCR · .mcpb', 'MCP Registry'],
    cards: [
      {
        title: 'Integración continua',
        body: 'Cada pull request ejecuta lint, formato, comprobación de tipos estricta y toda la suite de tests, con los de integración contra un servicio Qdrant {qdrant} real. Tres generadores (la tabla del README, los datos de esta página, las transcripciones de las demos) rompen la build si se desincronizan.',
      },
      {
        title: 'Releases',
        body: 'Un tag publica en PyPI con Trusted Publishing (sin token guardado), sube la imagen de Docker a GHCR y adjunta el bundle .mcpb a la release; cuando PyPI ya la tiene, la entrada del MCP Registry la sigue, autenticada por el propio GitHub. Cuatro workflows, comprobados tras cada tag.',
      },
      {
        title: 'Roadmap',
        body: 'Cada fase tiene su propia rama y su pull request. ROADMAP.md guarda las decisiones y los hallazgos verificados, incluidas las funcionalidades descartadas y por qué.',
      },
    ],
  },
  faq: {
    ordinal: 'Preguntas',
    title: 'Preguntas que hace un revisor.',
    items: [
      {
        q: '¿Está afiliado a Qdrant?',
        a: 'No. Es un proyecto independiente con licencia MIT que envuelve el SDK qdrant-client de la propia Qdrant.',
      },
      {
        q: '¿Crea embeddings?',
        a: 'Solo para buscar o guardar texto normal, y solo con el extra opcional embeddings: el texto se incrusta en local con fastembed, usando el modelo que la colección declara en sus propios metadatos, nunca uno supuesto. Sigue sin parsear ni trocear documentos: un texto es un punto. La búsqueda por palabras clave (BM25) no necesita modelo; la ordena Qdrant 1.20 sobre un índice de texto.',
      },
      {
        q: '¿Hay una versión alojada?',
        a: 'No, por diseño. Una fase anterior añadió un modo público multiinquilino y se retiró: es un proyecto que se ejecuta (uvx mcp-qdrant), no un servicio que alguien tenga que operar.',
      },
      {
        q: '¿Cómo se construyó?',
        a: 'Python 3.12 con uv, sobre el SDK oficial de Python de MCP y qdrant-client, con Pydantic validando cada entrada, tenacity reintentando los fallos de transporte y fastembed para los embeddings en local. La calidad la imponen pytest contra un Qdrant real en CI, mypy estricto, ruff y pre-commit; GitHub Actions publica en PyPI (Trusted Publishing), en GHCR y como bundle para Claude Desktop. Claude Code ayudó en el trabajo y los commits llevan su trailer Co-Authored-By; lo que decide qué es verdad es la cadena de herramientas, no el asistente. Esta página es Nuxt, Tailwind, GSAP y Lenis, servida por nginx en Docker.',
      },
      {
        q: '¿Qué versiones de Qdrant soporta?',
        a: 'CI lo prueba contra la v1.20.0, y cada afirmación de las descripciones de las herramientas está fijada contra esa versión. La búsqueda por texto necesita la v1.16 o posterior y su modo BM25, la v1.20; dos herramientas de vectores necesitan un endpoint al que los servidores anteriores a la v1.19 responden con 404.',
      },
      {
        q: '¿Qué no cubre?',
        a: 'La administración de clústeres distribuidos: las shard keys y el resharding necesitan un clúster, y el proyecto apunta a un único nodo. El roadmap recoge esa decisión y lo que se verificó.',
      },
    ],
  },
  contact: {
    ordinal: 'Contacto',
    title: 'Mira el código.',
    lead: 'El repositorio tiene toda la historia: cada fase, cada pull request, cada hallazgo.',
    cta: 'Abrir el repositorio',
    author: 'Autor',
    github: 'GitHub',
    linkedin: 'LinkedIn',
    email: 'Email',
  },
  footer: {
    license: 'Licencia MIT.',
    independent: 'Proyecto independiente, sin afiliación con Qdrant.',
    version: 'Versión {version}',
    builtWith: 'Hecho con Nuxt, GSAP y Lenis, servido como ficheros estáticos.',
  },
}

export const COPY: Record<Lang, Copy> = { en, es }
