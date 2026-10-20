# Auditoría — OmniCAD

| Campo | Valor |
|---|---|
| **Auditor** | Agente IA con skill `vibe-coding-audit` (3 dominios en paralelo, consolidados) |
| **Fecha de auditoría** | 2026-10-14 |
| **Versión del código auditado** | commit `8241c2e` (main, post-tanda de bugs 2026-10-13/14) |
| **Stack detectado** | Python 3.12 + PySide6 6.12 + cadquery-ocp 8.0.1 (kernel OCC) + numpy/scipy + mcp 2.3.0; PyInstaller/Inno Setup para Windows, AppImage para Linux |
| **Tipo de proyecto** | App de escritorio CAD paramétrica (GPL-3.0) con servidor MCP y CLI para agentes; sin web, sin DB, sin usuarios remotos |
| **¿Llama LLMs? / ¿Usa MCP?** | No llama LLMs. **Expone** un servidor MCP propio (S-18 aplica a configs del repo) |
| **Modo de auditoría** | Exhaustivo (~93 checks; web/auth/RLS/LLM marcados N/A con justificación) |
| **Entorno de ejecución** | OpenCode con filesystem + comandos reales (greps, `pytest --collect-only`, `pip list --outdated`, lectura del SDK mcp del venv) |

---

## Resumen Ejecutivo

**No hay findings críticos**: ningún hallazgo permite daño inmediato a un usuario. El riesgo real de este proyecto es de **proceso**, no de código: la CI arma y **publica instaladores en cada tag sin correr ni un test** (`instaladores.yml`), así que un commit roto en main se convierte directo en un instalador roto público. Ese es el hallazgo que cambia decisiones.

El segundo: el servidor MCP en modo `--http` no exige token propio — cualquier proceso local del mismo usuario puede llamar `execute_code` (ejecución arbitraria de código) sin autenticación, a diferencia del puente de la app que sí lo exige con `secrets.compare_digest`. En una máquina mono-usuario el riesgo es acotado, pero el software se publica: cualquiera que lo tenga corriendo con `--http` queda expuesto a cualquier otro proceso de su sesión.

El tercero: permisos de CI amplios (`contents: write` global) y acciones de terceros sin pin a SHA. Todo lo demás es calidad de mantenimiento: archivos gigantes (14 superan 1000 líneas), complejidad >20 en 6 funciones, hot-paths O(n²) no fichados y deuda de tooling (sin coverage, sin type-checker, sin lockfile). La arquitectura, en cambio, está notablemente sana: la regla sin-Qt del núcleo se cumple al 100%, no hay código muerto, no hay secrets, la suite tiene 2459 tests con testing ofensivo real.

### Health Score

| Dominio | Score | Notas |
|---|---|---|
| Seguridad | 15/18 | 0 críticos, 1 alto (MCP --http), 2 bajos |
| QA / Testing | 9/12 | Suite enorme y ofensiva; sin coverage ni type-checker; CI no la corre |
| Arquitectura | 9/12 | Reglas de capa 100% cumplidas; god files |
| Performance | 7/10 | Caché correcto; hot-paths fichados (B-16..20) + 2 nuevos |
| Code Quality | 8/12 | Complejidad >20 en 6 funciones; param-explosión en texto |
| Dependencias | 9/11 | 9 deps pinneadas y sanas; sin lockfile; pytest en runtime |
| Deployment | 6/10 | Instalador pulido; CI publica sin tests y con permisos amplios |
| Documentación | 7/8 | Excepcional (AGENTS.md, arquitectura.md); falta CHANGELOG público |
| **TOTAL** | **70/93** | **75%** — sin críticos; 3 altos de proceso/CI |

### Distribución de findings por severidad

| Severidad | Cantidad |
|---|---|
| 🛑 CRÍTICO | 0 |
| 🔴 ALTO | 3 |
| 🟡 MEDIO | 9 |
| 🟢 BAJO | 7 |
| 🔎 Requiere verificación manual | 4 |

### Veredicto

⚠️ **Listo con remediaciones** — 3 findings ALTOS por resolver antes de scale-up. Operable en beta cerrada.

---

## 1. Findings Críticos 🛑

_No se encontraron findings críticos. ✅_

---

## 2. Findings Altos 🔴

### ALTO-01 — Servidor MCP `--http` sin autenticación propia

