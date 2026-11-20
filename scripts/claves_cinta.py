# -*- coding: utf-8 -*-
"""Regenera `clon/omnicad/api/catalogo_cinta.py`: las secciones de la cinta (pestaña/grupo) con sus botones de fábrica,
para que la API y la página «Cinta» de Preferencias las usen sin importar Qt. Correr desde la raíz con el Python del
venv; `tests/test_cinta_personal.py` falla si quedó viejo.

    clon/.venv/bin/python scripts/claves_cinta.py
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "clon"
DESTINO = RAIZ / "omnicad" / "api" / "catalogo_cinta.py"


def contenido():
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from omnicad.ui.cinta import CONTEXTUALES, FAVORITAS, PESTANAS
    secciones = {f"{FAVORITAS[0]}/{FAVORITAS[1]}": []}
    for pestana, grupos in [*PESTANAS, *CONTEXTUALES]:     # P-187: BOCETO también se personaliza
        for titulo, rapidos, _items in grupos:
            secciones[f"{pestana}/{titulo}"] = [r for r in rapidos if isinstance(r, str)]
    lineas = "".join(f"    {k!r}: {v!r},\n" for k, v in secciones.items())
    import tempfile
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(tempfile.mkdtemp() + "/p.ini", QSettings.IniFormat)))
    usadas = sorted(c for c, a in v.acciones.items() if c.startswith("sk_") and a.property("titulo"))
    titulos = "".join(f"    {c!r}: {v.acciones[c].property('titulo')!r},\n" for c in usadas)
    v.close()
    return ('# -*- coding: utf-8 -*-\n"""Secciones de la cinta con sus botones de fábrica (GENERADO por scripts/claves_cinta.py; no se '
            'edita a mano)."""\n# «PESTAÑA/GRUPO»: [claves de los botones grandes, en orden]\n'
            f"SECCIONES = {{\n{lineas}}}\n"
            "# Título de los comandos del boceto (sk_*) que llevan botón: no están en catalogo_atajos (sus teclas son del boceto)\n"
            f"TITULOS_BOCETO = {{\n{titulos}}}\n")


if __name__ == "__main__":
    DESTINO.write_text(contenido(), encoding="utf-8", newline="\n")
    print("escrito:", DESTINO)
