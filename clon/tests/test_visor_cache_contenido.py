"""P-43: se conserva la revisión del padre solo si la forma que vuelve del hijo es idéntica."""
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo, intercambio as io
from omnicad.timeline.calculo_aislado import _codificar, _decodificar
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import visor3d as vis


@pytest.fixture
def visor():
    app = QApplication.instance() or QApplication([])
    v = vis.Visor3D()
    yield v
    v.close()
    v.deleteLater()
    app.processEvents()


def documento():
    d = Documento()
    for x in (0, 50):
        d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30", x=str(x)))
    return d


def volver_del_hijo(d, monkeypatch):
    e = _decodificar(_codificar(d.estado_final))
    e.cuerpos["op1.c1"].forma = geo.caja(11, 20, 30)
    monkeypatch.setattr(d, "_prevuelo_cambio", lambda *a, **k: {
        "previa": {"estado": e, "avisos": [], "usados": []}})
    op = OpPrimitiva(d.nuevo_id(), forma="caja", ancho="11", largo="20", alto="30")
    return d.previsualizar(op)[0]


def test_huella_igual_en_otro_objeto_y_distinta_al_editar():
    d = documento()
    original = d.estado_final
    copia = _decodificar(_codificar(original))
    a, b = original.cuerpos["op1.c1"].forma, copia.cuerpos["op1.c1"].forma
    assert io.huella_visual(a) == io.huella_visual(b)
    assert io.huella_visual(a) != io.huella_visual(geo.caja(11, 20, 30))
    assert io.huella_visual(a) != io.huella_visual(geo.trasladar(a, (2, 0, 0)))
    assert io.huella_visual(a) != io.huella_visual(a.Reversed())
    assert geo.es_valida(b) and geo.volumen_exacto(b) == pytest.approx(6000)


def test_copia_del_hijo_reusa_malla_pero_no_la_forma_modificada(visor, monkeypatch):
    d = documento()
    entrada = d.estado_final
    visor.set_modelo(entrada)
    mallas = {m["id"]: m for m in visor._mallas}
    e = volver_del_hijo(d, monkeypatch)
    assert e.cuerpos["op2.c1"].forma is entrada.cuerpos["op2.c1"].forma
    assert e.cuerpos["op1.c1"].forma is not entrada.cuerpos["op1.c1"].forma
    original = vis.teselar_cuerpo
    llamadas = []

    def contar(forma, *a, **k):
        llamadas.append(forma)
        return original(forma, *a, **k)

    monkeypatch.setattr(vis, "teselar_cuerpo", contar)
    visor.set_modelo(e)
    assert llamadas == [e.cuerpos["op1.c1"].forma]
    nueva = next(m for m in visor._mallas if m["id"] == "op2.c1")
    assert nueva["v"] is mallas["op2.c1"]["v"] and nueva["n"] is mallas["op2.c1"]["n"]
    visor.set_modelo(entrada)
    assert len(llamadas) == 2  # al volver en vivo solo cambia el cuerpo editado, no el intacto


def test_editar_forma_o_detalle_no_reusa_malla_vieja(visor, monkeypatch):
    d = documento()
    visor.set_modelo(d.estado_final)
    e = volver_del_hijo(d, monkeypatch)
    modificada = e.cuerpos["op1.c1"].forma
    assert geo.volumen_exacto(modificada) == pytest.approx(6600)
    assert geo.es_valida(modificada)
    visor.set_modelo(e)
    esperada = vis.teselar_cuerpo(modificada, visor._deflexion(modificada), visor.config.angular, False)
    assert np.allclose(visor._mallas[0]["v"], esperada[0])
    assert np.allclose(visor._mallas[0]["n"], esperada[1])
    visor.invalidar_teselado()
    visor.set_modelo(e)
    assert np.allclose(visor._mallas[0]["v"], esperada[0])
