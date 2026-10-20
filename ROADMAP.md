# Roadmap — Qdrant MCP

Servidor MCP que expone **toda la superficie útil de la API de Qdrant** (colecciones,
points, búsqueda, indexing, snapshots, observabilidad), no solo `store`/`find`
como el servidor oficial (`qdrant/mcp-server-qdrant`, 2 tools). No cubre administración
de cluster distribuido (Fase 5, descartada — ver más abajo): requiere Qdrant distribuido y
su funcionalidad más relevante (resharding real) es exclusiva de Qdrant Cloud. Sí cubre la
administración que funciona en un solo nodo (aliases, introspección — Fase 12).

**Posicionamiento (decidido 2026-10-20):** proyecto de portfolio dirigido a quien evalúe el
trabajo (reclutadores, equipos técnicos), no un servicio. El repo publica código, paquete e
imagen; **no opera ninguna instancia pública** ni aloja datos de terceros.

## Principios (no negociables)

1. **Wrapper puro sobre Qdrant, no un RAG.** El servidor nunca genera embeddings, nunca
   parsea documentos, nunca decide chunking. Recibe y devuelve vectores/payloads tal
   cual. Esto es lo que lo diferencia a propósito del proyecto anterior
   (`QdrantMCP_RAG-Build`) — de ahí no se porta código, solo sirve como referencia de
   qué NO volver a mezclar en este repo.
2. **Cada feature vive en su rama**, se cierra con PR + CI en verde, y no se abre la
   siguiente fase hasta cerrar la anterior.
3. **Cobertura antes que atajos.** El catálogo de tools de este roadmap está sacado del
   índice oficial de la API de Qdrant (`api.qdrant.tech`, comprobado 2026-08-26), no de
   memoria — si Qdrant añade/renombra endpoints, el roadmap se actualiza, no se inventa.
4. **Servidor MCP puro, no servicio.** Nada de multi-tenancy, instancias públicas ni
   infraestructura propia que mantener. Quien quiera exponerlo por red se autoaloja
   `streamable-http` con su secreto compartido; el proyecto no lo opera por nadie.

## Decisiones de arquitectura

