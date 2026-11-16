# -*- coding: utf-8 -*-
"""Regenera `clon/omnicad/api/catalogo_atajos.py`: cada comando de la ventana con su título y su atajo de fábrica, para
que la API y la página «Atajos de teclado» de Preferencias lo usen sin importar Qt. Correr desde la raíz con el Python del
venv; `tests/test_atajos.py` falla si quedó viejo.

    clon/.venv/bin/python scripts/claves_atajos.py
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "clon"
DESTINO = RAIZ / "omnicad" / "api" / "catalogo_atajos.py"


def contenido():
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(tempfile.mkdtemp() + "/p.ini", QSettings.IniFormat)))
    filas = sorted((c, a.property("titulo"), a.property("atajo_defecto")) for c, a in v.acciones.items()
                   if a.property("atajo_defecto") is not None and a.property("titulo"))
    v.close()
    lineas = "".join(f"    {c!r}: ({t!r}, {d!r}),\n" for c, t, d in filas)
    return ('# -*- coding: utf-8 -*-\n"""Comandos de la ventana con su atajo de fábrica (GENERADO por scripts/claves_atajos.py; no se '
            'edita a mano)."""\n# clave: (título, atajo de fábrica; "" = sin atajo)\n'
            f"CATALOGO = {{\n{lineas}}}\n")


if __name__ == "__main__":
    DESTINO.write_text(contenido(), encoding="utf-8", newline="\n")
    print("escrito:", DESTINO)
    sys.stdout.flush()
    os._exit(0)           # la ventana offscreen puede caerse al salir; el archivo ya está escrito
