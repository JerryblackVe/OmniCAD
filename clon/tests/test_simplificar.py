# -*- coding: utf-8 -*-
"""Eliminar operaciones (PLA-9: «Remove Features» de Fusion): empalmes, chaflanes y agujeros chicos
de una vez con un tamaño máximo."""
import math

import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo.simplificar import detectar, quitar_operaciones
from omnicad.nucleo.solidos_modificar import empalme
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_modificar import OpChaflan, OpEmpalme, OpEliminarOperaciones

_AGUJERO = math.pi * 4 * 20                    # Ø4 pasante por 20 de alto
_CHAFLAN = 10.0                                # el prisma de la esquina: 1 × 1 / 2 por 20 de alto


def _aristas(forma, largo):
    return [e for e in refs.subformas(forma, "arista")
            if refs.firma_arista(e)["geom"] == "linea" and abs(refs.firma_arista(e)["largo"] - largo) < 1e-6]


def _prisma_de_esquina(x, y, dx, dy, alto):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    from OCP.gp import gp_Pnt
    triangulo = BRepBuilderAPI_MakePolygon()
    for p in ((x, y, 0), (x + dx, y, 0), (x, y + dy, 0)):
        triangulo.Add(gp_Pnt(*p))
    triangulo.Close()
    return geo.trasladar(geo.extruir([BRepBuilderAPI_MakeFace(triangulo.Wire()).Face()], (0, 0, 1), alto),
                         (0, 0, 20 - alto))       # entra 1 mm en el cuerpo desde la cara de arriba


def _chaflanada():
    """Caja 40 × 30 × 20 con un chaflán 1 × 1 en una esquina vertical y nada más."""
    return geo.booleano(geo.caja(40, 30, 20), _prisma_de_esquina(-1, -1, 3, 3, 21), "cortar")


def _con_agujero(forma, x, y):
    return geo.booleano(forma, sc.agujero(forma, (x, y, 20), (0, 0, -1), diametro=4), "cortar")


def _pieza():
    """La caja con un empalme R2 en una arista vertical, un chaflán 1 en otra esquina y un agujero
    Ø4 pasante en el centro de arriba."""
    base = _chaflanada()
    forma = empalme(base, [{"aristas": _aristas(base, 20)[:1], "tipo": "constante", "radio": 2.0}])
    return _con_agujero(forma, 10, 7)


def _comando_de_pieza():
    """Una pieza armada con los pasos del timeline (como la haría el usuario): una caja con un
    chaflán 1 en una esquina vertical y un empalme R2 en la arista vertical de al lado."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    cid = next(iter(doc.estado_final.cuerpos))
    v = _aristas(geo.caja(40, 30, 20), 20)
    doc.agregar(OpChaflan(doc.nuevo_id(), "Chaflan1", distancia1="1 mm",
                          aristas=[refs.referencia(cid, v[0], doc.estado_final.cuerpos[cid].forma)]))
    doc.agregar(OpEmpalme(doc.nuevo_id(), "Empalme1", radio="2 mm",
                          aristas=[refs.referencia(cid, v[3], doc.estado_final.cuerpos[cid].forma)]))
    return doc


def test_sin_filtro_quita_empalme_chaflan_y_agujero_y_vuelve_a_la_caja():
    pieza = _pieza()
    assert geo.es_valida(pieza) and 23700 < geo.volumen(pieza) < 24000 - _AGUJERO
    encontrados = detectar(pieza, 5)
    assert {t: len(g) for t, g in encontrados.items()} == {"empalme": 1, "chaflan": 1, "agujero": 1}
    nueva, cuantas = quitar_operaciones(pieza, 5.0)
    assert cuantas == {"empalme": 1, "chaflan": 1, "agujero": 1}
    assert geo.es_valida(nueva) and geo.volumen(nueva) == pytest.approx(24000)
    assert len(refs.subformas(nueva, "cara")) == 6


def test_solo_agujero_sube_solo_lo_del_agujero():
    pieza = _pieza()
    nueva, cuantas = quitar_operaciones(pieza, 5.0, ["agujero"])
    assert cuantas == {"empalme": 0, "chaflan": 0, "agujero": 1}
    assert geo.es_valida(nueva)
    assert geo.volumen(nueva) == pytest.approx(geo.volumen(pieza) + _AGUJERO)
    assert geo.volumen(nueva) < 24000 - 0.1                          # el empalme y el chaflán siguen ahí


def test_tamano_1_5_deja_el_empalme_de_2_y_el_agujero_de_4():
    pieza = _pieza()
    encontrados = detectar(pieza, 1.5)
    assert not encontrados["empalme"] and not encontrados["agujero"] and len(encontrados["chaflan"]) == 1
    nueva, cuantas = quitar_operaciones(pieza, 1.5)
    assert cuantas == {"empalme": 0, "chaflan": 1, "agujero": 0}
    assert geo.es_valida(nueva)
    assert geo.volumen(nueva) == pytest.approx(geo.volumen(pieza) + _CHAFLAN)
    assert geo.volumen(nueva) < 24000 - 0.1                          # el empalme y el agujero siguen ahí


def test_el_chaflan_de_la_herramienta_tambien_se_quita():
    """El chaflán del árbol del modelo (herramienta de chaflán, 1 × 1 en una esquina vertical), no solo el cortado a mano."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    cid = next(iter(doc.estado_final.cuerpos))
    forma = doc.estado_final.cuerpos[cid].forma
    arista = next(e for e in _aristas(forma, 20) if refs.firma_arista(e)["medio"] == [0.0, 0.0, 10.0])
    doc.agregar(OpChaflan(doc.nuevo_id(), "Chaflan1", distancia1="1 mm",
                          aristas=[refs.referencia(cid, arista, forma)]))
    nueva, cuantas = quitar_operaciones(doc.estado_final.cuerpos[cid].forma, 1.5, ["chaflan"])
    assert cuantas == {"empalme": 0, "chaflan": 1, "agujero": 0}
    assert geo.es_valida(nueva) and geo.volumen(nueva) == pytest.approx(24000)


def test_sin_nada_para_quitar_falla_y_el_tipo_invalido_tambien():
    with pytest.raises(geo.ErrorGeometria, match="No se encontraron"):
        quitar_operaciones(geo.caja(40, 30, 20), 5.0)
    with pytest.raises(geo.ErrorGeometria, match="Tipo de operación desconocido"):
        detectar(geo.caja(40, 30, 20), 5.0, ["rosca"])


def test_la_operacion_del_timeline_quita_y_avisa_por_tipo():
    doc = _comando_de_pieza()
    cid = next(iter(doc.estado_final.cuerpos))
    assert geo.volumen(doc.estado_final.cuerpos[cid].forma) < 24000 - 0.1
    res = doc.agregar(OpEliminarOperaciones(doc.nuevo_id(), "Eliminar1", cuerpos=[cid], tamano="5 mm"))
    assert res.estado in ("ok", "aviso"), res.mensaje
    assert geo.es_valida(doc.estado_final.cuerpos[cid].forma)
    assert geo.volumen(doc.estado_final.cuerpos[cid].forma) == pytest.approx(24000)
    assert "empalme" in res.mensaje and "chaflan" in res.mensaje