| Área | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| SDK MCP | paquete oficial `mcp`, `MCPServer` (sucesor de `FastMCP` desde `mcp>=2.0`, protocolo stateless) — no confundir con el paquete de terceros `fastmcp`; fijar versión exacta en PyPI al bootstrapear (comprobado 2026-08-30: `mcp` v2 renombró `FastMCP`→`MCPServer`); `protocolVersion` objetivo `2026-07-28` o posterior (modo stateless, `server/discover` obligatorio) |
| Cliente Qdrant | `qdrant-client`, `AsyncQdrantClient`, instancia única compartida con **timeout explícito** y **retries con backoff vía `tenacity`** (el propio `qdrant-client` solo expone `timeout`, no retry nativo) configurados desde el arranque — nunca timeout infinito por defecto |
| Superficie MCP | Todo expuesto como `tools` (sin `resources`) — un único patrón de diseño en todas las fases, menos decisiones por endpoint. Revisable en la Fase 7 si para entonces hay un caso de uso concreto que lo justifique |
| Licencia | MIT |
| Paquete PyPI | `mcp-qdrant` — `qdrant-mcp` y `qdrant-mcp-server` ya están ocupados por proyectos de terceros no relacionados (comprobado en PyPI 2026-08-27), fijado ahora para no rehacer `pyproject.toml`/imports en la Fase 7 |
| Gestión de deps | `uv` |
| Transporte | `stdio` por defecto (Claude Desktop/Code); `streamable-http` opcional para uso remoto, protegido con un secreto compartido por variable de entorno — sin OAuth ni multi-usuario, no hay ese caso de uso |
| Config | variables de entorno: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_LOCAL_PATH`, `QDRANT_MCP_READ_ONLY`, `QDRANT_MCP_TRANSPORT`, `QDRANT_MCP_TOOLSETS` (lista de grupos de tools a registrar, p.ej. `core,search`; por defecto solo `core`, el resto es opt-in explícito para no exponer de golpe ~70 tools solapadas) — sin perfiles YAML, eso era complejidad del RAG-build |
| Validación | Pydantic en cada input de tool, errores estructurados (nunca `except` mudo) |
| Tool annotations | Cada tool declara `readOnlyHint`/`destructiveHint`/`idempotentHint` desde que se registra (Fase 1 en adelante) — habilita autoaprobación segura en el cliente, no se deja para el hardening de la Fase 7 |
| Testing | `pytest` (unit con client mockeado + integración contra Qdrant real vía Docker, versión mínima soportada fijada en CI), `ruff`, `mypy`, `pre-commit` |
| CI | GitHub Actions: lint + typecheck + tests en cada PR |
| Doc de tools | Generada automáticamente desde los schemas Pydantic (script + check en CI) a partir de la Fase 7 — no se mantiene a mano |
| Landing page | Fase 9 (primera versión) y Fase 16 (rediseño técnico para reclutadores). Vive en `/website`, fuera del paquete Python que se publica en PyPI/Docker. Escaparate técnico, no página de un servicio |

## Flujo de Git

- `main` protegida, solo se actualiza vía PR con CI en verde.
- Rama por feature: `feat/<slug>` (nombres exactos abajo, uno por fase o sub-bloque).
  `fix/<slug>`, `docs/<slug>`, `chore/<slug>` para el resto.
- Commits en inglés, imperativo, [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Squash merge a `main` → 1 commit por feature en el log.
- Tag semver (`vX.Y.Z`) por release, `CHANGELOG.md` en formato Keep a Changelog.

**Definition of Done por rama:**
1. Tools registradas + schema Pydantic validado + annotations MCP
   (`readOnlyHint`/`destructiveHint`/`idempotentHint`) + toolset asignado.
2. Tests unitarios (mock) y, si la tool muta estado, al menos un test de integración
   contra el Qdrant real de CI (no basta con el mock).
3. `ruff check`, `mypy`, `pytest` en verde.
4. Tabla de tools en README actualizada (manual hasta la Fase 7; desde la Fase 7,
   generada automáticamente y verificada en CI — ver más abajo).
5. `CHANGELOG.md` actualizado.
6. Sin `TODO`, sin credenciales, sin código muerto.

## Fases

### Fase 0 — `feat/project-scaffold` → v0.0.1 ✅ Cerrada (mergeada en `main`, tag `v0.0.1`)

- Repo, `pyproject.toml` (nombre de paquete `mcp-qdrant`, build backend excluye
  `/website` del paquete cuando exista), entrypoint CLI, esqueleto `MCPServer` vacío.
- `ruff` + `mypy` + `pytest` + `pre-commit`, GitHub Actions (lint + typecheck + tests).
- Conexión a Qdrant (`QDRANT_URL`/`QDRANT_API_KEY`/`QDRANT_LOCAL_PATH`) vía el
  `AsyncQdrantClient` compartido descrito en la tabla de arquitectura.
- Mecanismo de registro de tools por *toolset* (`core`, `search`, `payload`,
  `snapshots`, `admin`, `observability` — uno por Fase 1-6), filtrable con
  `QDRANT_MCP_TOOLSETS`. El scaffold solo define el mecanismo; cada fase registra
  su propio grupo al añadir sus tools — evita rediseñar esto cuando el catálogo
  crezca a 60-70 tools en la Fase 6.
- Guardarraíl mínimo de `QDRANT_MCP_READ_ONLY`: decorador que bloquea el registro/
  ejecución de toda tool anotada `destructiveHint=true` cuando la variable está
  activa. El scaffold no tiene tools mutantes propias, pero el mecanismo queda listo
  para que la Fase 1 en adelante lo herede desde el primer commit — no se deja para
  la Fase 7.
- Logging configurado a **stderr** desde el arranque (nunca stdout con transporte
  `stdio`, rompe el framing JSON-RPC) — con check en CI que falla si algo escribe a
  stdout fuera del framing MCP.
- `qdrant_health_check`: tool de humo que valida el pipeline end-to-end.
- CI fija una **versión mínima de Qdrant server soportada**, levantada como servicio
  Docker en el propio workflow — la misma imagen se reutiliza en las fases posteriores
  para los tests de integración.
- `LICENSE` (MIT), `.github/dependabot.yml`, plantillas mínimas de issue/PR.

### Fase 1 — `feat/core-collections-points` → v0.1.0 (MVP real) ✅ Cerrada (mergeada en `main` vía PR #2, tag `v0.1.0`)
CRUD completo de colecciones y points + búsqueda vectorial básica. Con esto ya es un MCP
usable de punta a punta y muy por encima del oficial.

- `qdrant_collection_create`, `_list`, `_info`, `_update`, `_delete`, `_exists`
- `qdrant_points_upsert`, `_get`, `_delete`, `_scroll`, `_count`
- `qdrant_query` (Query points: vector + filtro + límite, API unificada moderna).
  El schema Pydantic ships solo con lo anterior en esta fase — `prefetch`/`fusion`
  (hybrid search) llegan en la Fase 2, no hace falta diseñarlos ya.
- Descripciones de tools ricas + ejemplos desde esta fase (no se pospone a la
  Fase 7): con `query`/`search`/`recommend`/`discover` solapándose a partir de la
  Fase 2, el LLM necesita desambiguación desde el MVP.

### Fase 2 — `feat/search-advanced` → v0.2.0 ✅ Cerrada
Todo lo demás bajo "Search" en la API de Qdrant.

- `qdrant_query` (heredada de la Fase 1, toolset `core` sin cambios) se extiende aquí
  con `prefetch` + `fusion` (RRF/DBSF) para hybrid search, y `using`/`lookup_from` para
  vectores nombrados y búsquedas cruzando colecciones
- `qdrant_query_batch`, `qdrant_query_groups` (toolset `search`, mismas formas de query
  que `qdrant_query`)
- `qdrant_recommend`, `qdrant_recommend_batch`, `qdrant_recommend_groups`
- `qdrant_discover`, `qdrant_discover_batch`
- `qdrant_distance_matrix_pairs`, `qdrant_distance_matrix_offsets`

**Hallazgo verificado durante la Fase 2** (introspección directa de
`qdrant-client==1.19.0`, el pinneado en `pyproject.toml`, no de la doc HTTP de Qdrant
que usó la redacción original de este roadmap): `AsyncQdrantClient` en esta versión no
expone `search`, `search_batch`, `search_groups`, `recommend`, `recommend_batch`,
`recommend_groups`, `discover` ni `discover_batch` — ni siquiera en su capa REST de
bajo nivel (`qdrant_client.http.api.search_api` solo tiene `query_points`,
`query_batch_points`, `query_points_groups`, `search_matrix_pairs`,
`search_matrix_offsets`). Todo quedó consolidado en la Query API unificada.
Consecuencia: **`qdrant_search`/`_batch`/`_groups` (planeadas originalmente como
"legacy") se eliminan del catálogo** — duplicarían `qdrant_query` sin ninguna
capacidad real detrás, y envolverlas exigiría saltarse el SDK pinneado con HTTP
crudo, contra la decisión de arquitectura de la Fase 0. `qdrant_recommend`/`_batch`/
`_groups` y `qdrant_discover`/`_batch` no se ven afectadas: son query types reales
(`RecommendQuery`/`DiscoverQuery`) construidos sobre `query_points`.

### Fase 3 — `feat/payload-indexing-vectors` → v0.3.0 ✅ Cerrada
Payload, indexing y vectores nombrados — extiende los schemas de
`qdrant_collection_create`/`_update` (Fase 1, toolset `core` sin cambios) con las
opciones avanzadas de configuración de colección que la Fase 1 dejó fuera a propósito:

- `quantization_config` (scalar/product/binary)
- `sparse_vectors` (hybrid search de texto)
- multivectores (`comparator: max_sim`, estilo ColBERT) — vive dentro de la config de
  cada vector nombrado en `vectors`, no es un parámetro aparte
- `strict_mode_config` y metadata de colección (key-value)

Y el resto de tools de payload/indexing/vectores (toolset nuevo `payload`):

- `qdrant_payload_set`, `_overwrite`, `_delete`, `_clear`, `_facet`
- `qdrant_payload_index_create`, `_delete`
- `qdrant_points_batch_update` (operaciones múltiples en orden; **no** atómico — corregido en la Fase 15b)
- `qdrant_vectors_update`, `_delete` (named vectors sobre points existentes)
- `qdrant_collection_vector_create`, `_delete` (named vectors a nivel colección)

**Hallazgo verificado durante la Fase 3** (probado en vivo contra Qdrant real, no
asumido de la documentación): existen **dos mecanismos distintos** para vectores
nombrados, no uno. `qdrant_collection_update` (`quantization_config`/
`sparse_vectors_config`) solo **ajusta** un vector nombrado que ya existe — pedirle que
añada uno nuevo falla con el propio error de Qdrant "Not existing vector name". El
único mecanismo real para **añadir o quitar** un vector nombrado (denso o disperso) en
una colección que ya tiene puntos es `create_vector_name`/`delete_vector_name`
(`qdrant_collection_vector_create`/`_delete`) — y ese endpoint **no existe** en Qdrant
`v1.13.6` ni `v1.15.1` (404 verificado con ambos), solo a partir de una versión más
reciente (funciona en `v1.19.0`). Consecuencia: el **mínimo de Qdrant server soportado
por este proyecto sube a `v1.19.0`** desde esta fase — CI pinea esa versión, y el
resto de tests de integración de Fases 1-2 se re-verificaron sin cambios contra ella
(de paso, desaparece el aviso de incompatibilidad de versión cliente/servidor
documentado desde la Fase 0).

### Fase 4 — `feat/snapshots` → v0.4.0 ✅ Cerrada
Backup/restore, a nivel colección y storage completo.

- `qdrant_snapshot_create`, `_list`, `_delete`, `_recover`, `_download` (por colección)
- `qdrant_storage_snapshot_create`, `_list`, `_delete`, `_download`

**Hallazgo verificado durante la Fase 4** (probado en vivo, no asumido): el único
método que ofrece `qdrant-client==1.19.0` para "descargar" un snapshot
(`client.http.snapshots_api.get_snapshot`/`get_full_snapshot`, ni siquiera expuesto en
el cliente de alto nivel) siempre intenta parsear la respuesta como JSON — contra un
snapshot real (binario) revienta con `UnicodeDecodeError`. Tampoco tendría sentido
meter un fichero de gigabytes en la respuesta de un tool MCP. Consecuencia:
`qdrant_snapshot_download`/`qdrant_storage_snapshot_download` no devuelven bytes —
confirman que el snapshot existe (vía `list_snapshots`/`list_full_snapshots`, dentro
del SDK) y devuelven su descriptor más la URL REST donde se sirve; quien llama se lo
descarga por su cuenta. Verificado también en vivo que esa URL es directamente
reutilizable como `location` de `qdrant_snapshot_recover` (ciclo completo probado:
crear → descargar URL → borrar un punto → recuperar → el punto vuelve), siempre que esa
URL la pueda alcanzar el propio servidor Qdrant (no necesariamente quien llama al MCP —
matiz relevante si Qdrant corre detrás de un remapeo de puertos Docker o un proxy). No
existe `qdrant_storage_snapshot_recover`: restaurar el storage completo se hace con el
servidor parado, no es una llamada en caliente.

### Fase 5 — `feat/aliases-cluster-admin` ❌ Descartada
Se descarta: la mayoría de sus tools (aliases, estado de cluster, rebalanceo de
shards, snapshots por shard) solo tienen sentido con un Qdrant en modo distribuido
real, y el resharding —lo que justificaba el nombre "cluster-admin"— es exclusivo de
Qdrant Cloud (verificado en la Fase 0: el endpoint existe en self-hosted pero no
reequilibra nada de verdad). No aporta valor para el caso de uso real de este
proyecto (despliegue de un solo nodo). Los números de fase/versión posteriores
(Fase 6 / v0.6.0 en adelante) no se renumeran.

### Fase 6 — `feat/service-observability` → v0.6.0 ✅ Cerrada

- `qdrant_telemetry`, `qdrant_metrics_prometheus`
- `qdrant_quotas_get`, `_set`
- `qdrant_issues_list`, `_clear` (API Beta de Qdrant — documentar en la tool que puede
  cambiar sin previo aviso)

**Hallazgos verificados durante la Fase 6** (probado en vivo, no asumido):
- `qdrant_write_protection_get`/`_set` **se eliminan del catálogo**: ni el cliente de
  alto nivel ni ninguna de sus 10 clases de API REST de bajo nivel tienen nada
  relacionado con locks/write-protection/read-only a nivel servidor en
  `qdrant-client==1.19.0` — a diferencia de la Fase 2 (`search` seguía viva,
  consolidada en `query_points`), aquí no hay ningún concepto sustituto.
- `qdrant_metrics_prometheus` no puede traer el contenido: `client.http.service_api.metrics()`
  intenta `response.json()` sin mirar el tipo real, y revienta contra el texto plano
  formato Prometheus que devuelve de verdad. La tool devuelve la URL de scraping
  (`{QDRANT_URL}/metrics`) en vez de las métricas — mismo patrón que la descarga de
  snapshots de la Fase 4.
- Esta es la primera fase cuyo mecanismo principal pasa por la capa REST de bajo nivel
  (`client.http.<api>_api.<método>`) en vez del cliente de alto nivel: nada de
  telemetry/quotas/issues está envuelto ahí (la única excepción,
  `client.cluster_telemetry()`, es telemetría de cluster distribuido — fuera de
  alcance, coherente con haber descartado la Fase 5). `call_qdrant` sigue funcionando
  igual sin cambios; solo hay que desenvolver `.result` del sobre de respuesta a mano.

### Fase 7 — `feat/packaging-and-dx` → v1.0.0 ✅ Cerrada
Hardening y distribución, no tools nuevas. (El guardarraíl `QDRANT_MCP_READ_ONLY` y
las descripciones ricas de tools ya se resolvieron en Fase 0 y Fase 1
respectivamente — no se repiten aquí.)

- Publicación en PyPI, imagen Docker, manifest para Claude Desktop (`.mcpb`).
- Tabla de tools del README pasa a generarse automáticamente desde el registro vivo de
  tools (`scripts/gen_tools_doc.py`, vía `list_tools()` — la misma vista que ve un
  cliente MCP real, no un re-parseo manual de los schemas Pydantic + check en CI que
  falla si el README diverge) — sustituye el mantenimiento manual de las fases
  anteriores.
- README con guía de configuración completa
  (`claude_desktop_config.json` / Claude Code `.mcp.json`).
- Checklist de lanzamiento de v1.0.0 (visibilidad, no DoD de código): envío del server a
  `modelcontextprotocol/servers`, Smithery y demás registries de MCP relevantes.

**Añadido no previsto en el roadmap original, confirmado en vivo contra una cuenta real
de Claude.ai**: el transporte `streamable-http` corría sin ninguna autenticación — se
añade `QDRANT_MCP_SHARED_SECRET` (obligatorio si `QDRANT_MCP_TRANSPORT=streamable-http`,
el arranque falla alto si falta) y un middleware que exige `Authorization: Bearer
<secreto>`. Verificado en vivo con un túnel público real + el panel de "Añadir
conector personalizado" de Claude.ai: la cabecera `Authorization` es una de las dos que
Claude.ai permite sin aprobación manual de Anthropic; el ciclo completo (levantar en
`streamable-http`, sin cabecera → 401, con cabecera correcta → 200) se probó contra un
servidor real, en local y en Docker.

**Hallazgo sobre `.mcpb`**: el spec de `modelcontextprotocol/mcpb` define un tipo de
servidor `"uv"` (manifest v0.4+) pensado exactamente para proyectos `uv` — el propio
`uv` resuelve las dependencias del `pyproject.toml` en la máquina del usuario sin que
haga falta vendorizar nada dentro del bundle, y sin que el usuario necesite tener Python
ya instalado (uv se encarga). Bundle final validado con el CLI oficial
(`mcpb validate`/`mcpb pack`): ~136 KB, dentro del rango que promete el spec para este
tipo de servidor.

**Checklist de lanzamiento v1.0.0** (visibilidad — acciones externas, no automatizables
desde aquí):
- [x] Dar de alta "Trusted Publishing" para `mcp-qdrant` en pypi.org.
- [x] Crear el GitHub Environment `pypi` en la configuración del repo.
- [x] Empujar el tag `v1.0.0` — verificado en vivo: `mcp-qdrant==1.0.0` publicado en
      PyPI, `ghcr.io/avaazquezz/qdrant-mcp:1.0.0` publicado y descargable, Release
      `v1.0.0` creada con `mcp-qdrant.mcpb` adjunto.
- [x] **Corrección sobre el roadmap original**: `modelcontextprotocol/servers` ya no
      acepta servers de comunidad por PR — su propio README redirige al
      [MCP Registry](https://registry.modelcontextprotocol.io) oficial. Publicado ahí
      en la práctica: release `v1.0.1` con el marcador `mcp-name:
      io.github.avaazquezz/mcp-qdrant` en el README (necesario porque `v1.0.0` ya
      estaba en PyPI sin él), login con `mcp-publisher login github` (device-code) y
      `mcp-publisher publish` — verificado que aparece buscando
      `io.github.avaazquezz/mcp-qdrant` en `registry.modelcontextprotocol.io`.
- [ ] **Bloqueado, no por nosotros**: Smithery. Cuenta creada (namespace
      `adrianvazvaz-2117`) y CLI autenticado, pero `smithery mcp publish
      <bundle>.mcpb` falla con `"Could not determine bundle runtime from manifest"`
      — verificado leyendo el propio código del CLI (`smithery` npm, v1.2.0): solo
      reconoce `server.type` `"python"`/`"node"`/`"binary"`, no el tipo `"uv"` (MCPB
      spec v0.4+) que usa nuestro bundle real. Retomar cuando Smithery actualice su
      CLI, o si se decide construir un `.mcpb` alternativo vendorizado solo para esto
      (no se ha hecho: reintroduciría la fragilidad multi-plataforma que el tipo
      `"uv"` evita a propósito).

### Fase 8 — `feat/byo-public-instance` → v1.1.0 ⛔ Revertida en la Fase 10 (v2.0.0)
> **Histórico.** Esta fase se cerró y se publicó (v1.1.0/v1.1.1), y después se revirtió
> entera por el principio nº4 (servidor MCP puro, no servicio) — ver Fase 10. El texto de
> abajo se conserva porque los hallazgos (cabeceras preaprobadas de Claude.ai, SSRF,
> `contextvars`) siguen siendo ciertos, no porque el código exista.

Segundo modo de despliegue, sin tools nuevas: un `streamable-http` público donde el
operador no aloja ningún dato. Motivación: abrir el servidor a que lo use cualquiera
("como un MCP cualquiera") sin asumir el almacenamiento de terceros ni construir un
sistema de altas/claves por usuario.

**Decisión** (descartando la alternativa de una base de datos compartida con
namespacing por usuario): cada llamada trae su propio Qdrant (Qdrant Cloud propio, o el
de su empresa) vía cabeceras — sin base de datos de reserva. El aislamiento entre
usuarios es automático (cada uno habla con una BBDD distinta), así que no hace falta
namespacing de colecciones, ni registro de usuarios, ni claves emitidas por nosotros.

**Verificado en el código, no asumido**: el `AsyncQdrantClient` de cada tool se resuelve
por atributo en tiempo de llamada (dentro de los `lambda` de `call_qdrant`), no en el
registro — permite sustituirlo por un proxy (`BYOQdrantClientProxy`, en
`byo_qdrant.py`) que resuelve el cliente real por petición vía `contextvars`, sin tocar
ninguno de los 8 ficheros de tools. El SDK (`mcp==2.1.1`) propaga explícitamente esos
`contextvars` a través de sus `anyio` task boundaries — mecanismo real, no supuesto.

**Hallazgo crítico verificado en vivo contra Claude.ai**: un nombre de cabecera
personalizado (`X-Qdrant-Url`) no se puede usar — el propio panel de "Añadir conector
personalizado" avisa de que los nombres de cabecera a medida necesitan aprobación
manual de Anthropic, y un nombre no aprobado da error al añadir el conector. Por eso el
diseño reutiliza dos cabeceras ya preaprobadas con un significado distinto al de su
nombre: `Authorization` lleva la URL del Qdrant del usuario (valor literal, sin
`Bearer` forzado), `x-api-key` (opcional) lleva su API key.

**SSRF, no opcional**: el servidor conecta a una URL que aporta un desconocido, desde
un host que también aloja otros proyectos en redes Docker internas — `ssrf_guard.py`
rechaza cualquier URL que resuelva a una dirección privada/loopback/link-local
(`ipaddress.is_private` cubre RFC1918, loopback, link-local incl. el IP de metadatos
de nube, y las variantes IPv6), re-resolviendo en cada petición para no dejar hueco a
DNS rebinding.

Desplegado inicialmente como segundo servicio en paralelo al personal
(`mcp-qdrant-public.vazquezlabs.com`). Decisión posterior del propietario: el proyecto
pasa a ser **únicamente** la instancia BYO — se desmontó la instancia personal
(contenedor, Qdrant propia y su volumen de datos, sin colecciones que perder) y el
servicio BYO se movió al dominio principal, ahora liberado: `mcp-qdrant.vazquezlabs.com`,
sin Qdrant propio (`QDRANT_MCP_BYO=1`, sin `QDRANT_URL`, sin `QDRANT_MCP_SHARED_SECRET`).
El código de la instancia personal (secreto compartido + Qdrant fijo) permanece en el
repo sin cambios — sigue siendo un modo válido para quien se autoaloje el proyecto con
su propia base de datos; simplemente ya no es el que corre en este servidor.

### Fase 9 — `feat/landing-page` (post v1.0.0, sin bump de semver del paquete) — primera versión; rehecha en la Fase 16
Landing de marketing del producto. Vive en `/website`, build independiente del paquete
Python, desplegada en infra propia (Hetzner + Traefik) siguiendo el mismo patrón que el
resto de proyectos. Se construye al final, con el producto ya cerrado, para no rehacer
copy ni capturas cuando cambie el alcance real.

Contenido:

- Gancho principal: comparativa directa "server oficial: 2 tools" vs. la cobertura real
  de este server, con el número de tools contado al cerrar la Fase 7 (no una cifra
  provisional).
- Explorador interactivo del catálogo de tools, generado desde el mismo script de la
  Fase 7 — no se mantiene a mano por segunda vez.
- Diagrama de arquitectura que comunique el principio nº1 del roadmap: wrapper puro,
  no RAG.
- Comando de instalación con botón "copiar" para `claude_desktop_config.json` /
  Claude Code `.mcp.json`.
- Animación con GSAP/transiciones Vue + assets generados con Higgsfield, vía la skill
  `landing-page-motion`.

Huecos a decidir cuando se aborde la fase (no ahora): dominio a usar, y si el copy
final incluye alguna métrica de adopción (stars, downloads) o se lanza sin ella.

### Fase 10 — `refactor/pure-mcp` → v2.0.0 ✅ Cerrada (PR #31, tag `v2.0.0` publicado en PyPI/GHCR/`.mcpb`); acciones externas pendientes
Servidor MCP puro (principio nº4). Se revierte la Fase 8 entera; **breaking** por semver,
porque `QDRANT_MCP_BYO` salió publicado en v1.1.0.

- Se eliminan `byo_auth.py`, `byo_qdrant.py`, `qdrant_client_cache.py`, `ssrf_guard.py`, sus
  tests, y el cableado en `cli.py`/`server.py`/`config.py`/`tools/errors.py`
  (`NoQdrantClientError`). Se **conserva** `streamable-http` + `QDRANT_MCP_SHARED_SECRET`
  (obligatorio siempre, sin la excepción BYO) y la imagen Docker.
- `QDRANT_MCP_BYO` con valor verdadero **falla al arrancar** con un error explícito en vez de
  ignorarse: un despliegue v1.1.x con la variable olvidada arrancaría en un modo distinto del
  que su operador cree.
- README sin la sección BYO, ni el SSRF guard en Seguridad. CHANGELOG `2.0.0`.

**Acciones externas** (no automatizables desde el repo, a cargo del propietario):
- [ ] Desmontar la instancia pública `mcp-qdrant.vazquezlabs.com` (contenedor, router
      Traefik, registro DNS).
- [ ] Tag `v2.0.0` → publica PyPI/GHCR/`.mcpb`; reeditar la entrada del MCP Registry
      (`mcp-publisher publish`) para que deje de describir el modo BYO.
- [ ] La landing desplegada sigue anunciando la instancia BYO hasta la Fase 16.

### Fase 11 — `fix/sparse-multivector-io` → v2.1.0 ✅ Cerrada (PR #32, tag `v2.1.0`)
Arregla dos huecos que dejan inservible el hybrid search de la Fase 2. **Hallazgos
verificados en vivo** (2026-10-20, Qdrant `v1.19.0`, no asumidos):

- `qdrant_points_upsert` solo acepta `vector: list[float]`: una colección creada con
  `vectors`/`sparse_vectors` (Fase 3) **no se puede poblar** con la tool principal —
  `{"dense": [...], "sparse": {...}}` falla en la validación Pydantic; un `list[float]`
  suelto contra una colección con vectores con nombre falla en el servidor (`Not existing
  vector name`). El único camino hoy es `qdrant_points_batch_update`, que sí funciona
  (probado) pero un LLM no lo descubre solo.
- `VectorOrId = list[float] | int | str` no admite `SparseVector` ni multivectores: una
  query sparse se rechaza en el schema, y el ejemplo hybrid del docstring de `qdrant_query`
  (`"query_vector": [0.5, 0.5], "using": "sparse"`) falla en el servidor con `Conversion
  between sparse and regular vectors failed`. El servidor sí soporta dense+sparse con RRF
  (probado con el cliente crudo): el hueco es solo del schema de este proyecto. Los únicos
  tests con "sparse" en búsqueda son unitarios con cliente mockeado.

Trabajo:
- `PointInput.vector` pasa a aceptar el mismo tipo que `PointVectorInput` (`vectors.py`):
  `list[float] | list[list[float]] | dict[str, list[float] | SparseVector | list[list[float]]]`.
- `qdrant_points_upsert` gana `wait`, `update_mode` (`upsert`/`insert_only`/`update_only`) y
  `update_filter` (upserts condicionales) — presentes en la firma de `qdrant-client==1.19.x`.
- `VectorOrId` y `PrefetchInput.query_vector` aceptan `SparseVector` y `list[list[float]]`
  (un solo tipo compartido: arregla `qdrant_query`, `_batch`, `_groups`, `recommend*`,
  `discover*` de golpe).
- Docstring hybrid corregido + tests de integración reales: upsert dense+sparse+multivector,
  query sparse, hybrid RRF dense+sparse.

**Hallazgos verificados durante la Fase 11** (en vivo, `v1.19.0`):
- Semántica de las escrituras condicionales, comprobada y fijada en tests de integración:
  `insert_only` no pisa un id existente, `update_only` no crea uno nuevo, y `update_filter`
  solo sobrescribe puntos existentes cuyo payload actual cumple el filtro.
- Al ensanchar la unión con `list[list[float]]`, un `[]` empezó a validar como multivector
  vacío y llegaba a Qdrant (antes lo cortaba el `min_length` del vector denso). Lo detectó un
  test unitario; `VectorOrId` acota ahora ambas formas de lista y `[[]]`.

### Fase 12 — `feat/aliases-and-introspection` → v2.2.0 (toolset `admin`) ✅ Cerrada (PR #33, tag `v2.2.0`)
**Corrige una decisión de la Fase 5.** Allí los aliases se descartaron junto al cluster por
"solo tener sentido en modo distribuido"; verificado en vivo (2026-10-20, single-node
`v1.19.0`) que **no es cierto para aliases**: crear y listar un alias funciona. También
funcionan `collection_cluster_info` (shards locales, puntos, estado) y `get_optimizations`
(optimizaciones en curso/en cola/idle). Lo que **sigue descartado**: shard keys
(`PUT /collections/{c}/shards` → 405; `GET /cluster` → `disabled` fuera de modo cluster).

- `qdrant_alias_list`, `qdrant_collection_aliases`, `qdrant_alias_update` (lista de
  operaciones create/rename/delete — base del reindex sin downtime).
- `qdrant_collection_cluster_info`, `qdrant_collection_optimizations` ("¿ha terminado de
  indexar?", "¿por qué está en amarillo?").
- `qdrant_collection_create` gana `hnsw_config`, `optimizers_config`, `on_disk_payload`
  (hoy solo ajustables después con `_update`, y `on_disk_payload` no se puede fijar).
- El toolset `admin` deja de ser un nombre reservado vacío: README, `manifest.json` y el
  cableado de `server.py` se actualizan.

**Hallazgos verificados durante la Fase 12** (en vivo, single-node `v1.19.0`):
- **Un lote de operaciones de alias NO es atómico ante fallos.** El roadmap original (y mi
  primer borrador del docstring) asumían lo contrario; una petición con un `create_alias`
  válido seguido de otro sobre una colección inexistente falla, pero deja el primero
  aplicado. Se documenta en la tool y un test de integración lo fija (si Qdrant lo cambia,
  el test avisa). Consecuencia de diseño: cambiar un alias a otra colección se hace con un
  único `create_alias`, que es todo-o-nada por ser una sola operación.
- `create_alias` sobre un alias que ya existe lo **re-apunta** (devuelve `true`): no hace
  falta borrar y crear. Borrar un alias inexistente es un no-op; un alias no puede llamarse
  como una colección existente (409); borrar una colección borra sus aliases.
- Un alias vale como `collection_name` en cualquier operación (verificado con `retrieve`).
- `AsyncQdrantClient.get_optimizations` descarta el selector `with`, así que solo devuelve
  resumen y optimizaciones en curso; `queued`/`completed`/`idle_segments` solo salen por la
  capa REST (`client.http.collections_api`), que es la que usa la tool.

### Fase 13 — `feat/server-side-composites` → v2.3.0 (toolset `admin`; depende de la Fase 11) ✅ Cerrada (PR #34, tag `v2.3.0`)
Operaciones compuestas donde **los vectores no pasan por el contexto del LLM**. Código
determinista, sin embeddings: compatible con el principio nº1.

- `qdrant_collection_copy`: copia paginada y **reanudable** (devuelve `next_offset`; el LLM
  repite la llamada) de una colección a otra de la misma instancia, con filtro opcional y
  `batch_size`. Idempotente (usa upsert). Combinada con `qdrant_alias_update`: crear colección
  nueva con otra distancia/cuantización/HNSW → copiar → cambiar el alias.
- `qdrant_payload_schema_infer`: muestrea N puntos y devuelve, por clave de payload, tipos
  observados, si está indexada y, para campos con índice keyword, los valores más frecuentes
  (vía facet). Evita el fallo más común de un LLM con Qdrant: inventarse claves en los filtros.
- Decidido al abordar: `copy` copia como máximo `max_points` (1000 por defecto, tope 100 000)
  por llamada en lotes de `batch_size` (100, tope 1000); `schema_infer` muestrea 100 puntos
  (tope 1000) y devuelve como mucho 200 claves. `copy` exige que el destino exista, rechaza
  copiar una colección sobre sí misma (también vía alias) y, si un lote falla, el error dice
  cuántos puntos se copiaron y desde qué `offset` reanudar.

**Hallazgos verificados durante la Fase 13** (en vivo, `v1.19.0`):
- `scroll(with_vectors=True)` + `upsert` conserva dense, sparse y multivector sin
  conversión: el copy es un bucle de scroll y upsert, sin tipos especiales.
- `facet` solo funciona con índices `keyword`, `integer`, `uuid` y `bool`; con `float`,
  `datetime` y `text` responde 400 "No appropriate index for faceting". Por eso
  `top_values` se limita a esos cuatro tipos en vez de intentarlo y tragarse el error.
- El muestreo aleatorio (`SampleQuery`) funciona con vectores con nombre y con filtro. Las
  claves de `payload_schema` usan la sintaxis `a.b` y `a[].b`; `schema_infer` genera las
  mismas, para que lo que informa se pueda pegar tal cual en un filtro o un índice.

### Fase 14 — `feat/query-power` → v2.4.0 ✅ Cerrada (PR #35, tag `v2.4.0`)
`qdrant_query` expone hoy solo `Nearest` (vector literal o id) + `Fusion` (RRF/DBSF), con un
único nivel de prefetch. El modelo de `qdrant-client==1.19.x` (introspección directa) tiene
10 tipos de query y `query_points` acepta más parámetros de los que se pasan.

- Parámetros: `search_params` (`hnsw_ef`, `exact`, `quantization`, `indexed_only`, `acorn`),
  `score_threshold`, `offset`, `timeout`, `consistency`.
- Prefetch **anidado** (rerank multietapa) y `params`/`score_threshold` por etapa.
- Nuevos modos como argumento discriminado **dentro de `qdrant_query`** (no tools nuevas:
  más tools solapadas empeoran la elección del LLM): `formula` (boost de score por
  payload/geo/fecha, con `defaults`), `mmr` (diversidad), `order_by`, `sample` (aleatorio) y
  RRF con pesos. `RelevanceFeedbackQuery` y `ContextQuery`: solo si aparece un caso de uso
  concreto — decidir al abordar la fase.
- `qdrant_points_scroll` gana `order_by`.
- Cada modo se verifica en vivo antes de documentarlo (p. ej. si exige índice de payload).
- Decidido al abordar: los parámetros de ajuste (`search_params`, `score_threshold`, `offset`,
  `timeout_seconds`, `consistency`) se aceptan en **todas** las tools basadas en
  `query_points` (query, recommend, discover y sus variantes batch/groups), no solo en
  `qdrant_query`; los modos nuevos (`formula`, `mmr`, `order_by`, `sample`, RRF ponderado) en
  `qdrant_query`, `_batch` y `_groups`. `RelevanceFeedbackQuery` y `ContextQuery` **no** se
  implementan: no hay caso de uso concreto. El argumento se llama `timeout_seconds` (no
  `timeout`): lo exige ruff (ASYNC109) y además aclara que es un timeout del servidor.

**Hallazgos verificados durante la Fase 14** (en vivo, `v1.19.0`):
- **MMR no hace nada por defecto.** `candidates_limit` vale `limit`, así que con `limit` 2 el
  resultado es idéntico al de una query normal; hay que subirlo (con 10 sí promueve el punto
  disimilar). Además `offset` se aplica *dentro* de los `limit` resultados reordenados:
  `offset` 1 con `limit` 2 devuelve 1 punto y `offset` 2 devuelve vacío. Se documenta en la
  tool y un test lo fija.
- **`formula` exige `prefetch`** (`cannot apply Formula without prefetches`); una clave de
  payload ausente sin valor en `defaults` falla con un error claro. La gramática `Expression`
  pesa 35 KB de JSON Schema: se tipa de forma laxa (`dict | float | str`) y se valida en el
  servidor, y como un `ValidationError` de Pydantic sobre esa unión trae ~100 errores, se
  condensa en un único mensaje. Un `{}` valida como `Expression` (es un `Filter` vacío).
- **Pesos de RRF**: siguen el orden de las etapas (verificado con etapas disjuntas; con
  empates de score los resultados engañan) y su número debe coincidir con el de etapas.
- **`order_by`** exige un índice de payload de rango (float/integer/datetime): sin él responde
  400 "No range index". En scroll, `order_by` rechaza `offset` y `next_page_offset` es siempre
  `null`; se pagina con `start_from` (los empates en ese valor se repiten).
- `consistency` y `timeout` se aceptan en un nodo único (no tienen efecto observable).
- **Peso de los schemas**: la fase añade ~6,5 KB por tool de query; el catálogo completo pasa
  de 513 KB a 571 KB de `inputSchema` y `core` solo ya son 149 KB. No es nuevo (cada tool
  incluye su propia copia del schema de `Filter`, ~16 KB), pero queda como trabajo de la Fase 15.

### Fase 15 — `feat/response-limits` → v2.5.0 ✅ Cerrada (PR #36, tag `v2.5.0`)
Menos contexto y sin inundaciones accidentales. Medido antes de tocar nada (Fase 14): los
`inputSchema` que el cliente carga en el contexto del modelo eran **571 KB** para el catálogo
completo y **150 KB** para el toolset `core` por defecto.

- **`QDRANT_MCP_MAX_LIMIT`** (por defecto 1000; también en el formulario del `.mcpb`): tope de
  resultados por llamada. Se aplica a `limit` (query, recommend, discover, scroll, facet), a
  `limit × group_size` (tools `_groups`), a la suma de los items de un batch, a `sample × limit`
  (matrices de distancia) y al número de ids de `qdrant_points_get`. Una petición mayor se
  **rechaza con un error explícito** (dice qué era demasiado grande y que hay que paginar) en
  vez de recortarse en silencio: un recorte le daría al modelo menos resultados de los que cree
  haber recibido. Un valor inválido (0, negativo, no entero) falla al arrancar. Vive en
  `ToolRegistry.check_limit`, el mismo punto único donde ya se aplican toolsets y read-only.
  Cambio de comportamiento (peticiones de más de 1000 resultados dejan de funcionar), anotado
  en el CHANGELOG.
- **Schemas compactos** (`tools/schemas.py`): `Filter`, `SearchParams`, la lista de operaciones
  de `qdrant_points_batch_update` y los modelos de configuración (HNSW, optimizador, strict
  mode, cuantización, parámetros de vectores, tipos de índice de payload) anuncian un schema
  reducido con `pydantic.WithJsonSchema`. Solo cambia lo **anunciado**: la tool sigue recibiendo y
  validando el modelo real de Qdrant, así que lo que se acepta y se rechaza es idéntico. Para
  `Filter`, `SearchParams` y las operaciones, un resumen escrito a mano con la gramática de
  condiciones en la descripción; para los modelos de configuración, `slim_schema` parte del
  schema real, inlinea los `$ref` y quita solo la prosa (`title`/`description`/`default: null`),
  de modo que no hay texto a mano que se desfase. Resultado: **160 KB** el catálogo completo
  (−72 %) y **44 KB** `core` (−71 %).
- **Presupuesto en los tests**: `core`, catálogo completo y tool individual tienen un límite de
  bytes que falla si el schema vuelve a crecer; además, tests de paridad (el schema anunciado
  acepta y rechaza las mismas muestras que el modelo real, validado con `jsonschema`), de
  no-deriva (cada campo de condición, `match` y operación del `qdrant-client` instalado aparece en
  la gramática escrita a mano), y de que todos los `$ref` de todas las tools resuelven.

**Hallazgos verificados durante la Fase 15:**
- El peso estaba en la documentación embebida: `description` ≈ 36 % y los `$defs` de `Filter` y
  sus condiciones ≈ 250 KB repartidos por las tools (cada tool lleva su propia copia).
- **Primer borrador del schema de `Filter` incorrecto, corregido antes de publicar**: anunciaba
  `must`/`should`/`must_not` solo como lista, pero el modelo acepta *una lista o una única
  condición*; un cliente que validara contra el schema habría rechazado una llamada legal. Un test
  de paridad lo cubre ahora.
- El SDK de MCP ignora el metadato `Annotated` de un tipo de retorno `BaseModel` y no ofrece
  forma pública de fijar el `inputSchema` de una tool, así que la reducción va por tipo de
  parámetro. Los `outputSchema` (≈ 309 KB, sobre todo `CollectionInfo` y la telemetría) **no** se
  tocan: la API de mensajes de Anthropic solo recibe `name`, `description` e `input_schema` por
  herramienta, así que no cuestan contexto `[SIN VERIFICAR]` en cada cliente MCP; verificarlo
  antes de optimizarlos.
- `mypy` estricto exige `types-jsonschema` para los tests (se añade como dependencia de desarrollo);
  `jsonschema` en sí ya es dependencia dura de `mcp`.

### Fase 15b — `fix/review-hardening` → v2.6.0 ✅ Cerrada (PR #37, tag `v2.6.0`)
Revisión independiente del código de las Fases 11–15: un segundo lector sin contexto de mi
razonamiento, con la orden de **reproducir y no especular**. Cada hallazgo se volvió a reproducir
contra un Qdrant `v1.19.0` real antes de arreglarlo.

**Reproducidos y corregidos** (detalle en el CHANGELOG `2.6.0`):
1. Un `points_filter` sin condiciones (`{}`, `{"must": []}`, `{"should": []}`) **borraba la colección
   entera**: la guarda "exactamente un selector" lo aceptaba. Ahora se rechaza en delete, payload,
   vectors y dentro de `qdrant_points_batch_update`.
2. `qdrant_points_batch_update` se describía como **atómico** desde la Fase 3 y no lo es (una
   operación válida seguida de otra inválida deja la primera aplicada). Es la **misma clase de
   error que cometí con los aliases en la Fase 12**: afirmar una propiedad de Qdrant sin probarla.
3. `qdrant_payload_schema_infer`: abortaba con un índice entero `lookup: false`; imprimía claves que
   la sintaxis de filtros rechaza (espacios, `@`, `.`, `[]`, emojis) y no las casaba con su índice.
4. Claves desconocidas en inputs anidados se ignoraban en silencio: un prefetch con `filter` (el
   nombre de Qdrant) en vez de `query_filter` devolvía resultados **sin filtrar**.
5. Los schemas compactos de `Filter`/`SearchParams` (Fase 15) rechazaban `null` explícito e
   `idf: "global"` que el modelo real acepta.
6. `QDRANT_MCP_MAX_LIMIT` por debajo de 30 hacía fallar llamadas con solo los argumentos
   obligatorios; ahora el mínimo es 30, con un test que lo vigila.
7. Con `QDRANT_LOCAL_PATH`, dos tools de `admin` perdían su mensaje (`NotImplementedError`).
8. `qdrant_collection_copy`: `batch_size` hasta 1000 superaba el límite de 32 MiB de Qdrant con
   vectores de 3072 dimensiones; mensajes de error con repr de Python.

**Lección de método (ya en mi memoria de trabajo):** las afirmaciones sobre el comportamiento de
Qdrant que no he ejecutado son deuda. Este repo ya lo decía en el principio nº3; la revisión mostró
que lo incumplí dos veces. Las afirmaciones de comportamiento añadidas desde la Fase 12 (aliases,
MMR, `order_by` en scroll, fórmulas, pesos RRF, batch) ya tienen un test de integración que las
fija; las anteriores a la Fase 12 no se han revisado una a una.

**Anotado, no corregido** (no reproducido como defecto o sin impacto real hoy):
- `call_qdrant` reintenta con `tenacity` ante un fallo de transporte también en operaciones no
  idempotentes (p. ej. `rename_alias`): tras un timeout en el que el servidor sí aplicó la primera
  petición, el reintento fallaría con un error confuso. No corrompe datos; el arreglo sería no
  reintentar según `idempotent_hint`.
- Una etapa de `prefetch` sin `query` (válida en Qdrant: candidatos por filtro) y las etapas con
  `mmr`/`formula`/`order_by`/`sample`/`lookup_from` no se pueden expresar. Es una limitación de
  capacidad, no una regresión; ahora el error lo dice con claridad.

### Fase 16 — `feat/landing-technical` (sin bump de semver del paquete) ✅ Cerrada
Rediseño completo de `/website` (decidido 2026-10-20): de landing de un servicio a
**landing técnica para quien evalúa el proyecto** (reclutadores/equipos técnicos). Debe
explicar cómo funciona el proyecto de forma completa, fácil, interactiva y muy animada.

- **Fuera:** todo lo que venda o conecte con la instancia pública/BYO (copy, comando de
  conexión remota, enlaces al dominio de la instancia); `app.vue`, `InstallPaths.vue`,
  `robots.txt` y `sitemap.xml` hoy la mencionan.
- **Dentro:** documentación interactiva del catálogo de tools (generada desde el registro
  vivo, como `scripts/gen_tools_json.py`, nunca a mano); casos de uso reales encadenando
  tools (hybrid search, reindex sin downtime con copy + alias, auditoría de payload);
  arquitectura de integración (cliente MCP → `ToolRegistry` como punto único de toolsets y
  read-only → `call_qdrant` con retry → Qdrant); decisiones y hallazgos verificados (el
  propio ROADMAP es el material); CI/tests/cobertura como señales de calidad.
- Método: skill `landing-page-motion` — discovery y brief cerrados **antes** de construir;
  GSAP + Lenis sobre Nuxt, respetando `prefers-reduced-motion`, Core Web Vitals y
  accesibilidad.
- Operativa: siempre vía el contenedor Docker `qdrant-mcp-website` (nunca `npm run dev`),
  `npm install --legacy-peer-deps`.
- El brief puede abrirse ya; el copy final de casos de uso espera a la Fase 13 para mostrar
  las tools de reindex.

**Resultado** (✅ Cerrada, sin tag: no cambia el paquete):
- Concepto «el instrumento que mide»: una hoja de datos viva donde cada cifra sale del repo.
  Bilingüe EN `/` y ES `/es/` (prerender estático), CTA único = abrir el repositorio.
- **Nada a mano.** `scripts/gen_site_stats.py` (versión, tools, tests, KB de schemas, releases) y
  `scripts/record_scenarios.py` (ejecuta tools reales contra un Qdrant real y graba cada llamada y
  respuesta) generan los JSON que consume la web; ambos tienen `--check` en CI. La bitácora de
  ingeniería enlaza PRs y versiones reales.
- Secciones: hero con campo vectorial (distancias calculadas en el navegador), banda de cifras,
  método, arquitectura con el paquete JSON-RPC real viajando por los cinco saltos (pin solo en
  escritorio), 4 escenarios reproducibles, explorador de las 56 tools, instalación con generador
  de `.mcp.json`, bitácora, calidad, FAQ, contacto.
- Medido en local (sin red, así que LCP es optimista): FCP 116 ms, LCP 1,0 s, CLS 0,025, sin tareas
  largas, ≤64 ms por interacción, 180 KB de JS comprimido. Contraste AA en todos los pares de
  texto. Probado a 375 px (se corrigieron un desbordamiento horizontal por columnas de rejilla
  implícitas y un solape en las tarjetas de arquitectura), con teclado (skip link, foco visible)
  y con `prefers-reduced-motion` simulado (sin pin, sin Lenis, todo el contenido visible).
- Dominio `https://mcp-qdrant.vazquezlabs.com` (convención del propietario: `proyecto.vazquezlabs.com`) en
  `nuxt.config.ts` (`siteUrl`): de ahí salen canonical, hreflang,
  `og:*`, `sitemap.xml` y `robots.txt` (rutas de servidor prerenderizadas), un único sitio donde vive
  el dominio; `NUXT_PUBLIC_SITE_URL` lo sobrescribe en build y vacío los omite.
