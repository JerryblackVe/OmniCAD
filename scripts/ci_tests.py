# -*- coding: utf-8 -*-
"""Corre una tanda de tests archivo por archivo, cada uno en su proceso y con tope: en CI un test trabado no se lleva
puesto el registro ni al runner (v0.2.0). Uso desde clon/: .venv/Scripts/python.exe ../scripts/ci_tests.py <parte>"""
import subprocess
import sys
from pathlib import Path

TANDAS = 6
TOPE = 900          # s por archivo


def correr(archivo):
    proceso = subprocess.Popen([sys.executable, "-m", "pytest", str(archivo), "-q", "-o", "faulthandler_timeout=300"])
    try:
        return proceso.wait(TOPE)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], check=False)     # el árbol: también el trabajador
        return "TRABADO"


def main():
    fallos = []
    for archivo in sorted(Path("tests").glob("test_*.py"))[int(sys.argv[1])::TANDAS]:
        print(f"=== {archivo.name}", flush=True)
        salida = correr(archivo)
        if salida != 0:
            print(f"=== FALLA {archivo.name}: {salida}", flush=True)
            fallos.append(f"{archivo.name}: {salida}")
    print(f"=== Fallas: {fallos or 'ninguna'}", flush=True)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
