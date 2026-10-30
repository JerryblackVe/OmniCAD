# -*- coding: utf-8 -*-
"""Corre toda la prueba de la ventana como usuario, de a una pieza (con `scripts/turno.py`: una sola cosa pesada a la vez).

Desde `clon/`:
    .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py [nombre ...]

Sin nombres corre todas. Deja los registros (`*.json`), los logs y las capturas en `evidencias/ui_<hoy>/` (fuera de git)
y al final imprime un resumen: comprobaciones y fallas por pieza.
    --ventana minimizada|visible   (por defecto minimizada: la ventana no aparece ni roba el foco, se puede usar la PC;
                                    visible: se ve y toma el foco, no usar el mouse ni el teclado mientras corre).
Las piezas de PIEZAS_CON_FOCO_REAL (única lista; hoy `registro_uso`) se saltean en minimizada con un aviso ⚠ (no cuentan como ✗):
correrlas con `--ventana visible`. Lo mismo vale para el chequeo de Ctrl+Mayús+A de `asistente` (se saltea dentro de la pieza con ⚠).
Con la PC en uso, esas corridas con foco real se dejan para el final.
"""
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):          # el resumen usa ✗: que no dependa de la consola (cp1252)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
SALIDA = Path(os.environ.get("OMNICAD_PRUEBA_SALIDA") or RAIZ / "evidencias" / f"ui_{date.today().isoformat()}")
PIEZAS = ["cinta_completa", "superficie", "solido_crear", "solido_modificar", "asas", "teclear", "ventana_uso", "ensamblar", "boceto_cotas", "asistente", "iconos", "boton_asistente", "abrir_f3d", "booleana_unir", "origen_cara", "registro_uso"]
# Piezas que necesitan el foco REAL de Windows (no solo el activo de Qt). Vacía hasta que la A/B demuestre alguna.
PIEZAS_CON_FOCO_REAL = {"registro_uso"}      # el indicador y la sesión real no arrancan con la ventana transparente


def correr(nombre):
    SALIDA.mkdir(parents=True, exist_ok=True)
    log = SALIDA / f"{nombre}.log"
    entorno = dict(os.environ, OMNICAD_PRUEBA_SALIDA=str(SALIDA), PYTHONIOENCODING="utf-8")
    python = sys.executable
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([python, str(RAIZ / "scripts" / "turno.py"), "--", python, str(AQUI / f"{nombre}.py")],
                           stdout=f, stderr=subprocess.STDOUT, env=entorno, cwd=RAIZ / "clon")
    texto = log.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"=== (\d+) comprobaciones, (\d+) con", texto)
    return r.returncode, (int(m.group(1)), int(m.group(2))) if m else None, log


if __name__ == "__main__":
    args = sys.argv[1:]
    modo = os.environ.get("OMNICAD_PRUEBA_VENTANA", "minimizada")
    if "--ventana" in args:
        i = args.index("--ventana")
        modo = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if modo not in ("minimizada", "visible"):
        sys.exit("--ventana debe ser «minimizada» o «visible»")
    os.environ["OMNICAD_PRUEBA_VENTANA"] = modo          # los hijos la heredan
    elegidas = args or PIEZAS
    for nombre in elegidas:
        if nombre not in PIEZAS:
            sys.exit(f"Pieza desconocida: {nombre}. Opciones: {', '.join(PIEZAS)}")
    print(f"Evidencia en {SALIDA}\n")
    mal = 0
    for nombre in elegidas:
        if modo == "minimizada" and nombre in PIEZAS_CON_FOCO_REAL:
            print(f"{nombre:18s} ⚠ saltada: necesita ventana visible (--ventana visible)")
            continue
        codigo, cuentas, log = correr(nombre)
        if cuentas is None:
            print(f"{nombre:18s} ✗ no terminó (salida {codigo}); mirar {log.name}")
            mal += 1
        else:
            total, fallas = cuentas
            print(f"{nombre:18s} {total:4d} comprobaciones, {fallas:3d} con ✗   ({log.name})")
            mal += fallas > 0
    print("\nLas ✗ no siempre son bugs: abrir el log, ver si es de la app o de la prueba (omnicad-test, sección 5).")
    sys.exit(1 if mal else 0)
