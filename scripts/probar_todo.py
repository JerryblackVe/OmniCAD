#!/usr/bin/env python3
"""Corre todas las pruebas automáticas de a una y deja un informe.

Uso, desde clon/ con el Python del venv:
  ../scripts/probar_todo.py --rapido
  ../scripts/probar_todo.py --noche [--horas 6] [--seguir]

Cada paso es un subprocess con cwd=clon/ y se ejecuta de a uno. Los scripts
propios ya hacen fila con turno.py por dentro, así que no se los envuelve.
El informe queda en evidencias/probar_todo_<fecha>/informe.md (o en la carpeta
indicada por OMNICAD_PROBAR_TODO_DIR).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLON = RAIZ / "clon"
FINALES = ("ok", "fallo", "saltado")


def _python_venv():
    """Devuelve el intérprete del venv de clon/ (o el del repo principal, si esto es un worktree) o, si no hay, el actual."""
    clones = [CLON]
    try:  # un worktree no tiene venv propio: usa el del repo principal, como scripts/worktree_item.sh
        comun = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--git-common-dir"],
                               capture_output=True, text=True, check=True).stdout.strip()
        clones.append((RAIZ / comun).resolve().parent / "clon")
    except (OSError, subprocess.CalledProcessError):
        pass
    for clon in clones:
        for relativo in (Path(".venv/Scripts/python.exe"), Path(".venv/bin/python")):
            if (clon / relativo).exists():
                return str(clon / relativo)
    return sys.executable


def _rel(ruta):
    """Ruta de un archivo de la raíz del repo, relativa a clon/."""
    return os.path.relpath(str(ruta), str(CLON))


def pasos(modo, horas):
    """Devuelve la lista de (nombre, comando) del modo pedido.

    Un comando None marca un paso que se salta (el script no existe).
    """
    python = _python_venv()
    caza = _rel(RAIZ / "scripts" / "caza" / "cazar.py")
    if modo == "rapido":
        return [
            ("caza_rapida", [python, caza, "rapida"]),
            ("tests_afectados", [python, _rel(RAIZ / "scripts" / "tests_afectados.py"), "--correr"]),
        ]
    registro = RAIZ / "scripts" / "registro_bugs.py"
    ventana = [python, _rel(RAIZ / "scripts" / "prueba_ui" / "todo.py")]
    if sys.platform.startswith("linux"):
        ventana = ["xvfb-run", "-a", *ventana]
    return [
        ("registro_bugs", [python, _rel(registro)] if registro.exists() else None),
        ("caza_noche", [python, caza, "noche", "--horas", str(horas)]),
        ("prueba_ventana", ventana),
        ("cierre_completo", ["bash", _rel(RAIZ / "scripts" / "cierre_completo.sh")]),
    ]


def _leer_estado(carpeta):
    ruta = carpeta / "estado.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _guardar_estado(carpeta, estado):
    estado["actualizado"] = datetime.now().isoformat(timespec="seconds")
    (carpeta / "estado.json").write_text(
        json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _escribir_informe(carpeta, estado, nombres):
    hechos = estado.get("pasos", {})
    filas = []
    fallos = []
    for nombre in nombres:
        info = hechos.get(nombre)
        if not info:
            filas.append(f"| {nombre} | pendiente | - | - |")
            continue
        resultado = info.get("resultado", "?")
        filas.append(
            f"| {nombre} | {resultado} | {float(info.get('duracion', 0)):.1f} s | {info.get('log', '')} |"
        )
        if resultado == "fallo":
            fallos.append(f"- **{nombre}**: {info.get('detalle', '')} (log: {info.get('log', '')})")
    modo = "noche" if "cierre_completo" in nombres else "rapido"
    texto = [
        "# Informe de pruebas automáticas",
        "",
        f"- Fecha: {datetime.now().strftime('%Y-%m-%d')}",
        f"- Modo: {modo}",
        f"- Carpeta: {carpeta}",
        "",
        "| paso | resultado | duración | detalle |",
        "|---|---|---|---|",
        *filas,
        "",
        "## Fallos",
        "",
        *(fallos or ["Ninguno."]),
        "",
    ]
    (carpeta / "informe.md").write_text("\n".join(texto), encoding="utf-8")


def _correr(nombre, comando, carpeta):
    log = carpeta / f"{nombre}.log"
    env = os.environ.copy()
    if nombre == "prueba_ventana":
        env["OMNICAD_PRUEBA_VENTANA"] = "minimizada"
    inicio = time.monotonic()
    codigo = 0
    with log.open("w", encoding="utf-8") as salida:
        salida.write(f"$ {' '.join(comando)}\n\n")
        salida.flush()
        try:
            proceso = subprocess.run(
                comando, cwd=str(CLON), stdout=salida, stderr=subprocess.STDOUT, env=env
            )
            codigo = proceso.returncode
        except Exception as exc:
            codigo = -1
            salida.write(f"\nNo se pudo lanzar: {type(exc).__name__}: {exc}\n")
    duracion = round(time.monotonic() - inicio, 2)
    detalle = "código 0" if codigo == 0 else f"terminó con código {codigo}"
    return {
        "resultado": "ok" if codigo == 0 else "fallo",
        "duracion": duracion,
        "detalle": detalle,
        "log": str(log),
    }


def ejecutar(pasos, carpeta, seguir):
    """Corre los pasos de a uno, guarda estado.json e informe.md. Devuelve 0 o 1."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    estado = _leer_estado(carpeta) if seguir else {}
    hechos = estado.get("pasos")
    if not isinstance(hechos, dict):
        hechos = {}
    estado["pasos"] = hechos
    nombres = [nombre for nombre, _ in pasos]
    _escribir_informe(carpeta, estado, nombres)
    for indice, (nombre, comando) in enumerate(pasos, 1):
        previo = hechos.get(nombre)
        if seguir and previo and previo.get("resultado") in FINALES:
            print(f"[{indice}/{len(pasos)}] {nombre}: ya terminado ({previo['resultado']}), se omite")
            continue
        if comando is None:
            log = carpeta / f"{nombre}.log"
            log.write_text("Saltado: el script no existe.\n", encoding="utf-8")
            hechos[nombre] = {
                "resultado": "saltado",
                "duracion": 0.0,
                "detalle": "el script no existe",
                "log": str(log),
            }
            print(f"[{indice}/{len(pasos)}] {nombre}: saltado (el script no existe)")
        else:
            hechos[nombre] = _correr(nombre, comando, carpeta)
            info = hechos[nombre]
            print(
                f"[{indice}/{len(pasos)}] {nombre}: {info['resultado']} "
                f"({info['duracion']:.1f} s) -> {info['log']}"
            )
        _guardar_estado(carpeta, estado)
        _escribir_informe(carpeta, estado, nombres)
    fallidos = [n for n in nombres if hechos.get(n, {}).get("resultado") == "fallo"]
    print(f"Informe: {carpeta / 'informe.md'}")
    return 1 if fallidos else 0


def _carpeta_informe():
    destino = os.environ.get("OMNICAD_PROBAR_TODO_DIR")
    if destino:
        ruta = Path(destino)
        return ruta if ruta.is_absolute() else RAIZ / ruta
    return RAIZ / "evidencias" / f"probar_todo_{datetime.now().strftime('%Y-%m-%d')}"


def main(argv=None):
    analizador = argparse.ArgumentParser(
        description="Corre todas las pruebas automáticas de a una y deja un informe."
    )
    grupo = analizador.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--rapido", action="store_true", help="caza rápida y tests afectados")
    grupo.add_argument("--noche", action="store_true", help="registro, caza de noche, ventana y cierre")
    analizador.add_argument("--horas", type=int, default=6, help="horas de la caza de noche (6)")
    analizador.add_argument("--seguir", action="store_true", help="retoma desde el primer paso sin terminar")
    args = analizador.parse_args(argv)
    modo = "rapido" if args.rapido else "noche"
    return ejecutar(pasos(modo, args.horas), _carpeta_informe(), args.seguir)


if __name__ == "__main__":
    sys.exit(main())
