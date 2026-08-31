# Roadmap — Qdrant MCP

Servidor MCP que expone **toda la superficie útil de la API de Qdrant** (colecciones,
points, búsqueda, indexing, snapshots, observabilidad), no solo `store`/`find`
como el servidor oficial (`qdrant/mcp-server-qdrant`, 2 tools). No cubre administración
de cluster (Fase 5, descartada — ver más abajo): requiere Qdrant distribuido y su
funcionalidad más relevante (resharding real) es exclusiva de Qdrant Cloud.

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
| Landing page | Fase 9, tras v1.0.0. Vive en `/website`, fuera del paquete Python que se publica en PyPI/Docker. Desplegada en infra propia (Hetzner + Traefik). Dominio: pendiente de decidir al abordar la fase |

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
- `qdrant_points_batch_update` (operación atómica múltiple)
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

### Fase 8 — `feat/byo-public-instance` → v1.1.0 ✅ Cerrada
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

### Fase 9 — `feat/landing-page` (post v1.0.0, sin bump de semver del paquete)
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
| v1.1.0 | 8 — instancia pública "bring your own Qdrant" |
| — | 9 — landing page, sin versión de paquete, deploy propio |

---
*Catálogo de endpoints verificado contra `api.qdrant.tech/master/llms.txt` y el README de
`qdrant/mcp-server-qdrant` el 2026-08-26. Si Qdrant cambia su API, actualizar esta lista
antes de abrir la rama correspondiente, no asumir.*
