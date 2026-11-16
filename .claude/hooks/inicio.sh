#!/usr/bin/env bash
# SessionStart: lista de arranque de 5 líneas (HOOKS-1116; AUDIT-REGLAS-1116).
python3 - <<'PY'
import json
t = ("Lista de arranque OmniCAD: "
     "1) leé SOLO la nota de traspaso más nueva de PROJECT_LOG.md › Registro (grep -n, offset/limit; no el log entero, ni APRENDIZAJES.md entero: de las lecciones, solo la sección del tema). "
     "2) E1–E11: informá al coordinador por SendMessage a «Coordinador principal OmniCAD en VPS» (el coordinador se vacía, no se reemplaza: el nombre no cambia); el coordinador informa al chat maestro (nombre en ~/chat_maestro.txt). "
     "3) Coordinador y chat maestro: vigilar cada 2 h y cuando una sesión termina, no por reloj corto; OpenCode siempre con trabajo (Protocolo de OpenCode). "
     "4) Regla 17: si CLAUDE.md/Protocolo ya deciden un paso, hacelo sin preguntar y avisá en 1 renglón; preguntá solo por push, gasto, borrado, algo hacia afuera o decisión de producto. "
     "5) Tope de contexto y quién vacía a quién: CLAUDE.md › Protocolo de ahorro, punto 1.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": t}}))
PY