- **Check fallado**: S-18 (adaptado a servidor propio expuesto) / equivalente desktop de A01
- **Severidad**: 🔴 ALTO
- **Archivos**: `clon/omnicad/servidor_mcp/principal.py:64-67`
- **Evidencia**: en modo HTTP el servidor no genera ni exige token; `execute_code` queda disponible a cualquier proceso local. La protección DNS-rebinding del SDK `mcp==2.3.0` (verificada en el venv, `server.py:1164-1169`) filtra navegadores, no procesos locales. Contraste: el puente de la app (`ui/puente.py:84,210`) genera `secrets.token_urlsafe(32)` y compara con `secrets.compare_digest`.
- **Impacto**: cualquier proceso de la misma sesión de usuario puede ejecutar código arbitrario con los permisos del usuario si el MCP corre con `--http`.
- **Corrección concreta**: generar un token al arrancar con `--http` y exigirlo en un middleware del servidor (mismo patrón que `puente.json`), o documentar en grande que `--http` solo es confiable en mono-usuario y desactivar `execute_code` en ese modo.
- **Referencia**: OWASP A01:2025 Broken Access Control (adaptado a IPC local).

### ALTO-02 — CI publica instaladores sin correr tests

- **Check fallado**: Q-04 (tests en CI) + DP-09 (deploy solo tras verde)
- **Severidad**: 🔴 ALTO
- **Archivos**: `.github/workflows/instaladores.yml` (jobs 22-29, 51-56)
- **Evidencia**: único workflow del repo; instala deps y arma instaladores Windows/Linux; `publicar` usa `generate_release_notes` en tags. Cero invocaciones a pytest, ruff o `--prueba-humo` en el archivo.
- **Impacto**: un commit roto en main se publica como instalador público sin ninguna red.
- **Corrección concreta**: job `test` (pytest -q + ruff `--select F,B023,B905` + humo con `QT_QPA_PLATFORM: offscreen`) y `publicar: needs: [test, windows, linux]`.
- **Referencia**: DP-09 del checklist; "verify-before-commit" del propio AGENTS.md.

### ALTO-03 — Permisos CI amplios + acciones de terceros sin pin

- **Check fallado**: DP-11 (hardening CI/CD)
- **Severidad**: 🔴 ALTO
- **Archivos**: `.github/workflows/instaladores.yml:11-12,27` (`permissions: contents: write` global; `choco install innosetup`; `softprops/action-gh-release@v2` sin SHA)
- **Evidencia**: el permiso `contents: write` aplica a los 3 jobs aunque solo `publicar` lo necesita; las actions se referencian por tag mutable.
- **Impacto**: superficie de supply chain del propio pipeline; un tag re-punteado de la action o un PR externo que dispare build escribe en Releases.
- **Corrección concreta**: `permissions: contents: read` en el workflow y `contents: write` solo en el job `publicar`; pinnear `softprops/action-gh-release` a SHA completo.
- **Referencia**: DP-11; OWASP A03:2025 Supply Chain.

---

## 3. Findings Medios 🟡

### MED-01 — Sin reglas de seguridad always-on para codegen ni SAST
[S-21] · no existe `.claude/rules/security.md` ni secret-scanning en CI. Guía en tiempo de generación, no enforcement: agregar la sección a AGENTS.md + un workflow con gitleaks/ruff en PRs.

### MED-02 — Sin medición de cobertura
[Q-05] · `pytest-cov` no está en requirements ni configs (búsqueda `--cov` vacía). Agregar `pytest-cov` como dep dev y medir sin umbral al inicio.

### MED-03 — Sin lockfile
[D-02] · mitigado: `clon/requirements.txt` 100% pinneado con `==` y es fuente de pyproject (`pyproject.toml:22`). Con uv: `uv pip compile` → lock.

### MED-04 — pytest como dependencia de runtime
[D-05] · `requirements.txt:7` mete pytest al paquete y al instalador PyInstaller. Mover a `requirements-dev.txt` / extra.

### MED-05 — Sin type checker
[Q-07] · Python 3.12 grande (PySide6+OCP) sin mypy/pyright. Empezar mypy no-strict sobre `nucleo/`.

