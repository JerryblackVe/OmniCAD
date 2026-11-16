#!/usr/bin/env python3
"""PreToolUse(Bash): recordatorio de ponytail-review solo si el comando ejecuta `git commit` (también tras `&&` o `;`), no si solo lo nombra."""
import json
import re
import sys

try:
    comando = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
    if re.search(r"(^|&&|;|\|\|)\s*git commit\b", comando):
        msg = ("Antes de commitear: si el commit lleva cambios de codigo y todavia no corriste la skill ponytail-review "
               "en esta sesion, invocala ahora con la herramienta Skill. Reporta el resultado real.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
except Exception:
    pass  # un hook de aviso nunca debe trabar el turno
