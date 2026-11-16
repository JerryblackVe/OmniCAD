#!/usr/bin/env python3
"""UserPromptSubmit: si el contexto pasó el 25 %, recuerda el traspaso (HOOKS-1116).

Lee transcript_path del stdin y suma el uso del último mensaje del asistente
(input + cache_creation + cache_read). Ventana: OMNICAD_CTX_VENTANA (def. 1000000).
shortcut: aproximación por tokens del transcript, no el medidor de la app; afinar la ventana si difiere.
"""
import json
import os
import sys


def tokens(ruta):
    ultimo = 0
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400_000))
        for linea in f.read().decode("utf-8", "ignore").splitlines():
            try:
                u = (json.loads(linea).get("message") or {}).get("usage")
            except ValueError:
                continue
            if u:
                ultimo = sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return ultimo


try:
    ruta = json.load(sys.stdin).get("transcript_path", "")
    usados = tokens(ruta) if ruta and os.path.exists(ruta) else 0
    ventana = int(os.environ.get("OMNICAD_CTX_VENTANA", "1000000"))
    if usados * 4 >= ventana:
        msg = (f"Contexto ~{usados * 100 // ventana} % (>=25 %): al cerrar el ítem actual, nota de traspaso de 5 líneas "
               "en PROJECT_LOG › Registro → clear_session → brief nuevo. No abras sesión nueva. Nunca vaciar en medio de un ítem.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}))
except Exception:
    pass  # un hook de aviso nunca debe trabar el turno