### MED-06 — God files
[A-06] · 14 archivos >1000 líneas; top: `ui/editor_boceto.py` 3533, `nucleo/solidos_crear.py` 2506, `restricciones/boceto.py` 2407, `nucleo/malla.py` 2144, `ui/ventana.py` 1972. Partir incremental al tocar cada archivo (roscas/agujeros de solidos_crear ya son un módulo natural).

### MED-07 — Complejidad >20 en 6 funciones
[C-02] · medido en el grafo: `auto_restringir` 29, `api/registro._convertir` 24, `svg._recorrer` 23, `timeline/entidades.resolver` 23, `boceto_desde_primitivas` 23, `fuentes._tabla_kern` 22. Extraer dispatch a tabla tipo→función.

### MED-08 — Hot-paths no fichados
[P-06] · `nucleo/analisis._mascara_aristas_concavas` con `linear_scan_in_loop=1` (O(n²) encubierto) y `nucleo/solidos_modificar.empalme` con `transitive_loop_depth=9` (kernel OCC en bucles anidados). (B-16..B-20 ya fichados en PROJECT_LOG no se repiten.)

### MED-09 — Param-explosión en la API de texto
[C-01] · `add_text`/`edit_text` con 31 params c/u, 4 niveles de opciones paralelas (`_opciones_texto`, `_maquetar`, `_validar_opciones_texto`). Unificar en un dict de opciones documentado.

---

## 4. Findings Bajos 🟢

| ID | Check | Archivo | Descripción | Corrección |
|---|---|---|---|---|
| BAJO-01 | S-02 | `.gitignore` | Sin entrada `.env*` (nunca hubo .env commiteado) | Agregar `.env*` |
| BAJO-02 | S-12 | `api/protocolo_puente.py:60-66` | `puente.json` con permisos de umask (legible en Linux multi-usuario) | `os.chmod(ruta, 0o600)` tras el replace |
| BAJO-03 | S-03 | `io_archivos/proyecto.py` (`z.read`) | Lectura de miembros ZIP sin tope de tamaño (zip-bomb de memoria) | Rechazar `file_size` > ~512 MB antes de leer |
| BAJO-04 | DP-08 | `instalador/` | Instalador sin firma de código (SmartScreen advertirá) | Documentar en README de releases; firmar si hay cert |
| BAJO-05 | Q-06 | `clon/pyproject.toml` | Ruff corre por doc (`--select F,B023,B905` en AGENTS.md) sin `[tool.ruff]` | Mover el select a pyproject para que todos corran lo mismo |
| BAJO-06 | DOC-07 | raíz | Sin `CHANGELOG.md` público (PROJECT_LOG cumple el rol interno) | CHANGELOG mínimo por tag |
| BAJO-07 | DP-07 | `docs/` | Sin runbook/rollback documentado | Sección en docs/arquitectura.md |

---

## 5. Requiere verificación manual 🔎

| ID | Check | Qué se sospecha | Qué falta para confirmar |
|---|---|---|---|
| VER-01 | D-01 | CVEs en deps pinneadas (pip-audit no instalado) | Correr `pip install pip-audit && pip-audit` una vez |
| VER-02 | DP-04 | Agente anterior citó RotatingFileHandler; esta pasada no lo encontró — logs a stderr/stdout | Confirmar si el log rotativo (ficha B-21 del PROJECT_LOG) llegó a main |
| VER-03 | DP-03 | El instalador .exe funciona limpio en máquina sin Python | Instalar el exe publicado en VM limpia |
| VER-04 | Q-01 | Suite completa verde (solo se coleccionó: 2459 tests) | Corrida completa por turnos (la corre el orquestador por memoria) |

---

## 6. Lo que SÍ está bien ✅

- **Regla arquitectónica sin-Qt 100% cumplida**: grep de PySide/Qt en `nucleo/`, `timeline/`, `restricciones/`, `io_archivos/` y `api/` = 0 violaciones; `api/` tampoco importa `mcp`. El catálogo único api→MCP/CLI no se duplica (los `cmd_*` son wrappers finos).
- **Secrets: cero** en el índice git; token del puente generado por arranque con `secrets`; sin `.env` en historia.
- **Puente en vivo bien diseñado**: localhost-only, token 32 bytes con compare_digest, `execute_code` desactivado por defecto, grupo `dev` bloqueado en vivo, tope 100 s.
- **Lectura de archivos falla cerrado y versionada** en tres capas (formato/receta/caché), sin zip-slip (`z.read` de nombres fijos), escritura atómica con limpieza de temporales.
- **2459 tests** con testing ofensivo serio: recetas corruptas, argumentos basura parametrizados contra toda la API, timeouts de bucles, topes astronómicos, números no finitos.
- **Sin eval inseguro**: expresiones paramétricas por AST con lista blanca (`timeline/parametros.py:11`); `exec` solo en los 2 lugares by-design y documentados.
- **Cero TODO/FIXME/HACK reales, cero código muerto detectado** (conteo de importadores + re-verificación manual de cada candidato).
- **Deps**: 9, todas pinneadas, oficiales, licencias compatibles con GPL-3.0.
- **Docs muy por encima del estándar**: AGENTS.md con recetas, arquitectura.md con 17 decisiones justificadas, doc de agentes generada con test anti-envejecimiento.

