#!/usr/bin/env python3
"""PreToolUse(Bash): recordatorio de ponytail-review solo si el comando ejecuta `git commit`.

Cubre `git commit`, `git -C x commit`, tras `&&`, `;`, `||`, `|` o salto de línea; no si el texto solo lo nombra
(`echo git commit`, un `for` que lo imprime).
"""
import json
import re
import sys

COMMIT = re.compile(r"(?:^|&&|\|\||;|\||\n)[ \t]*git(?:[ \t]+-[^\s]+(?:[ \t]+[^\s-][^\s]*)?)*[ \t]+commit(?![-\w])")

try:
    comando = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
    if COMMIT.search(comando):
        msg = ("Antes de commitear: si el commit lleva cambios de codigo y todavia no corriste la skill ponytail-review "
               "en esta sesion, invocala ahora con la herramienta Skill. Reporta el resultado real.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
except Exception:
    pass  # un hook de aviso nunca debe trabar el turno
