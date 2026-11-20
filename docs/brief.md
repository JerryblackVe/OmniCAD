# Plantilla de brief a una sesión o a OpenCode

El brief que manda el coordinador es corto (5 líneas como mucho; número único, también en `CLAUDE.md` › Protocolo de ahorro): **ID + archivo(s) + «seguí docs/brief.md»**. Todo lo fijo vive acá, para no repetirlo en cada mensaje.

## Lo que el brief nombra
- ID del ítem, archivo(s) o sección y qué significa «hecho» (1 línea).
- Modelo y esfuerzo del ítem (los fija el coordinador: tabla en `docs/coordinacion.md`).

## Lo que esta plantilla ya exige
1. **Skills** (fuente única de esta lista; invocadas con la herramienta Skill, no solo nombradas): `fable-method` y `ponytail` al empezar, `verify-before-commit` (en OmniCAD se cumple con ruff y `tests_afectados.py --correr`: la suite y la humo corren de noche), y `ponytail-review` antes de cerrar (`omnicad-test` si prueba la ventana; `ponytail-audit` / `ponytail-debt` cuando haga falta). Briefs a OpenCode: además `plan-then-do` y `tool-calling-guard`.
2. **Fusion**: leer `docs/fusion_docs/` antes de arreglar algo que replica un comando (cómo buscar: `docs/coordinacion.md`).
3. **Autocontenido**: la sesión arranca leyendo solo la última nota de TU sesión (la que empieza con el encabezado «Traspaso <título de la sesión>») en el Registro de `PROJECT_LOG.md`, nada más.
4. **Un ítem**: worktree propio (`scripts/worktree_item.sh`), `tests_afectados.py --correr`, sin commit ni push. Conservar los finales de línea de cada archivo (casi todos son CRLF): nunca pasarlo entero a LF; `git diff --stat` del archivo tiene que mostrar solo las líneas cambiadas (Gerardo, 2026-11-19, por B-586).
5. **Modelos**: solo los que nombra el brief; si no están o se acaba el cupo, parar y avisar, nunca reemplazar (salvo la rotación del vigía, «Protocolo de OpenCode»).
6. **UI**: si el ítem toca interfaz, leé [docs/protocolo_ux.md](docs/protocolo_ux.md) antes de empezar y pegá su «Lista de control» (15 puntos, con captura o test por punto) en el informe. El coordinador no integra un ítem de UI sin ella, aunque ruff y los tests estén en verde.
7. **Informe** (10 líneas más los hallazgos de `ponytail-review`): hecho / no hecho, archivos, salida real de ruff y tests, y qué falta. El coordinador comprueba que pegó la salida real de `ponytail-review`.
