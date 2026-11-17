"""B-616: el Vaciado de un barrido empalmado (sin Cadena tangente) da OPERATION_FAILED y se deshace.

El caso es el de B-536: un círculo de r5 barrido por una spline y empalmado en todas las aristas; al quitar una tapa
con 1 mm de espesor y Cadena tangente desmarcada, el kernel devuelve el cuerpo sin tocar y el plan B no lo salva.
"""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


@pytest.mark.xfail(strict=True, reason="B-616")
def test_vaciado_de_un_barrido_empalmado_sin_cadena_tangente():
    sesion = api.Sesion()
    for nombre, args in (("create_sketch", {"plane": "XY", "name": "perfil"}), ("draw_circle", {"radius": 5}),
                         ("create_sketch", {"plane": "XZ", "name": "ruta"}),
                         ("draw_spline", {"points": [[0, 0], [30, 10], [60, 0], [90, 10]]}),
                         ("sweep", {"sketch": "perfil", "path_sketch": "ruta"}),
                         ("fillet", {"body": "Cuerpo1", "edges": "all", "radius": 1})):
        assert api.llamar(sesion, nombre, args)["ok"], nombre
    tapa = [f["id"] for f in api.llamar(sesion, "find_faces", {})["result"]["faces"] if f["type"] == "plane"][0]
    antes = geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    r = api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": [tapa], "thickness": 1, "tangent_chain": False})
    assert r["ok"], r
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and 0 < geo.volumen(forma) < antes
