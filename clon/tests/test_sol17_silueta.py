"""SOL-17: División de silueta: «Solo caras», «Cuerpo vaciado» y «Cuerpo sólido»."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _volumenes(s):
    return sorted(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values())


def test_solido_parte_un_cilindro_en_dos_mitades():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30, name="Eje")
    llamar(s, "silhouette_split", body="Eje", direction="X", operation="solid_body")
    mitad = math.pi * 100 * 30 / 2
    assert _volumenes(s) == pytest.approx([mitad, mitad], rel=1e-4)
    assert all(geo.es_valida(c.forma) for c in s.doc.estado_final.cuerpos.values())
    llamar(s, "undo")
    assert len(s.doc.estado_final.cuerpos) == 1


def test_solo_caras_deja_un_cuerpo():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30, name="Eje")
    llamar(s, "silhouette_split", body="Eje", direction="X")
    assert len(s.doc.estado_final.cuerpos) == 1


def test_vaciado_exige_un_cuerpo_vaciado():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30, name="Taza")
    r = api.llamar(s, "silhouette_split", {"body": "Taza", "direction": "X", "operation": "shelled_body"})
    assert not r["ok"]
    llamar(s, "shell", body="Taza", faces=[">Z"], thickness=2)
    volumen = geo.volumen(s.cuerpo("Taza").forma)
    llamar(s, "silhouette_split", body="Taza", direction="X", operation="shelled_body")
    assert _volumenes(s) == pytest.approx([volumen / 2, volumen / 2], rel=1e-3)


def test_esfera_vista_desde_arriba_en_hemisferios():
    s = api.Sesion()
    llamar(s, "create_sphere", radius=10, name="Bola")
    llamar(s, "silhouette_split", body="Bola", direction="Z", operation="solid_body")
    assert _volumenes(s) == pytest.approx([2 / 3 * math.pi * 1000] * 2, rel=1e-3)
