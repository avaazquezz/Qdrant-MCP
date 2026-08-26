# Roadmap — Qdrant MCP

Servidor MCP que expone **toda la superficie útil de la API de Qdrant** (colecciones,
points, búsqueda, indexing, snapshots, cluster, observabilidad), no solo `store`/`find`
como el servidor oficial (`qdrant/mcp-server-qdrant`, 2 tools).

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
| SDK MCP | paquete oficial `mcp` (`FastMCP`) — fijar versión exacta en PyPI al bootstrapear |
| Cliente Qdrant | `qdrant-client`, `AsyncQdrantClient`, instancia única compartida con **timeout explícito y retries con backoff** configurados desde el arranque — nunca timeout infinito por defecto |
| Superficie MCP | Todo expuesto como `tools` (sin `resources`) — un único patrón de diseño en todas las fases, menos decisiones por endpoint. Revisable en la Fase 7 si para entonces hay un caso de uso concreto que lo justifique |
| Licencia | MIT |
| Gestión de deps | `uv` |
| Transporte | `stdio` por defecto (Claude Desktop/Code); `streamable-http` opcional para uso remoto, protegido con un secreto compartido por variable de entorno — sin OAuth ni multi-usuario, no hay ese caso de uso |
| Config | variables de entorno: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_LOCAL_PATH`, `QDRANT_MCP_READ_ONLY`, `QDRANT_MCP_TRANSPORT` — sin perfiles YAML, eso era complejidad del RAG-build |
| Validación | Pydantic en cada input de tool, errores estructurados (nunca `except` mudo) |
| Testing | `pytest` (unit con client mockeado + integración contra Qdrant real vía Docker, versión mínima soportada fijada en CI), `ruff`, `mypy`, `pre-commit` |
| CI | GitHub Actions: lint + typecheck + tests en cada PR |
| Doc de tools | Generada automáticamente desde los schemas Pydantic (script + check en CI) a partir de la Fase 7 — no se mantiene a mano |
| Landing page | Fase 8, tras v1.0.0. Vive en `/website`, fuera del paquete Python que se publica en PyPI/Docker. Desplegada en infra propia (Hetzner + Traefik). Dominio: pendiente de decidir al abordar la fase |

## Flujo de Git

- `main` protegida, solo se actualiza vía PR con CI en verde.
- Rama por feature: `feat/<slug>` (nombres exactos abajo, uno por fase o sub-bloque).
  `fix/<slug>`, `docs/<slug>`, `chore/<slug>` para el resto.
- Commits en inglés, imperativo, [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Squash merge a `main` → 1 commit por feature en el log.
- Tag semver (`vX.Y.Z`) por release, `CHANGELOG.md` en formato Keep a Changelog.

**Definition of Done por rama:**
1. Tools registradas + schema Pydantic validado.
2. Tests unitarios (mock) y, si la tool muta estado, al menos un test de integración
   contra el Qdrant real de CI (no basta con el mock).
3. `ruff check`, `mypy`, `pytest` en verde.
4. Tabla de tools en README actualizada (manual hasta la Fase 7; desde la Fase 7,
   generada automáticamente y verificada en CI — ver más abajo).
5. `CHANGELOG.md` actualizado.
6. Sin `TODO`, sin credenciales, sin código muerto.

## Fases

### Fase 0 — `feat/project-scaffold` → v0.0.1

- Repo, `pyproject.toml` (build backend excluye `/website` del paquete cuando exista),
  entrypoint CLI, esqueleto `FastMCP` vacío.
- `ruff` + `mypy` + `pytest` + `pre-commit`, GitHub Actions (lint + typecheck + tests).
- Conexión a Qdrant (`QDRANT_URL`/`QDRANT_API_KEY`/`QDRANT_LOCAL_PATH`) vía el
  `AsyncQdrantClient` compartido descrito en la tabla de arquitectura.
- `qdrant_health_check`: tool de humo que valida el pipeline end-to-end.
- CI fija una **versión mínima de Qdrant server soportada**, levantada como servicio
  Docker en el propio workflow — la misma imagen se reutiliza en las fases posteriores
  para los tests de integración.
- `LICENSE` (MIT), `.github/dependabot.yml`, plantillas mínimas de issue/PR.

### Fase 1 — `feat/core-collections-points` → v0.1.0 (MVP real)
CRUD completo de colecciones y points + búsqueda vectorial básica. Con esto ya es un MCP
usable de punta a punta y muy por encima del oficial.

- `qdrant_collection_create`, `_list`, `_info`, `_update`, `_delete`, `_exists`
- `qdrant_points_upsert`, `_get`, `_delete`, `_scroll`, `_count`
- `qdrant_query` (Query points: vector + filtro + límite, API unificada moderna).
  El schema Pydantic ships solo con lo anterior en esta fase — `prefetch`/`fusion`
  (hybrid search) llegan en la Fase 2, no hace falta diseñarlos ya.

### Fase 2 — `feat/search-advanced` → v0.2.0
Todo lo demás bajo "Search" en la API de Qdrant.

- `qdrant_query_batch`, `qdrant_query_groups`
- `qdrant_query`/`_batch`/`_groups` (heredadas de la Fase 1) se extienden aquí con
  `prefetch` + `fusion` (RRF/DBSF) para hybrid search, y `using`/`lookup_from` para
  multivectores y búsquedas cruzando vectores nombrados
- `qdrant_search`, `qdrant_search_batch`, `qdrant_search_groups` (legacy, para clientes
  que aún no usan Query API)
- `qdrant_recommend`, `qdrant_recommend_batch`, `qdrant_recommend_groups`
- `qdrant_discover`, `qdrant_discover_batch`
- `qdrant_distance_matrix` (pairs/offsets)

### Fase 3 — `feat/payload-indexing-vectors` → v0.3.0
Payload, indexing y vectores nombrados — incluye extender los schemas de
`qdrant_collection_create`/`_update` (Fase 1) con las opciones avanzadas de
configuración de colección que la Fase 1 dejó fuera a propósito:

- `quantization_config` (scalar/product/binary)
- `sparse_vectors` (hybrid search de texto)
- multivectores (`comparator: max_sim`, estilo ColBERT)
- `strict_mode_config` y metadata de colección (key-value)

Y el resto de tools de payload/indexing:

- `qdrant_payload_set`, `_overwrite`, `_delete`, `_clear`, `_facet`
- `qdrant_payload_index_create`, `_delete`
- `qdrant_points_batch_update` (operación atómica múltiple)
- `qdrant_vectors_update`, `_delete` (named vectors sobre points existentes)
- `qdrant_collection_vector_create`, `_delete` (named vectors a nivel colección)

### Fase 4 — `feat/snapshots` → v0.4.0
Backup/restore, a nivel colección y storage completo.

- `qdrant_snapshot_create`, `_list`, `_delete`, `_recover`, `_download` (por colección)
- `qdrant_storage_snapshot_create`, `_list`, `_delete`, `_download`

### Fase 5 — `feat/aliases-cluster-admin` → v0.5.0 (marcar como avanzado/opcional)
Requiere Qdrant en modo distribuido para tener sentido pleno; documentar claramente que
algunas tools solo aplican con cluster real.

- `qdrant_alias_update` (create/rename/delete), `_list`, `_list_all`
- `qdrant_cluster_status`, `_info`, `_recover`, `_peer_remove`
- `qdrant_shard_key_create`, `_delete`, `_list`
- `qdrant_shard_snapshot_create`, `_list`, `_download`, `_delete`, `_recover`

**DoD específico de esta fase** (sustituye el punto 2 genérico): los tests de
integración corren contra un **cluster Qdrant multi-nodo levantado con
`docker-compose`**, no contra el nodo único de CI de las fases anteriores — documentar
en `docs/` cómo levantarlo en local.

### Fase 6 — `feat/service-observability` → v0.6.0

- `qdrant_telemetry`, `qdrant_metrics_prometheus`
- `qdrant_write_protection_get`, `_set`
- `qdrant_quotas_get`, `_set`
- `qdrant_issues_list`, `_clear` (API Beta de Qdrant — documentar en la tool que puede
  cambiar sin previo aviso)

### Fase 7 — `feat/packaging-and-dx` → v1.0.0
Hardening y distribución, no tools nuevas.

- Modo `QDRANT_MCP_READ_ONLY` global que bloquea toda tool mutante.
- Descripciones de tools ricas + ejemplos (afecta a qué tan bien las elige el LLM).
- Publicación en PyPI, imagen Docker, manifest para Claude Desktop (`.mcpb`).
- Tabla de tools del README pasa a generarse automáticamente desde los schemas
  Pydantic (`scripts/gen_tools_doc.py` + check en CI que falla si el README diverge) —
  sustituye el mantenimiento manual de las fases anteriores.
- README con guía de configuración completa
  (`claude_desktop_config.json` / Claude Code `.mcp.json`).
- Checklist de lanzamiento de v1.0.0 (visibilidad, no DoD de código): envío del server a
  `modelcontextprotocol/servers`, Smithery y demás registries de MCP relevantes.

### Fase 8 — `feat/landing-page` (post v1.0.0, sin bump de semver del paquete)
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
| v0.5.0 | 5 — cluster/admin (opcional según despliegue) |
| v0.6.0 | 6 — observabilidad |
| v1.0.0 | 7 — endurecido, documentado, publicable |
| — | 8 — landing page, sin versión de paquete, deploy propio |

---
*Catálogo de endpoints verificado contra `api.qdrant.tech/master/llms.txt` y el README de
`qdrant/mcp-server-qdrant` el 2026-08-26. Si Qdrant cambia su API, actualizar esta lista
antes de abrir la rama correspondiente, no asumir.*
