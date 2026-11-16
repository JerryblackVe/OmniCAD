#!/usr/bin/env bash
# SessionStart: lista de arranque de 5 líneas (HOOKS-1116).
python3 - <<'PY'
import json
t = ("Lista de arranque OmniCAD: "
     "1) leé la nota de traspaso más nueva en PROJECT_LOG.md › Registro y ~/chat_maestro.txt (nombre del chat maestro: lo de Gerardo va ahí por SendMessage). "
     "2) Reportá al coordinador: SendMessage a «Coordinador principal OmniCAD en VPS» (desde la VPS también vale el id local_8795179c-70ba-4adf-9cd5-7f2bfba5513a). "
     "3) Coordinador y chat maestro: vigilar cada 2 h y cuando una sesión termina, no por reloj corto; OpenCode siempre con trabajo (Protocolo de OpenCode). "
     "4) Regla 17: si CLAUDE.md/memoria/Protocolo ya deciden un paso, hacelo sin preguntar y avisá en 1 renglón; preguntá solo por push, gasto, borrado, algo hacia afuera o decisión de producto. "
     "5) Al 25 % de contexto: nota de 5 líneas → clear_session → brief; no abras sesión nueva.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": t}}))
PY
