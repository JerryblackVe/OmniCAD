# -*- coding: utf-8 -*-
"""B-842: Cara de desfase sobre cadenas abiertas de paredes de una extrusión."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm


def _ok(sesion, herramienta, args):
    respuesta = api.llamar(sesion, herramienta, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _cuerpo_mixto():
    """Dos arcos y dos paredes planas tangentes; una cara mínima corta la cadena antes de cerrarla."""
    sesion = api.Sesion()
    entidades = [
        {"type": "arc", "center": [0, 0], "start": [10, 0], "sweep": 180},
        {"type": "line", "start": [-10, 0], "end": [-10, -10]},
        {"type": "arc", "center": [0, -10], "start": [-10, -10], "sweep": 180},
        {"type": "line", "start": [10, -10], "end": [10, -0.15]},
        {"type": "line", "start": [10, -0.15], "end": [10.1, 0]},
        {"type": "line", "start": [10.1, 0], "end": [10, 0]},
    ]
    _ok(sesion, "sketch_from_spec", {"plane": "XY", "name": "Perfil", "entities": entidades})
    _ok(sesion, "extrude", {"sketch": "Perfil", "profile": 0, "distance": 3})
    return sesion


def _cadena(sesion):
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    curva = next(c for c in geo.caras(forma) if sm._plano_de_cara(c) is None)
    return forma, sm.caras_en_cadena(forma, [curva], coplanares=False)


def _cara_cilindrica(sesion):
    caras = _ok(sesion, "find_faces", {"body": "Cuerpo1"})["faces"]
    return next(c["id"] for c in caras if c["type"] == "cylinder")


def test_cadena_abierta_mixta_negativa_por_contorno():
    sesion = _cuerpo_mixto()
    forma, caras = _cadena(sesion)
    assert len(caras) == 4                   # dos cilindros y dos planos; la cara mínima queda afuera
    resultado = sm._desfase_por_contorno(forma, caras, -0.3)
    assert resultado is not None and geo.es_valida(resultado) and len(geo.solidos(resultado)) == 1
    cambio = geo.volumen_exacto(resultado) - geo.volumen_exacto(forma)
    assert cambio == pytest.approx(-0.3 * sum(geo.area(c) for c in caras), rel=0.1)


def test_cadena_abierta_positiva_sobre_un_cuerpo_ya_desfasado():
    sesion = _cuerpo_mixto()
    _ok(sesion, "offset_faces", {"faces": _cara_cilindrica(sesion), "distance": -0.3, "tangent": True})
    forma, caras = _cadena(sesion)
    antes = geo.volumen_exacto(forma)
    _ok(sesion, "offset_faces", {"faces": _cara_cilindrica(sesion), "distance": 0.5, "tangent": True})
    resultado = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(resultado) and len(geo.solidos(resultado)) == 1
    cambio = geo.volumen_exacto(resultado) - antes
    assert cambio == pytest.approx(0.5 * sum(geo.area(c) for c in caras), rel=0.15)


@pytest.mark.parametrize("distancia, cambio", [(0.5, 102.5), (-0.5, -97.5)])
def test_cadena_abierta_de_caras_planas(distancia, cambio):
    caja = geo.caja(10, 10, 10)
    este = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[0])
    norte = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[1])
    resultado = sm._desfase_por_contorno(caja, [este, norte], distancia)
    assert resultado is not None and geo.es_valida(resultado)
    assert geo.volumen_exacto(resultado) - 1000 == pytest.approx(cambio)
