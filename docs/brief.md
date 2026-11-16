# Plantilla de brief a una sesión o a OpenCode

El brief que manda el coordinador es corto (5 líneas como mucho; número único, también en `CLAUDE.md` › Protocolo de ahorro): **ID + archivo(s) + «seguí docs/brief.md»**. Todo lo fijo vive acá, para no repetirlo en cada mensaje.

## Lo que el brief nombra
- ID del ítem, archivo(s) o sección y qué significa «hecho» (1 línea).
- Modelo y esfuerzo del ítem (los fija el coordinador: tabla en `docs/coordinacion.md`).

## Lo que esta plantilla ya exige
1. **Skills** (invocadas con la herramienta Skill, no solo nombradas): `fable-method` y `ponytail` al empezar, `verify-before-commit`, y `ponytail-review` antes de cerrar (`omnicad-test` si prueba la ventana). Briefs a OpenCode: además `plan-then-do` y `tool-calling-guard`.
2. **Fusion**: leer `docs/fusion_docs/` con `scripts/fusion_docs.py buscar <palabras>` antes de arreglar algo que replica un comando.
3. **Autocontenido**: la sesión arranca leyendo la última nota de traspaso de TU sesión (la tuya, no la más nueva de otra) en el Registro de `PROJECT_LOG.md`, nada más.
4. **Un ítem**: worktree propio (`scripts/worktree_item.sh`), `tests_afectados.py --correr`, sin commit ni push.
5. **Modelos**: solo los que nombra el brief; si no están o se acaba el cupo, parar y avisar, nunca reemplazar.
6. **Informe** (10 líneas más los hallazgos de `ponytail-review`): hecho / no hecho, archivos, salida real de ruff y tests, y qué falta. El coordinador comprueba que pegó la salida real de `ponytail-review`.
