# -*- coding: utf-8 -*-
"""
Devuelve a un archivo los finales de línea (CRLF o LF) que tenía en una revisión de git, línea por línea.

Varios archivos del repo mezclan CRLF y LF; un editor que los normaliza ensucia el diff con líneas que no cambiaron. Las
líneas iguales a las de la revisión recuperan su final original; las nuevas toman el de la línea de arriba.

Uso, desde la raíz del repo:  python scripts/restaurar_finales_de_linea.py <revisión> <archivo> [<archivo> …]
"""
import difflib
import subprocess
import sys
from pathlib import Path


def _final(linea):
    return b"\r\n" if linea.endswith(b"\r\n") else b"\n" if linea.endswith(b"\n") else b""


def restaurar(revision, ruta):
    original = subprocess.run(["git", "show", f"{revision}:{ruta.as_posix()}"], capture_output=True, check=True).stdout
    actual = ruta.read_bytes()
    lo, la = original.splitlines(keepends=True), actual.splitlines(keepends=True)
    texto = lambda lineas: [x.rstrip(b"\r\n") for x in lineas]          # noqa: E731
    salida = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, texto(lo), texto(la), autojunk=False).get_opcodes():
        if tag == "equal":
            salida += lo[i1:i2]
        elif tag in ("replace", "insert"):
            for linea in la[j1:j2]:
                fin = _final(salida[-1]) if salida else (b"\r\n" if b"\r\n" in original else b"\n")
                salida.append(linea.rstrip(b"\r\n") + (fin if _final(linea) else b""))
    nuevo = b"".join(salida)
    if nuevo != actual:
        ruta.write_bytes(nuevo)
    return nuevo != actual


if __name__ == "__main__":
    for r in sys.argv[2:]:
        print(r, "restaurado" if restaurar(sys.argv[1], Path(r)) else "sin cambios")
