"""Animación › Transformar componentes con la tríada en el lienzo: se tira con el ratón, escribe en los campos del
diálogo y la escena muestra el movimiento en vivo (GZ-19)."""
import numpy as np
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog
from test_animacion import qapp, ventana  # noqa: F401  (fixtures)
from test_manipuladores import _arrastrar

from omnicad.ui import animacion as an
from omnicad.ui import manipuladores as mp


def _eje_z(v, d):
    """Punto de pantalla al medio de la flecha Z de la tríada y el punto al que lleva 6 mm de movimiento."""
    g = d.asas
    tri = next(m for m in g.manips if isinstance(m, mp.Triada))
    (_, poli), = [(s, p) for s, p in tri._partes(g)[0] if s == ("eje", 2)]
    medio = poli.mean(axis=0)
    xy, ok = g.pantalla([medio, medio + [0, 0, 6]])
    assert ok.all()
    return xy[0], xy[1]


def _preparar(v):
    cid = list(v.lienzo.objetos)[0]
    v.seleccionar([cid])
    v.ir_a(0.5)
    return cid


def test_arrastrar_la_flecha_mueve_el_cuerpo_en_vivo_y_se_guarda_al_aceptar(ventana, monkeypatch):  # noqa: F811
    v = ventana
    cid = _preparar(v)
    visto = {}

    def exec_(self):
        assert self.asas is not None and v._dialogo is self and not v.cinta.isEnabled()
        a, b = _eje_z(v, self)
        _arrastrar(v.lienzo, a, b)
        visto["dZ"] = self.campos["dZ"].value()
        visto["m"] = v.lienzo.transformaciones[cid][:3, 3].copy()      # la vista previa ya movió el cuerpo
        return QDialog.Accepted
    monkeypatch.setattr(an.DialogoAccion, "exec", exec_)
    a = v.comando("transformar")
    assert visto["dZ"] == pytest.approx(6, abs=0.5)
    assert visto["m"][2] == pytest.approx(visto["dZ"], abs=0.05)
    assert a["traslacion"][2] == pytest.approx(visto["dZ"], abs=0.05)
    assert v._dialogo is None and v.cinta.isEnabled() and v.linea.isEnabled()


def test_cancelar_deja_la_escena_como_estaba(ventana, monkeypatch):  # noqa: F811
    v = ventana
    cid = _preparar(v)

    def exec_(self):
        a, b = _eje_z(v, self)
        _arrastrar(v.lienzo, a, b)
        assert not np.allclose(v.lienzo.transformaciones[cid], np.identity(4))
        return QDialog.Rejected
    monkeypatch.setattr(an.DialogoAccion, "exec", exec_)
    assert v.comando("transformar") is None
    assert v.guion.acciones == [] and np.allclose(v.lienzo.transformaciones[cid], np.identity(4))
    assert v.cinta.isEnabled()


def test_el_arco_gira_y_el_valor_escrito_mueve_la_tríada(ventana, monkeypatch):  # noqa: F811
    v = ventana
    _preparar(v)
    visto = {}

    def exec_(self):
        g = self.asas
        tri = next(m for m in g.manips if isinstance(m, mp.Triada))
        c = tri.centro.copy()
        (_, poli), = [(s, p) for s, p in tri._partes(g)[0] if s == ("giro", 2)]
        p0 = poli[len(poli) // 2]
        w = p0 - c
        t = np.radians(20)
        giro = c + np.array([w[0] * np.cos(t) - w[1] * np.sin(t), w[0] * np.sin(t) + w[1] * np.cos(t), w[2]])
        xy, ok = g.pantalla([p0, giro])
        assert ok.all()
        _arrastrar(v.lienzo, *xy)
        visto["aZ"] = self.campos["aZ"].value()
        self.campos["dX"].setValue(15)                                  # teclear mueve la tríada
        visto["centro"] = next(m for m in g.manips if isinstance(m, mp.Triada)).centro - c
        return QDialog.Accepted
    monkeypatch.setattr(an.DialogoAccion, "exec", exec_)
    a = v.comando("transformar")
    assert visto["aZ"] == pytest.approx(20, abs=1.5)
    assert visto["centro"] == pytest.approx([15, 0, 0], abs=1e-6)
    assert np.linalg.norm(a["giro"]) == pytest.approx(visto["aZ"], abs=1.5)


def test_el_dialogo_real_no_bloquea_la_ventana_y_se_cierra_con_aceptar(ventana):  # noqa: F811
    v = ventana
    cid = _preparar(v)
    visto = {}

    def con_el_dialogo_abierto():
        d = v._dialogo
        visto["abierto"] = d is not None and d.isVisible() and not d.isModal()
        v.seleccionar([])                                               # con el diálogo abierto la selección no cambia
        visto["seleccion"] = list(v.seleccion)
        a, b = _eje_z(v, d)
        _arrastrar(v.lienzo, a, b)
        d.accept()
    QTimer.singleShot(0, con_el_dialogo_abierto)
    a = v.comando("transformar")
    assert visto["abierto"] and visto["seleccion"] == [cid]
    assert a["traslacion"][2] == pytest.approx(6, abs=0.5)


def test_cerrar_la_ventana_con_el_dialogo_abierto_no_cuelga(ventana):  # noqa: F811
    v = ventana
    _preparar(v)
    QTimer.singleShot(0, v.close)
    assert v.comando("transformar") is None


def test_editar_una_accion_muestra_la_triada_y_guarda_el_cambio(ventana, monkeypatch):  # noqa: F811
    v = ventana
    cid = _preparar(v)
    a = v.agregar_accion({"tipo": "transformar", "cuerpos": [cid], "traslacion": [0, 0, 10], "inicio": 0.5, "duracion": 1})

    def exec_(self):
        assert self.asas is not None
        self.campos["dZ"].setValue(25)
        return QDialog.Accepted
    monkeypatch.setattr(an.DialogoAccion, "exec", exec_)
    v.editar_accion(a["id"])
    assert v.guion.accion(a["id"])["traslacion"][2] == pytest.approx(25)
    assert v._dialogo is None
