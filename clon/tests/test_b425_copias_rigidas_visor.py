# -*- coding: utf-8 -*-
"""B-425: con copias rígidas (sin «Copias ligeras») el visor teselaba cada copia en el hilo de la ventana (2000 copias:
28 s). Ahora mueve la malla del original; sin el registro de la copia, tesela como siempre."""
import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline import ops_solido  # noqa: I001 — después de operaciones (orden de carga de timeline)
from omnicad.timeline.ops_solido import OpPatron


@pytest.fixture
def visor():
    from PySide6.QtWidgets import QApplication

    from omnicad.ui import visor3d as vis
    QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    v.resize(800, 600)
    yield v
    v.deleteLater()


def _patron_rigido(**p):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="20", operacion="cortar",
                            objetivo="op1.c1"))                          # el original ya modificado por un corte
    assert doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], **p)).estado == "ok"
    return doc.estado_final


def test_b425_copias_rigidas_una_teselada_iguales_a_teselar_aparte_y_clic(visor, monkeypatch):
    from omnicad.ui import visor3d as vis
    estado = _patron_rigido(forma_patron="rectangular", dir1={"tipo": "eje", "id": "X"}, n1=3, d1="20 mm",
                            distribucion="espaciado")
    llamadas, teselar = [], vis.teselar_cuerpo
    monkeypatch.setattr(vis, "teselar_cuerpo", lambda *a, **k: llamadas.append(1) or teselar(*a, **k))
    visor.set_modelo(estado)
    assert len(llamadas) == 1 and len(visor._mallas) == 3
    defl = visor._deflexion(estado.cuerpos["op1.c1"].forma)
    for m, c in zip(visor._mallas, estado.cuerpos.values(), strict=True):
        v, _n = teselar(c.forma, defl, visor.config.angular, False)
        assert np.allclose(np.sort(m["v"], axis=0), np.sort(v, axis=0), atol=1e-4)
        assert np.allclose(m["seg"].min(0), vis.aristas_cuerpo(c.forma).min(0), atol=1e-4)
    visor.vista("iso")
    visor.encuadrar()
    for c in estado.cuerpos.values():
        (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(c.forma)
        hit = visor.elegir_entidad(visor.proyectar(np.array([x0 + 0.5, (y0 + y1) / 2, z1])), {"cara"})
        assert hit is not None and hit["cuerpo"] == c.id                 # el clic elige la copia que está debajo


def test_b425_sin_registro_la_copia_se_tesela_como_siempre(visor, monkeypatch):
    from omnicad.ui import visor3d as vis
    estado = _patron_rigido(forma_patron="circular", eje={"tipo": "eje", "id": "Z"}, n=3, distribucion="completo")
    llamadas, teselar = [], vis.teselar_cuerpo
    monkeypatch.setattr(vis, "teselar_cuerpo", lambda *a, **k: llamadas.append(1) or teselar(*a, **k))
    monkeypatch.setattr(ops_solido, "COPIAS_RIGIDAS", {})
    visor.set_modelo(estado)
    assert len(llamadas) == 3 and len(visor._mallas) == 3
