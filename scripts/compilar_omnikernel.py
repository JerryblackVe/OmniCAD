# -*- coding: utf-8 -*-
"""Compila el binding sin escribir Cargo.lock ni target en el repo del kernel.

Las fuentes verificadas por SHA-256 se copian a evidencias/ (fuera de git).
El kernel original no se modifica. Usa el cargo y maturin ya instalados.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


def preparar(origen, destino):
    for nombre in ("Cargo.toml", "rust-toolchain.toml"):
        shutil.copy2(origen / nombre, destino / nombre)
    for crate in ("kernel", "omnikernel_py"):
        fuente = origen / "crates" / crate
        copia = destino / "crates" / crate
        shutil.copytree(fuente, copia, dirs_exist_ok=True, ignore=shutil.ignore_patterns("target", "__pycache__"))
        for archivo in fuente.rglob("*"):
            if archivo.is_file() and "target" not in archivo.relative_to(fuente).parts:
                relativo = archivo.relative_to(fuente)
                assert hashlib.sha256(archivo.read_bytes()).digest() == hashlib.sha256((copia / relativo).read_bytes()).digest()


def main():
    raiz = Path(__file__).resolve().parents[1]
    origen = Path("D:/rea/cad/rust-kernel")
    destino = raiz / "evidencias" / "motor_omnikernel" / "compilacion"
    destino.mkdir(parents=True, exist_ok=True)
    preparar(origen, destino)
    entorno = dict(os.environ, PYO3_PYTHON=sys.executable, VIRTUAL_ENV=str(Path(sys.executable).parents[1]),
                   PYTHONIOENCODING="utf-8")
    comando = (["cargo", "test", "-p", "omnikernel_py"] if "--test" in sys.argv else
               [sys.executable, "-m", "maturin", "develop", "--release", "--manifest-path",
                str(destino / "crates" / "omnikernel_py" / "Cargo.toml")])
    return subprocess.call(comando, cwd=destino, env=entorno)


if __name__ == "__main__":
    sys.exit(main())
