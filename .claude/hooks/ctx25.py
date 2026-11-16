#!/usr/bin/env python3
"""UserPromptSubmit: avisa del traspaso cuando el contexto llega al umbral de aviso.

Los números (aviso, topes) viven en CLAUDE.md › Protocolo de ahorro, punto 1; acá solo se leen de las constantes.
Lee transcript_path del stdin: uso = input + cache_creation + cache_read del último mensaje del asistente, modelo del
mismo mensaje y título de la sesión (custom-title). Ventana: OMNICAD_CTX_VENTANA, o 1M si el modelo trae «[1m]» o el uso
ya pasó 200K; si no, 200K. Rol por el título: «maestro» o «coordinador» → reemplazo; el resto (E1–E11) → clear_session.
shortcut: aproximación por tokens del transcript, no el medidor de la app; afinar la ventana si difiere.
"""
import json
import os
import sys

CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
AVISO, TOPE_E, TOPE_COORD = 30, 35, 40


def leer(ruta):
    """(uso, modelo, título) del final del transcript (lee solo los últimos 400 KB)."""
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400_000))
        lineas = f.read().decode("utf-8", "ignore").splitlines()
    uso, modelo, titulo = 0, "", ""
    for linea in reversed(lineas):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        m = d.get("message") or {}
        if not uso and m.get("usage"):
            uso = sum(m["usage"].get(k, 0) or 0 for k in CAMPOS)
            modelo = m.get("model", "")
        if not titulo and d.get("type") == "custom-title":
            titulo = d.get("customTitle", "")
        if uso and titulo:
            break
    return uso, modelo, titulo


def ventana(uso, modelo):
    env = os.environ.get("OMNICAD_CTX_VENTANA")
    if env:
        return int(env)
    return 1_000_000 if "[1m]" in modelo.lower() or uso > 200_000 else 200_000


def aviso(uso, modelo, titulo):
    pct = uso * 100 // ventana(uso, modelo)
    if pct < AVISO:
        return ""
    reemplazo = any(r in titulo.lower() for r in ("maestro", "coordinador"))
    tope, accion = (TOPE_COORD, "sesión nueva con el mismo título (la vieja pasa a «(viejo)»), sin clear_session") if reemplazo \
        else (TOPE_E, "clear_session + brief nuevo")
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
