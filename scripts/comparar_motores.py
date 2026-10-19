# -*- coding: utf-8 -*-
"""Compara los dos motores: tiempos por operación (casos de paridad) y recálculo de los documentos guardados.

Uso, desde la raíz del repo y con el Python del venv:
    clon/.venv/Scripts/python.exe scripts/comparar_motores.py            escribe docs/comparacion_motores.md
Cada medición corre en un intérprete aparte con UN solo motor; el lado OmniKernel con OMNICAD_BLOQUEAR_OCP=1.
Los documentos son todos los .omnicad de evidencias/ (fuera de git), con su ruta relativa en la tabla.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

RAIZ = Path(__file__).resolve().parents[1]
CLON = RAIZ / "clon"
PLAZO = 300           # por documento: las booleanas curvas lentas (FK-016) pasan los 15 minutos


def _entorno(motor):
    e = dict(os.environ, OMNICAD_MOTOR=motor, PYTHONIOENCODING="utf-8", PYTHONPATH=str(CLON),
             QT_QPA_PLATFORM="offscreen")
    e.pop("OMNICAD_BLOQUEAR_OCP", None)
    if motor == "omnikernel":
        e["OMNICAD_BLOQUEAR_OCP"] = "1"
    return e


def _correr(args, motor, prefijo):
    try:
        p = subprocess.run([sys.executable, *args], cwd=CLON, env=_entorno(motor), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=PLAZO)
    except subprocess.TimeoutExpired:
        return {"error_kind": "TIEMPO", "mensaje": f"más de {PLAZO} s"}
    lineas = [x for x in p.stdout.splitlines() if x.startswith(prefijo)]
    if not lineas:
        salida = (p.stdout + p.stderr).strip().splitlines()
        motivo = [x for x in salida if "memory allocation" in x or "panicked" in x] or salida[-1:] or ["sin salida"]
        return {"error_kind": "CAIDA", "mensaje": motivo[0].strip()[:200]}
    return json.loads(lineas[-1][len(prefijo):])


def medir_documento(ruta):
    """Abre el documento y lo recalcula entero con el motor de OMNICAD_MOTOR."""
    import omnicad  # noqa: F401 — activa el bloqueo de OCP antes de cargar geometría
    from omnicad.io_archivos import proyecto
    from omnicad.nucleo import consultas, geometria as geo
    d = proyecto.abrir(ruta)
    d._cache.clear()        # sin la caché en memoria: se mide el recálculo entero
    inicio = time.perf_counter()
    d.recalcular(0)
    segundos = time.perf_counter() - inicio
    pasos = []
    for op, r in zip(d.operaciones, d.resultados, strict=False):
        if r.estado != "ok":
            pasos.append({"id": op.id, "tipo": op.TIPO, "estado": r.estado, "mensaje": r.mensaje[:300]})
    volumen, cuerpos = 0.0, 0
    for c in d.estado_final.cuerpos.values():
        if consultas.es_forma(c.forma):        # los cuerpos de malla no tienen volumen exacto
            try:
                volumen += geo.volumen(c.forma)
                cuerpos += 1
            except geo.ErrorGeometria:
                pass
    return {"segundos": segundos, "pasos": len(d.operaciones), "fallidos": pasos, "volumen": volumen,
            "cuerpos": cuerpos}


def _resumen_doc(a, b):
    if "error_kind" in b:
        return f"{b['error_kind']}: {b['mensaje']}"
    sin = [p for p in b["fallidos"] if "OmniKernel todavía no hace" in p["mensaje"]]
    otros = [p for p in b["fallidos"] if p not in sin and p["id"] not in {q["id"] for q in a.get("fallidos", [])}]
    if sin:
        motivo = sin[0]["mensaje"].split("OmniKernel todavía no hace ", 1)[1].split(". Podés")[0]
        return f"MOTOR_SIN_SOPORTE ({len(sin)} pasos; primero {sin[0]['id']} {sin[0]['tipo']}: {motivo})"
    if otros:
        return f"FALLA ({otros[0]['id']} {otros[0]['tipo']}: {otros[0]['mensaje'][:120]})"
    if "volumen" in a and abs(a["volumen"] - b["volumen"]) > 1e-6 * max(abs(a["volumen"]), 1.0):
        return f"diferencia de volumen {b['volumen'] - a['volumen']:+.6g} mm³"
    return "OK"


def main():
    sys.path.insert(0, str(CLON / "tests"))
    from test_paridad_motor import CONECTADOS, SIN_SOPORTE
    filas_op, diferencias = [], []
    for caso in CONECTADOS + SIN_SOPORTE:
        a, b = (_correr(["tests/caso_paridad_motor.py", caso], m, "RESULTADO_PARIDAD=")
                for m in ("opencascade", "omnikernel"))
        igual = "sí" if caso in CONECTADOS else "no (MOTOR_SIN_SOPORTE)"
        tb = f"{b['segundos'] * 1000:.1f}" if "segundos" in b else "—"
        filas_op.append(f"| {caso} | {a['segundos'] * 1000:.1f} | {tb} | {igual} |")
        if "segundos" in b:
            diferencias.append((b["segundos"] - a["segundos"], f"operación {caso}", a["segundos"], b["segundos"]))
        print(filas_op[-1], flush=True)
    filas_doc = []
    for ruta in sorted((RAIZ / "evidencias").rglob("*.omnicad")):
        rel = ruta.relative_to(RAIZ).as_posix()
        a = _correr([str(Path(__file__).resolve()), "--documento", str(ruta)], "opencascade", "RESULTADO_DOC=")
        b = _correr([str(Path(__file__).resolve()), "--documento", str(ruta)], "omnikernel", "RESULTADO_DOC=")
        ta = f"{a['segundos']:.2f}" if "segundos" in a else a.get("error_kind", "—")
        tb = f"{b['segundos']:.2f}" if "segundos" in b else b.get("error_kind", "—")
        pasos = a.get("pasos", b.get("pasos", "—"))
        filas_doc.append(f"| `{rel}` | {pasos} | {ta} | {tb} | {_resumen_doc(a, b)} |")
        if "segundos" in a and "segundos" in b and not b["fallidos"]:
            diferencias.append((b["segundos"] - a["segundos"], f"documento {rel}", a["segundos"], b["segundos"]))
        print(filas_doc[-1], flush=True)
    diferencias.sort(key=lambda x: -abs(x[0]))
    texto = ["# Comparación de motores: OpenCascade y OmniKernel", "",
             f"Generado por `scripts/comparar_motores.py` el {time.strftime('%Y-%m-%d %H:%M')}. Cada medición corre en "
             "un proceso aparte con un solo motor; el lado OmniKernel con `OMNICAD_BLOQUEAR_OCP=1`. Los tiempos de "
             "operación incluyen construir la entrada (caja, boceto). «Resultado igual» = la prueba de paridad de "
             "`clon/tests/test_paridad_motor.py` (volumen, área, conteos, validez y firmas).", "",
             "## Operaciones", "", "| Operación | OCC (ms) | OmniKernel (ms) | Resultado igual |", "|---|---|---|---|",
             *filas_op, "", "## Documentos guardados", "",
             "Recálculo completo (`Documento.recalcular(0)`) de cada `.omnicad` de `evidencias/`.", "",
             "| Documento | Pasos | OCC (s) | OmniKernel (s) | Resultado con OmniKernel |", "|---|---|---|---|---|",
             *filas_doc, "", "## Las 5 diferencias de tiempo más grandes", "",
             "| Qué | OCC (s) | OmniKernel (s) | OmniKernel − OCC (s) |", "|---|---|---|---|",
             *[f"| {q} | {a:.3f} | {b:.3f} | {d:+.3f} |" for d, q, a, b in diferencias[:5]], ""]
    (RAIZ / "docs" / "comparacion_motores.md").write_text("\n".join(texto), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--documento"]:
        try:
            r = medir_documento(sys.argv[2])
        except Exception as e:  # noqa: BLE001 — se informa en la tabla, no frena la comparación
            r = {"error_kind": getattr(e, "error_kind", type(e).__name__), "mensaje": str(e)[:300]}
        print("RESULTADO_DOC=" + json.dumps(r, ensure_ascii=False))
    else:
        main()
