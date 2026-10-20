// The engineering log: real entries, from this repository's own history. Nothing here is
// illustrative. Every `tests` entry is a test that exists (name + file), every PR and
// version is one that was merged and released, and each entry says what the claim was,
// what was run, what actually happened and what changed.
//
// Voice is impersonal on purpose: the log records what the repository records.

import type { Lang } from './copy'

export const REPO = 'https://github.com/avaazquezz/Qdrant-MCP'

interface Prose {
  title: string
  claim: string
  probe: string
  result: string
  fix: string
}

export interface LogEntry {
  id: string
  /** Releases that carry the fix (tags v<version>). */
  versions: string[]
  /** Pull requests, in order. */
  prs: number[]
  tests: { name: string; file: string }[]
  /** True if an independent review (a reader told to reproduce, not speculate) found it. */
  review: boolean
  text: Record<Lang, Prose>
}

export const LOG: LogEntry[] = [
  {
    id: 'sparse-hybrid',
    versions: ['2.1.0'],
    prs: [32],
    tests: [
      {
        name: 'test_hybrid_rrf_over_dense_and_sparse_prefetch',
        file: 'tests/integration/test_sparse_multivector_integration.py',
      },
    ],
    review: false,
    text: {
      en: {
        title: 'Hybrid search that could not run',
        claim:
          'Hybrid search over dense and sparse vectors works: the query tool’s own description carried an example.',
        probe:
          'Run that example against a real Qdrant, then try to write a point with a sparse vector through the upsert tool.',
        result:
          'The example failed ("Conversion between sparse and regular vectors failed"), and the upsert tool rejected every vector that was not a plain list of numbers. The flagship feature could not work, and no integration test covered sparse vectors at all.',
        fix: 'One shared vector type for writing and querying, conditional upserts (insert-only, update-only), and integration tests for named, sparse and multivector points.',
      },
      es: {
        title: 'Una búsqueda híbrida que no podía ejecutarse',
        claim:
          'La búsqueda híbrida sobre vectores densos y dispersos funciona: la propia descripción de la herramienta de consulta traía un ejemplo.',
        probe:
          'Ejecutar ese ejemplo contra un Qdrant real y luego intentar escribir un punto con un vector disperso a través de la herramienta de upsert.',
        result:
          'El ejemplo falló ("Conversion between sparse and regular vectors failed"), y la herramienta de upsert rechazaba cualquier vector que no fuera una lista simple de números. La funcionalidad estrella no podía funcionar y ningún test de integración cubría los vectores dispersos.',
        fix: 'Un único tipo de vector compartido para escribir y consultar, upserts condicionales (solo insertar, solo actualizar) y tests de integración para puntos con nombre, dispersos y multivector.',
      },
    },
  },
  {
    id: 'alias-atomicity',
    versions: ['2.2.0'],
    prs: [33],
    tests: [
      {
        name: 'test_alias_batch_is_not_rolled_back_when_a_later_operation_fails',
        file: 'tests/integration/test_admin_integration.py',
      },
    ],
    review: false,
    text: {
      en: {
        title: 'The alias batch that was not atomic',
        claim: 'Alias operations sent in one call are applied atomically (the first draft of the tool description).',
        probe:
          'One request with a valid "create alias" followed by a "create alias" on a collection that does not exist, then list the aliases.',
        result: 'The request fails, but the first alias is still there. A batch is not rolled back.',
        fix: 'The description says so and recommends a single operation to re-point an alias, which is all-or-nothing by definition. An integration test fails if Qdrant ever changes this.',
      },
      es: {
        title: 'El lote de alias que no era atómico',
        claim:
          'Las operaciones de alias enviadas en una llamada se aplican de forma atómica (el primer borrador de la descripción de la herramienta).',
        probe:
          'Una petición con un "crear alias" válido seguido de otro sobre una colección que no existe, y luego listar los alias.',
        result: 'La petición falla, pero el primer alias sigue ahí. Un lote no se revierte.',
        fix: 'La descripción lo dice y recomienda una sola operación para reapuntar un alias, que es todo o nada por definición. Un test de integración falla si Qdrant cambia esto alguna vez.',
      },
    },
  },
  {
    id: 'mmr-noop',
    versions: ['2.4.0'],
    prs: [35],
    tests: [
      {
        name: 'test_mmr_needs_candidates_beyond_limit_and_offset_pages_inside_the_limit',
        file: 'tests/integration/test_query_power_integration.py',
      },
    ],
    review: false,
    text: {
      en: {
        title: 'Diversity that did nothing',
        claim: 'MMR re-ranks results for diversity.',
        probe: 'Query with MMR, no candidate limit and a limit of 2, and compare it with the plain query.',
        result:
          'Identical results. The candidate pool defaults to the limit, so MMR has nothing to choose from. And the offset is applied inside those results: offset 1 with limit 2 returns one point.',
        fix: 'Both facts are in the tool description and pinned by a test.',
      },
      es: {
        title: 'Una diversidad que no hacía nada',
        claim: 'MMR reordena los resultados para dar diversidad.',
        probe: 'Consultar con MMR, sin límite de candidatos y con límite 2, y compararlo con la consulta normal.',
        result:
          'Resultados idénticos. El conjunto de candidatos por defecto es el límite, así que MMR no tiene entre qué elegir. Y el offset se aplica dentro de esos resultados: offset 1 con límite 2 devuelve un punto.',
        fix: 'Ambos hechos están en la descripción de la herramienta y fijados por un test.',
      },
    },
  },
  {
    id: 'schema-weight',
    versions: ['2.5.0'],
    prs: [36],
    tests: [
      {
        name: 'test_the_default_toolset_stays_within_its_schema_budget',
        file: 'tests/unit/test_schemas.py',
      },
    ],
    review: false,
    text: {
      en: {
        title: 'Tool definitions that ate the context',
        claim: 'A compact set of tool definitions.',
        probe: 'Measure the input schemas that a client loads into the model’s context.',
        result:
          '571 KB for the whole catalog and 150 KB for the default toolset: every tool carried its own copy of Qdrant’s 16 KB filter schema.',
        fix: 'The advertised schemas were compacted by roughly two thirds without changing what is accepted, and a test now enforces a size budget so the weight cannot creep back.',
      },
      es: {
        title: 'Definiciones de herramientas que se comían el contexto',
        claim: 'Un conjunto compacto de definiciones de herramientas.',
        probe: 'Medir los schemas de entrada que un cliente carga en el contexto del modelo.',
        result:
          '571 KB para el catálogo completo y 150 KB para el toolset por defecto: cada herramienta llevaba su propia copia del schema de filtros de Qdrant, de 16 KB.',
        fix: 'Los schemas anunciados se compactaron en torno a dos tercios sin cambiar lo que se acepta, y un test impone ahora un presupuesto de tamaño para que el peso no vuelva a crecer sin que nadie lo note.',
      },
    },
  },
  {
    id: 'schema-parity',
    versions: ['2.5.0', '2.6.0'],
    prs: [36, 37],
    tests: [
      {
        name: 'test_filter_schema_accepts_what_qdrants_filter_accepts',
        file: 'tests/unit/test_schemas.py',
      },
    ],
    review: true,
    text: {
      en: {
        title: 'A compact schema that refused legal calls',
        claim: 'The compact filter schema accepts exactly what Qdrant’s filter model accepts.',
        probe: 'Validate the advertised schema and the real model against the same valid and invalid inputs.',
        result:
          'The first draft refused a legal single condition where a list was expected. After parity tests were added, an independent review found it also refused explicit nulls and a legal "global" option. A client validating arguments against the schema would have rejected legal calls.',
        fix: 'Both fixed. The parity tests now run the schema and the model against the same samples, and a second test fails if the installed client gains a condition the hand-written grammar does not mention.',
      },
      es: {
        title: 'Un schema compacto que rechazaba llamadas legales',
        claim: 'El schema compacto de filtros acepta exactamente lo que acepta el modelo de filtros de Qdrant.',
        probe: 'Validar el schema anunciado y el modelo real con las mismas entradas válidas e inválidas.',
        result:
          'El primer borrador rechazaba una condición única legal donde se esperaba una lista. Tras añadir tests de paridad, una revisión independiente encontró que también rechazaba nulls explícitos y una opción "global" legal. Un cliente que validara los argumentos contra el schema habría rechazado llamadas legales.',
        fix: 'Ambos corregidos. Los tests de paridad ejecutan ahora el schema y el modelo con las mismas muestras, y otro test falla si el cliente instalado gana una condición que la gramática escrita a mano no menciona.',
      },
    },
  },
  {
    id: 'empty-filter',
    versions: ['2.6.0'],
    prs: [37],
    tests: [
      {
        name: 'test_an_empty_filter_no_longer_wipes_the_collection',
        file: 'tests/integration/test_review_hardening_integration.py',
      },
    ],
    review: true,
    text: {
      en: {
        title: 'The filter that deleted everything',
        claim: 'A delete needs exactly one selector, ids or a filter, so it cannot be ambiguous.',
        probe: 'Delete with the filters {}, {"must": []} and {"should": []} on a small collection.',
        result:
          'Each one deleted every point. An empty filter matches everything, and nothing in the tool said no. A model building its condition list dynamically and ending up with an empty one would wipe the data.',
        fix: 'A filter with no conditions is refused in delete, payload and vector tools and inside batch updates, and a batch with one refused operation sends nothing at all.',
      },
      es: {
        title: 'El filtro que lo borraba todo',
        claim: 'Un borrado necesita exactamente un selector, ids o un filtro, así que no puede ser ambiguo.',
        probe: 'Borrar con los filtros {}, {"must": []} y {"should": []} en una colección pequeña.',
        result:
          'Cada uno borró todos los puntos. Un filtro vacío coincide con todo y nada en la herramienta lo impedía. Un modelo que construya su lista de condiciones dinámicamente y acabe con una vacía borraría los datos.',
        fix: 'Un filtro sin condiciones se rechaza en las herramientas de borrado, payload y vectores y dentro de los lotes, y un lote con una operación rechazada no envía nada.',
      },
    },
  },
  {
    id: 'batch-atomicity',
    versions: ['2.6.0'],
    prs: [37],
    tests: [
      {
        name: 'test_a_batch_is_not_all_or_nothing_as_the_tool_now_says',
        file: 'tests/integration/test_review_hardening_integration.py',
      },
    ],
    review: true,
    text: {
      en: {
        title: 'Atomic, since the third phase, and never true',
        claim: 'The batch-update tool runs its operations atomically (in its description since the third phase).',
        probe: 'A valid upsert followed by one with the wrong vector size, then count the points.',
        result:
          'The first one stays applied. It was never atomic. This is the same mistake as the alias entry: a property of Qdrant asserted without running it.',
        fix: 'The description, the tool title, the README and this page no longer say it, and a test pins the real behavior.',
      },
      es: {
        title: 'Atómico desde la tercera fase, y nunca fue cierto',
        claim: 'La herramienta de actualización por lotes ejecuta sus operaciones de forma atómica (en su descripción desde la tercera fase).',
        probe: 'Un upsert válido seguido de otro con un tamaño de vector incorrecto, y luego contar los puntos.',
        result:
          'El primero queda aplicado. Nunca fue atómico. Es el mismo error que la entrada de los alias: una propiedad de Qdrant afirmada sin ejecutarla.',
        fix: 'La descripción, el título de la herramienta, el README y esta página ya no lo dicen, y un test fija el comportamiento real.',
      },
    },
  },
  {
    id: 'silent-extra-keys',
    versions: ['2.6.0'],
    prs: [37],
    tests: [
      {
        name: 'test_an_unknown_key_in_a_nested_input_is_an_error_not_a_silent_no_op',
        file: 'tests/unit/test_input_strictness.py',
      },
    ],
    review: true,
    text: {
      en: {
        title: 'A filter that silently did not filter',
        claim: 'A prefetch stage takes a filter.',
        probe: 'Give a stage Qdrant’s own key, "filter", instead of the tool’s "query_filter".',
        result:
          'No error, and the results were not filtered: unknown keys were silently ignored. A misspelled option of MMR ran with its defaults the same way, and a typo in a point’s payload key dropped the payload.',
        fix: 'Nested inputs now reject unknown keys with a clear error.',
      },
      es: {
        title: 'Un filtro que callaba y no filtraba',
        claim: 'Una etapa de prefetch acepta un filtro.',
        probe: 'Darle a una etapa la clave propia de Qdrant, "filter", en lugar de "query_filter" de la herramienta.',
        result:
          'Ningún error, y los resultados no estaban filtrados: las claves desconocidas se ignoraban en silencio. Una opción de MMR mal escrita se ejecutaba con sus valores por defecto de la misma forma, y una errata en la clave del payload de un punto descartaba el payload.',
        fix: 'Las entradas anidadas rechazan ahora las claves desconocidas con un error claro.',
      },
    },
  },
  {
    id: 'filter-keys',
    versions: ['2.6.0'],
    prs: [37],
    tests: [
      {
        name: 'test_schema_infer_emits_keys_that_work_as_filter_keys_and_index_keys',
        file: 'tests/integration/test_review_hardening_integration.py',
      },
    ],
    review: true,
    text: {
      en: {
        title: 'Keys that could not be pasted into a filter',
        claim: 'Payload profiling reports keys written the way Qdrant’s filters expect.',
        probe: 'Profile a collection with a key that contains a space, then use the printed key in a filter.',
        result:
          'Qdrant answers 400: such a key needs double quotes. A literal key "k[]" was read as an array path, and an index created on a quoted key never matched its entry in the profile.',
        fix: 'Keys are quoted where the syntax requires it, which is also the form Qdrant reports for indexes, so keys now match their index.',
      },
      es: {
        title: 'Claves que no se podían pegar en un filtro',
        claim: 'El perfilado de payload informa de las claves escritas como esperan los filtros de Qdrant.',
        probe: 'Perfilar una colección con una clave que contiene un espacio y usar la clave impresa en un filtro.',
        result:
          'Qdrant responde 400: una clave así necesita comillas dobles. Una clave literal "k[]" se leía como una ruta de array, y un índice creado sobre una clave entre comillas no coincidía nunca con su entrada en el perfil.',
        fix: 'Las claves se entrecomillan donde la sintaxis lo exige, que es también la forma en que Qdrant informa de los índices, así que las claves ahora coinciden con su índice.',
      },
    },
  },
]
