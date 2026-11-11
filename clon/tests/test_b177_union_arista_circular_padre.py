# -*- coding: utf-8 -*-
"""B-177: una unión con origen en una arista circular gira igual aunque el componente padre esté girado."""
import numpy as np

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **argumentos):
    resultado = api.llamar(sesion, nombre, argumentos)
    assert resultado["ok"], resultado
    return resultado["result"]


def _arista_circular(sesion, cuerpo, eje, signo):
    aristas = [a for a in _llamar(sesion, "find_edges", body=cuerpo)["edges"] if a.get("type") == "circle"]
    return max(aristas, key=lambda a: signo * a["center"][eje])["id"]


def test_el_giro_de_la_hija_no_depende_del_giro_del_padre():
    s = api.Sesion()
    _llamar(s, "create_box", length=200, width=200, height=10, z=-10, name="Base")
    _llamar(s, "create_component", bodies=["Base"], name="BASE", grounded=True)
    _llamar(s, "create_cylinder", height=50, radius=20, name="Col")
    _llamar(s, "create_component", bodies=["Col"], name="COL")
    _llamar(s, "create_cylinder", height=20, radius=10, x=100, y=40, plane="XZ", name="Eje")   # eje en Y
    _llamar(s, "create_box", length=10, width=10, height=40, x=100, z=40, name="Palanca")
    _llamar(s, "create_component", bodies=["Eje", "Palanca"], name="ARM", parent="COL")
    _llamar(s, "create_as_built_joint", origin=_arista_circular(s, "Col", 2, -1), body="Col", component2="BASE",
            joint_type="revolute", name="J1")
    _llamar(s, "create_as_built_joint", origin=_arista_circular(s, "Eje", 1, 1), body="Eje", component2="COL",
            joint_type="revolute", name="J2")
    vistos = []
    for grados in (0, 50, 90):     # pasados los 45° el eje del mundo más alineado deja de ser Y
        _llamar(s, "drive_joint", joint="J1", rotation=grados)
        _llamar(s, "drive_joint", joint="J2", rotation=40)
        palanca = next(c for c in s.doc.estado_final.cuerpos.values() if c.nombre == "Palanca")
        a, b = (np.array(p) for p in geo.caja_envolvente(palanca.forma))
        t = np.radians(-grados)
        deshacer_padre = np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
        vistos.append(deshacer_padre @ ((a + b) / 2))
    assert np.allclose(vistos, vistos[0], atol=1e-6), vistos
