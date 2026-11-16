#!/usr/bin/env python3
"""UserPromptSubmit: avisa del traspaso cuando el contexto llega al umbral de aviso.

Los números (aviso, topes) viven en CLAUDE.md › Protocolo de ahorro, punto 1; acá solo se leen de las constantes.
Lee transcript_path del stdin: uso = input + cache_creation + cache_read del último mensaje del asistente, modelo del
mismo mensaje y título de la sesión (custom-title). Ventana: OMNICAD_CTX_VENTANA (def. 1M: Sonnet 5.5 y Opus 5.5, medido con get_usage).
Rol por el título: «maestro» o «coordinador» → reemplazo; el resto (E1–E11) → lo vacía el coordinador.
shortcut: aproximación por tokens del transcript, no el medidor de la app; afinar la ventana si difiere.
"""
import json
import os
import sys

CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
AVISO, TOPE_E, TOPE_COORD = 30, 35, 40


def leer(ruta):
    """(uso, título) del final del transcript (lee solo los últimos 400 KB)."""
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400_000))
        lineas = f.read().decode("utf-8", "ignore").splitlines()
    uso, titulo = 0, ""
    for linea in reversed(lineas):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        m = d.get("message") or {}
        if not uso and m.get("usage"):
            uso = sum(m["usage"].get(k, 0) or 0 for k in CAMPOS)
        if not titulo and d.get("type") == "custom-title":
            titulo = d.get("customTitle", "")
        if uso and titulo:
            break
    return uso, titulo


def aviso(uso, titulo):
    pct = uso * 100 // int(os.environ.get("OMNICAD_CTX_VENTANA", "1000000"))
    if pct < AVISO:
        return ""
    reemplazo = any(r in titulo.lower() for r in ("maestro", "coordinador"))
    tope, accion = (TOPE_COORD, "sesión nueva con el mismo título (la vieja pasa a «(viejo)»), sin clear_session") if reemplazo \
        else (TOPE_E, "te vacía el coordinador (clear_session + brief nuevo)")
    return (f"Contexto ~{pct} % (aviso al {AVISO} %; tu tope: {tope} %): al cerrar el ítem actual, nota de traspaso de 5 líneas "
            f"en PROJECT_LOG › Registro → {accion}. Nunca en medio de un ítem. Detalle: CLAUDE.md › Protocolo de ahorro.")


if __name__ == "__main__":
    try:
        ruta = json.load(sys.stdin).get("transcript_path", "")
        if ruta and os.path.exists(ruta):
            msg = aviso(*leer(ruta))
            if msg:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}))
    except Exception:
        pass  # un hook de aviso nunca debe trabar el turno
