# -*- coding: utf-8 -*-
"""B-425: un Patrón circular de 5000 copias tardaba 5,4 s solo en el modelo: nombrar cada copia y buscar su id recorría
todos los cuerpos (cuadrático). Con `nombres_de_copia` y el `k` de `nuevo_cuerpo` es lineal y da los mismos nombres e ids."""
import time

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_solido import OpPatron


def test_b425_patron_de_5000_copias_es_lineal_y_conserva_nombres_e_ids():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    op = OpPatron(doc.nuevo_id(), forma_patron="circular", cuerpos=["op1.c1"], eje={"tipo": "eje", "id": "Z"}, n=5000,
                  distribucion="completo")
    t = time.perf_counter()
    assert doc.agregar(op).estado == "ok"
    assert time.perf_counter() - t < 3                     # antes 5,4 s; ahora ~0,5 s
    cuerpos = doc.estado_final.cuerpos
    assert len(cuerpos) == 5000
    assert [cuerpos[f"{op.id}.c{k}"].nombre for k in (1, 2, 3, 4999)] == [
        "Cuerpo1 (copia)", "Cuerpo1 (copia 2)", "Cuerpo1 (copia 3)", "Cuerpo1 (copia 4999)"]


def test_b425_nombres_de_copia_da_lo_mismo_que_nombrar_de_a_uno():
    doc = Documento()
    for _ in range(2):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    estado = doc.estado_final
    estado.cuerpos["op2.c1"].nombre = "Cuerpo1 (copia 2)"  # un hueco ocupado: la serie lo saltea
    pedidos = ["Cuerpo1", "Cuerpo1 (copia)", "Otro", "Cuerpo1", "Cuerpo1"]
    nombrar = estado.nombres_de_copia()
    en_serie = [nombrar(n) for n in pedidos]
    de_a_uno = []
    for n in pedidos:                                      # lo de antes: cada copia ya creada cuenta para la siguiente
        de_a_uno.append(estado.nombre_de_copia(n))
        estado.nuevo_cuerpo("op9", None, nombre=de_a_uno[-1])
    assert en_serie == de_a_uno == ["Cuerpo1 (copia)", "Cuerpo1 (copia 3)", "Otro (copia)", "Cuerpo1 (copia 4)",
                                    "Cuerpo1 (copia 5)"]


# ---------------------------------------------------------------- visor: las copias que comparten geometría
@pytest.fixture
def visor():
    from PySide6.QtWidgets import QApplication

    from omnicad.ui import visor3d as vis
    QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    v.resize(800, 600)
    yield v
    v.deleteLater()


def _patron_ligero(**p):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    assert doc.agregar(OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], ligeras=True, **p)).estado == "ok"
    return doc.estado_final


def test_b425_el_visor_tesela_una_vez_y_cada_copia_queda_igual_que_teselada_aparte(visor, monkeypatch):
    from omnicad.ui import visor3d as vis
    estado = _patron_ligero(forma_patron="circular", eje={"tipo": "eje", "id": "Z"}, n=4, distribucion="completo")
    llamadas = []
    teselar = vis.teselar_cuerpo
    monkeypatch.setattr(vis, "teselar_cuerpo", lambda *a, **k: llamadas.append(1) or teselar(*a, **k))
    visor.set_modelo(estado)
    assert len(llamadas) == 1 and len(visor._mallas) == 4      # antes, una por copia
    for m, c in zip(visor._mallas, estado.cuerpos.values(), strict=True):
        v, n = teselar(c.forma, visor._deflexion(estado.cuerpos["op1.c1"].forma), visor.config.angular, False)
        assert np.allclose(m["v"], v, atol=1e-4) and np.allclose(m["n"], n, atol=1e-4)    # rotada: normales giradas
        assert np.allclose(m["seg"], vis.aristas_cuerpo(c.forma), atol=1e-4)


def test_b425_el_clic_elige_la_copia_que_esta_debajo(visor):
    estado = _patron_ligero(forma_patron="rectangular", dir1={"tipo": "eje", "id": "X"}, n1=3, d1="20 mm",
                            distribucion="espaciado")
    visor.set_modelo(estado)
    visor.vista("iso")
    visor.encuadrar()
    for c in estado.cuerpos.values():
        (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(c.forma)
        pos = visor.proyectar(np.array([(x0 + x1) / 2, (y0 + y1) / 2, z1]))      # el medio de la tapa de esa copia
        hit = visor.elegir_entidad(pos, {"cara"})
        assert hit is not None and hit["cuerpo"] == c.id
