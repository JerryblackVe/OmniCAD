# -*- coding: utf-8 -*-
"""
Genera las imágenes «antes → después» del globo de ayuda de los comandos principales (P9).

Cada imagen sale del propio núcleo: arma la pieza con la API, aplica el comando y renderiza las dos vistas con
`get_viewport_image` (render por software). Se guardan en `clon/omnicad/recursos/ayuda/<clave>.png`, con la clave
del comando de `ui/comandos`. Sin Qt: se puede correr con cualquier plataforma.

Uso, desde la raíz del repo:  clon/.venv/Scripts/python.exe scripts/ayuda_imagenes.py [carpeta_de_salida]
"""
import sys
from io import BytesIO
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from PIL import Image, ImageDraw  # noqa: E402

from omnicad import api  # noqa: E402

ANCHO, ALTO = 200, 150


def _ok(sesion, herramienta, **args):
    r = api.llamar(sesion, herramienta, args)
    assert r["ok"], (herramienta, args, r)
    return r["result"]


def _imagen(sesion):
    r = _ok(sesion, "get_viewport_image", width=ANCHO, height=ALTO)
    return Image.open(BytesIO(r["image"].png)).convert("RGB")


def _caja():
    s = api.Sesion()
    _ok(s, "create_box", length=40, width=30, height=20)
    return s


def _boceto_rectangular(**rect):
    s = api.Sesion()
    _ok(s, "create_sketch", plane="XY")
    _ok(s, "draw_rectangle", **rect)
    return s


# clave de comando → (pieza de partida o None, función que aplica el comando)
CASOS = {
    "empalme_3d": (_caja, lambda s: _ok(s, "fillet", edges=">Z", radius=5)),
    "chaflan_3d": (_caja, lambda s: _ok(s, "chamfer", edges=">Z", distance=4)),
    "vaciado": (_caja, lambda s: _ok(s, "shell", body="Cuerpo1", faces=">Z", thickness=3)),
    "agujero": (_caja, lambda s: _ok(s, "create_hole", face=">Z", diameter=14, through_all=True)),
    "simetria_3d": (lambda: (lambda s: (_ok(s, "create_box", length=20, width=20, height=20, x=18), s)[1])(api.Sesion()),
                    lambda s: _ok(s, "mirror", bodies="Cuerpo1", plane="YZ")),
    "patron_rectangular_3d": (lambda: (lambda s: (_ok(s, "create_cylinder", radius=6, height=16), s)[1])(api.Sesion()),
                              lambda s: _ok(s, "rectangular_pattern", bodies="Cuerpo1", x_count=3, x_spacing=22,
                                            y_count=2, y_spacing=22)),
    "extruir": (None, lambda: (lambda s: (_ok(s, "extrude", sketch="Boceto1", profile=0, distance=18), s)[1])(
        _boceto_rectangular(x1=-20, y1=-15, x2=20, y2=15))),
    "revolucion": (None, lambda: (lambda s: (_ok(s, "revolve", sketch="Boceto1", profile=0, axis="sketch_y"), s)[1])(
        _boceto_rectangular(x1=8, y1=0, x2=18, y2=30))),
}


def _componer(antes, despues):
    """Las dos imágenes lado a lado con una flecha en el medio (solo `despues` si no hay `antes`)."""
    if antes is None:
        return despues
    flecha = 36
    lienzo = Image.new("RGB", (ANCHO * 2 + flecha, ALTO), (30, 33, 40))
    lienzo.paste(antes, (0, 0))
    lienzo.paste(despues, (ANCHO + flecha, 0))
    d = ImageDraw.Draw(lienzo)
    y, x0 = ALTO // 2, ANCHO + 6
    d.line([(x0, y), (x0 + flecha - 12, y)], fill=(255, 140, 0), width=3)
    d.polygon([(x0 + flecha - 12, y - 7), (x0 + flecha - 12, y + 7), (x0 + flecha - 1, y)], fill=(255, 140, 0))
    return lienzo


def generar(salida):
    salida.mkdir(parents=True, exist_ok=True)
    for clave, (partida, aplicar) in CASOS.items():
        if partida is None:                       # comandos que parten de un boceto: solo se muestra el resultado
            sesion, antes = aplicar(), None
        else:
            sesion = partida()
            antes = _imagen(sesion)
            aplicar(sesion)
        _componer(antes, _imagen(sesion)).save(salida / f"{clave}.png", optimize=True)
        print("ok", clave)
    return salida


if __name__ == "__main__":
    generar(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "clon" / "omnicad" / "recursos" / "ayuda")
