#!/usr/bin/env bash
# SessionStart: lista de arranque de 5 líneas (HOOKS-1116; AUDIT-REGLAS-1116).
python3 - <<'PY'
import json
t = ("Lista de arranque OmniCAD: "
     "1) leé solo la última nota de TU sesión (la que empieza con el encabezado «Traspaso <título de la sesión>») en PROJECT_LOG.md › Registro (grep -n, offset/limit; no el log entero, ni APRENDIZAJES.md entero: de las lecciones, solo la sección del tema). En OmniCAD esto manda sobre el recordatorio global de aprender (no hace falta leer APRENDIZAJES ni contar lecciones). El coordinador además lee docs/seguimiento/agenda.md. "
     "2) E1–E11: informá al coordinador por SendMessage a «Coordinador principal OmniCAD»; el coordinador informa al chat maestro (nombre en ~/chat_maestro.txt). Si ves un título repetido con «(viejo)», escribile a la sesión sin «(viejo)». "
     "3) Coordinador y chat maestro: vigilancia y cola de OpenCode según el «Protocolo de OpenCode» (docs/coordinacion.md), no por reloj corto. "
     "4) Regla 17: si CLAUDE.md/Protocolo ya deciden un paso, hacelo sin preguntar y avisá en 1 renglón; preguntá solo por push, gasto, borrado, algo hacia afuera o decisión de producto. "
     "5) Tope de contexto y quién vacía a quién: CLAUDE.md › Protocolo de ahorro, punto 1.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": t}}))
PY