- Pendiente fuera del repo: ese host lo ocupa todavía la instancia pública antigua (Fase 10):
  desmontarla y servir ahí la imagen nueva de la landing.

## Versionado

| Versión | Fase cerrada |
|---|---|
| v0.1.0 | 1 — MVP funcional |
| v0.2.0 | 2 — búsqueda avanzada |
| v0.3.0 | 3 — payload/indexing/vectores |
| v0.4.0 | 4 — snapshots |
| — | 5 — descartada (cluster/admin, requiere Qdrant distribuido; resharding real es Cloud-only) |
| v0.6.0 | 6 — observabilidad |
| v1.0.0 | 7 — endurecido, documentado, publicable |
| v1.1.0 | 8 — instancia pública "bring your own Qdrant" (revertida en v2.0.0) |
| — | 9 — landing page, sin versión de paquete, deploy propio (rehecha en la Fase 16) |
| v2.0.0 | 10 — servidor MCP puro, sin modo BYO (breaking) |
| v2.1.0 | 11 — escritura/consulta sparse y multivector |
| v2.2.0 | 12 — aliases e introspección (`admin`) |
| v2.3.0 | 13 — operaciones server-side: copy, schema infer (`admin`) |
| v2.4.0 | 14 — potencia de query |
| v2.5.0 | 15 — límites de respuesta y schemas compactos |
| v2.6.0 | 15b — revisión independiente: correcciones |
| — | 16 — landing técnica, sin versión de paquete |

---
*Catálogo de endpoints verificado contra `api.qdrant.tech/master/llms.txt` y el README de
`qdrant/mcp-server-qdrant` el 2026-08-26. Si Qdrant cambia su API, actualizar esta lista
antes de abrir la rama correspondiente, no asumir.*
