# -*- coding: utf-8 -*-
"""Regenera `clon/omnicad/api/claves_comandos.py`: las claves de los comandos de la ventana, para que la API las
compruebe sin importar Qt. Correr desde la raíz con el Python del venv; `tests/test_claves_comandos.py` falla si quedó viejo.

    clon/.venv/Scripts/python.exe scripts/claves_comandos.py
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "clon"
DESTINO = RAIZ / "omnicad" / "api" / "claves_comandos.py"


def contenido():
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from omnicad.ui.comandos import CATALOGO
    lineas = "".join(f'    "{k}",\n' for k in sorted(CATALOGO))
    return ('# -*- coding: utf-8 -*-\n"""Claves de los comandos de la ventana (GENERADO por scripts/claves_comandos.py; no se edita a mano)."""\n'
            f"CLAVES = frozenset({{\n{lineas}}})\n")


if __name__ == "__main__":
    DESTINO.write_text(contenido(), encoding="utf-8", newline="\n")
    print("escrito:", DESTINO)
