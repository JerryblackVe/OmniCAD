# -*- coding: utf-8 -*-
"""Corre toda la prueba de la ventana como usuario, de a una pieza (con `scripts/turno.py`: una sola cosa pesada a la vez)
o de a varias con `--paralelo N`.

Desde `clon/`:
    .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py [nombre ...]

Sin nombres corre todas. Deja los registros (`*.json`), los logs y las capturas en `evidencias/ui_<hoy>/` (fuera de git)
y al final imprime un resumen: comprobaciones y fallas por pieza.
En ambos modos guarda SALIDA/tiempos_piezas.json, conservando los tiempos previos de las piezas no ejecutadas.
    --ventana minimizada|visible   (por defecto minimizada: la ventana no aparece ni roba el foco, se puede usar la PC;
                                    visible: se ve y toma el foco, no usar el mouse ni el teclado mientras corre).
    --paralelo N                    (por defecto 1: como siempre, de a una pieza y en orden). Con N > 1 corre hasta N
                                    piezas a la vez, cada una en su propia ventana, y `turno.py` les da N lugares
                                    (OMNICAD_TURNOS=N para los hijos). Si hay tiempos de una corrida anterior (el más nuevo de
                                    `evidencias/ui_*/tiempos_piezas.json`), arranca por la más larga para achicar la
                                    cola final; una pieza sin dato va al final. El resumen sale siempre en el orden de
                                    PIEZAS (o el de los nombres pedidos), termine como termine cada pieza.
Las piezas de PIEZAS_CON_FOCO_REAL (única lista; hoy `registro_uso`) se saltean en minimizada con un aviso ⚠ (no cuentan como ✗):
correrlas con `--ventana visible`. Lo mismo vale para el chequeo de Ctrl+Mayús+A de `asistente` (se saltea dentro de la pieza con ⚠).
Con la PC en uso, esas corridas con foco real se dejan para el final.
La carpeta de piezas se puede cambiar con OMNICAD_PRUEBA_PIEZAS (una pieza por `.py`; la usan los tests, que no abren
ventanas) y la de salida con OMNICAD_PRUEBA_SALIDA.
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):          # el resumen usa ✗: que no dependa de la consola (cp1252)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
SALIDA = Path(os.environ.get("OMNICAD_PRUEBA_SALIDA") or RAIZ / "evidencias" / f"ui_{date.today().isoformat()}")
PIEZAS = ["cinta_completa", "superficie", "superficie_fusion", "superficie_guias", "solido_crear", "solido_modificar", "asas", "teclear", "herramientas_solido", "ventana_uso", "ensamblar", "ensamblar_asm", "posicion_asm", "boceto_cotas", "asistente", "iconos", "boton_asistente", "abrir_f3d", "booleana_unir", "origen_cara", "auditoria_boceto", "simetria_boceto", "auditoria_undo", "seccion_color", "perdidas_atenuar", "registro_uso", "inferencias", "desfase_boceto", "patrones_boceto", "restricciones_boceto", "patrones_solidos", "paneles_inventario", "dialogos_inventario", "paneles_temas", "patrones_ensamble_rosca", "boceto_herramientas", "proyectar_boceto", "panel_movible", "paneles_boceto", "timeline_menu", "subensamblaje", "pasos_largos", "construir", "mapa_desviacion", "texto_curva", "inspeccionar", "parametros", "previa_aparte", "cm_ventana", "cm_pieza_varilla"]
PIEZAS.append("objetos_vectoriales")
PIEZAS.append("manipulacion_vectorial")
PIEZAS.append("extruir_espacios")
PIEZAS.append("revolucion_barrido_solevacion")
PIEZAS.append("nervio_red_repujado")
PIEZAS.append("proyecciones_boceto")
# Carpeta de piezas propia (tests): una pieza por `.py`, sin tocar las de verdad.
PIEZAS_DIR = Path(os.environ.get("OMNICAD_PRUEBA_PIEZAS") or AQUI)
if PIEZAS_DIR != AQUI:
    PIEZAS = sorted(p.stem for p in PIEZAS_DIR.glob("*.py") if p.stem not in ("todo", "arnes"))
# Piezas que necesitan el foco REAL de Windows (no solo el activo de Qt). Vacía hasta que la A/B demuestre alguna.
PIEZAS_CON_FOCO_REAL = {"registro_uso"}      # el indicador y la sesión real no arrancan con la ventana transparente
TIEMPOS = "tiempos_piezas.json"              # segundos por pieza de la corrida anterior (la más larga arranca primero)


def correr(nombre, lugares=1):
    SALIDA.mkdir(parents=True, exist_ok=True)
    log = SALIDA / f"{nombre}.log"
    entorno = dict(os.environ, OMNICAD_PRUEBA_SALIDA=str(SALIDA), PYTHONIOENCODING="utf-8")
    if lugares > 1:
        entorno["OMNICAD_TURNOS"] = str(lugares)     # N piezas a la vez comparten los N lugares de turno.py
    python = sys.executable
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([python, str(RAIZ / "scripts" / "turno.py"), "--", python, str(PIEZAS_DIR / f"{nombre}.py")],
                           stdout=f, stderr=subprocess.STDOUT, env=entorno, cwd=RAIZ / "clon")
    texto = log.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"=== (\d+) comprobaciones, (\d+) con", texto)
    return r.returncode, (int(m.group(1)), int(m.group(2))) if m else None, log


def _informe(nombre, codigo, cuentas, log):
    """Una línea del resumen; devuelve 1 si la pieza falló."""
    if cuentas is None:
        print(f"{nombre:18s} ✗ no terminó (salida {codigo}); mirar {log.name}")
        return 1
    total, fallas = cuentas
    print(f"{nombre:18s} {total:4d} comprobaciones, {fallas:3d} con ✗   ({log.name})")
    return 1 if fallas else 0


def _tiempos_previos():
    """Segundos por pieza de la corrida anterior: el `tiempos_piezas.json` más nuevo (el propio de SALIDA o el de
    `evidencias/ui_*/`). {} si no hay ninguno o está roto."""
    candidatos = [SALIDA / TIEMPOS, *(RAIZ / "evidencias").glob(f"ui_*/{TIEMPOS}")]
    try:
        archivo = max((c for c in candidatos if c.is_file()), key=lambda c: c.stat().st_mtime)
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):      # sin candidatos (max de vacío) o JSON roto: corre sin orden conocido
        return {}


if __name__ == "__main__":
    args = sys.argv[1:]
    modo = os.environ.get("OMNICAD_PRUEBA_VENTANA", "minimizada")
    if "--ventana" in args:
        i = args.index("--ventana")
        modo = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    paralelo = 1
    if "--paralelo" in args:
        i = args.index("--paralelo")
        try:
            paralelo = int(args[i + 1]) if i + 1 < len(args) else 0
        except ValueError:
            paralelo = 0
        del args[i:i + 2]
    if paralelo < 1:
        sys.exit("--paralelo debe ser un número entero mayor o igual a 1")
    if modo not in ("minimizada", "visible"):
        sys.exit("--ventana debe ser «minimizada» o «visible»")
    os.environ["OMNICAD_PRUEBA_VENTANA"] = modo          # los hijos la heredan
    elegidas = args or PIEZAS
    for nombre in elegidas:
        if nombre not in PIEZAS:
            sys.exit(f"Pieza desconocida: {nombre}. Opciones: {', '.join(PIEZAS)}")
    print(f"Evidencia en {SALIDA}\n")
    mal = 0
    previos, tiempos = _tiempos_previos(), {}
    if paralelo == 1:
        for nombre in elegidas:                          # como siempre: de a una, en orden, imprimiendo a medida que corren
            if modo == "minimizada" and nombre in PIEZAS_CON_FOCO_REAL:
                print(f"{nombre:18s} ⚠ saltada: necesita ventana visible (--ventana visible)")
                continue
            t0 = time.monotonic()
            resultado = correr(nombre)
            tiempos[nombre] = round(time.monotonic() - t0, 1)
            mal += _informe(nombre, *resultado)
    else:
        orden = sorted(elegidas, key=lambda n: -previos.get(n, -1.0))   # la más larga primero; sin dato, al final
        resultados = {}

        def _una(nombre):
            t0 = time.monotonic()
            resultados[nombre] = correr(nombre, paralelo)
            tiempos[nombre] = round(time.monotonic() - t0, 1)

        a_correr = [n for n in orden if not (modo == "minimizada" and n in PIEZAS_CON_FOCO_REAL)]
        with ThreadPoolExecutor(max_workers=paralelo) as ex:
            list(ex.map(_una, a_correr))
        for nombre in elegidas:                          # el resumen, siempre en el orden pedido
            if modo == "minimizada" and nombre in PIEZAS_CON_FOCO_REAL:
                print(f"{nombre:18s} ⚠ saltada: necesita ventana visible (--ventana visible)")
                continue
            mal += _informe(nombre, *resultados[nombre])
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / TIEMPOS).write_text(json.dumps({**previos, **tiempos}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nLas ✗ no siempre son bugs: abrir el log, ver si es de la app o de la prueba (omnicad-test, sección 5).")
    sys.exit(1 if mal else 0)