---

## 7. Roadmap de Remediación Sugerido

### Hoy (bloqueantes para el próximo release)
- [ ] ALTO-02: job `test` en CI + `publicar: needs: [test]`
- [ ] ALTO-03: permisos CI acotados + action pineada a SHA
- [ ] ALTO-01: token para `--http` (o desactivar `execute_code` en ese modo y documentarlo)

### Esta semana (alto impacto, low effort)
- [ ] BAJO-01/02/03 (.gitignore, chmod puente.json, tope ZIP) — tres líneas cada uno
- [ ] MED-04: pytest fuera de requirements de runtime
- [ ] BAJO-05: `[tool.ruff]` en pyproject

### Próximo sprint
- [ ] MED-02 (coverage) y MED-05 (mypy no-strict en nucleo/)
- [ ] MED-08: índice/set en `_mascara_aristas_concavas`; medir `empalme`
- [ ] MED-06/07: partir archivos y bajar complejidad incrementalmente (al tocar cada uno)

### Backlog
- [ ] BAJOS restantes (CHANGELOG, runbook, firma de instalador)
- [ ] MED-09: objeto de opciones para texto

---

## 8. Acciones que el usuario debe ejecutar manualmente
- Correr `pip-audit` una vez (VER-01) e instalar el .exe publicado en una VM limpia (VER-03).

---

## 9. Próximos pasos sugeridos
1. Resolver los 3 ALTOS antes del próximo tag/release.
2. Si querés, `loop-mejora` con los ALTOS como quality gates.
3. Re-audit con esta skill tras las remediaciones.

---

## Anexos

### A. Comandos usados
Greps de secrets (`sk_live/AKIA/AIza/ghp_/postgresql://`, api_key/secret/password/token), `git log --all -- .env*`, `git ls-files`, `pytest --collect-only -q` (2459 collected in 17.75s), `pip list --outdated`, lectura del SDK `mcp` del venv, conteo de importadores sobre 161 archivos, `grep PySide/Qt/mcp` por capa, queries al grafo codebase-memory (complejidad, fan-in), grep TODO/FIXME/HACK, búsqueda `--cov/coverage`, medición de líneas de archivos.

### B. Archivos revisados (muestra clave)
`servidor_mcp/principal.py`, `api/protocolo_puente.py`, `ui/puente.py`, `io_archivos/proyecto.py`, `io_archivos/f3d_nativo.py`, `integraciones/fusion/…/OmniCADPuente.py`, `timeline/documento.py`, `timeline/operaciones.py`, `clon/requirements.txt`, `clon/pyproject.toml`, `.github/workflows/instaladores.yml`, `instalador/*.iss`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/arquitectura.md`, suites `tests/` (94 archivos). No auditado: `analisis auto/` (fuera de git), `privado/`, venv.

### C. Checks ejecutados — resumen
S: 21 checks (10 aplicables: 8 PASS, 2 FAIL-Bajo/Medio) · Q: 13 (9 aplicables: 6 PASS, 3 FAIL) · D: 12 (10 aplicables: 7 PASS, 3 FAIL) · DP: 11 (8 aplicables: 4 PASS, 4 FAIL) · A: 12 (10 aplicables: 9 PASS, 1 FAIL) · P: 10 (4 aplicables: 3 PASS, 1 FAIL-conocido) · C: 12 (9 aplicables: 6 PASS, 3 FAIL/note) · DOC: 8 (7 PASS, 1 FAIL). Detalle por check disponible en los reportes de los 3 subagentes de dominio (sesión 2026-10-14).
