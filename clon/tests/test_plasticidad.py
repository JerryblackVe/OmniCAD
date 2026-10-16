# -*- coding: utf-8 -*-
"""PL4 (Plasticity › «Fillet Order of Operations»): el error de empalme enseña el orden correcto
(de lo grande a lo chico) y move_feature deja reordenar los pasos para seguir la pista."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.solidos_modificar import empalme
from omnicad.timeline.operaciones import OpPrimitiva


def _caja(doc):
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    return doc.estado_final.cuerpos["c1"].forma


def test_el_empalme_imposible_ensenia_el_orden_de_lo_grande_a_lo_chico():
    from omnicad.nucleo import referencias as refs
    caja = geo.caja(40, 40, 20)
    aristas = refs.subformas(caja, "arista")[:4]
    with pytest.raises(geo.ErrorGeometria) as e:
        empalme(caja, [{"aristas": aristas, "tipo": "constante", "radio": 500.0}])
    assert "radio MAYOR" in str(e.value) and "de lo grande a lo chico" in str(e.value)
    assert "reordená los empalmes" in str(e.value)


def test_la_pista_llega_por_la_api_y_move_feature_reordena():
    sesion = api.Sesion()
    doc = sesion.doc
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    r = api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 500})
    assert not r["ok"] and "de lo grande a lo chico" in r["mensaje"]

    # move_feature (la herramienta nueva que hace la pista accionable): el primitivo pasa al final.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="5"))
    r = api.llamar(sesion, "move_feature", {"feature": "op1", "index": 1})
    assert r["ok"] and r["result"]["before"] == 0 and r["result"]["now"] == 1
    assert doc.operaciones[0].TIPO == "primitiva" and "op1" != doc.operaciones[0].id
    r = api.llamar(sesion, "move_feature", {"feature": "no-hay", "index": 0})
    assert not r["ok"] and r["error_kind"] == "FEATURE_NOT_FOUND"
