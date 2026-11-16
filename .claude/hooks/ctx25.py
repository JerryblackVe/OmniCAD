#!/usr/bin/env python3
"""UserPromptSubmit: avisa del traspaso cuando el contexto llega al umbral de aviso.

Umbrales (CLAUDE.md › Protocolo de ahorro, punto 1): aviso al 30 % para todos; tope 40 % chat maestro y
coordinador, 35 % E1–E11. El hook no sabe el rol: dice los dos topes. Lee transcript_path del stdin;
uso = input + cache_creation + cache_read del último mensaje del asistente. Ventana: OMNICAD_CTX_VENTANA.
shortcut: aproximación por tokens del transcript, no el medidor de la app; afinar la ventana si difiere.
"""
import json
import os
import sys

CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
AVISO, TOPE_E, TOPE_COORD = 30, 35, 40


def uso_actual(ruta):
    """Último uso de contexto del transcript (lee solo el final del archivo)."""
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400_000))
        lineas = f.read().decode("utf-8", "ignore").splitlines()
    for linea in reversed(lineas):
        try:
            u = (json.loads(linea).get("message") or {}).get("usage")
        except ValueError:
            continue
        if u:
            return sum(u.get(k, 0) or 0 for k in CAMPOS)
    return 0


def aviso(usados, ventana):
    pct = usados * 100 // ventana
    if pct < AVISO:
        return ""
    return (f"Contexto ~{pct} % (aviso al {AVISO} %; tope {TOPE_COORD} % chat maestro y coordinador, {TOPE_E} % E1–E11): "
            "al cerrar el ítem actual, nota de traspaso de 5 líneas en PROJECT_LOG › Registro → clear_session → brief nuevo "
            "(quién vacía a quién: CLAUDE.md › Protocolo de ahorro). Nunca vaciar en medio de un ítem.")


if __name__ == "__main__":
    try:
        ruta = json.load(sys.stdin).get("transcript_path", "")
        if ruta and os.path.exists(ruta):
            msg = aviso(uso_actual(ruta), int(os.environ.get("OMNICAD_CTX_VENTANA", "1000000")))
            if msg:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}))
    except Exception:
        pass  # un hook de aviso nunca debe trabar el turno
