"""P-153: un tamaño alejado del diámetro de la cara avisa sin impedir la rosca."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _crear_rosca(designacion=None, *, radio=23.95, modelada=True):
    sesion = api.Sesion()
    cilindro = api.llamar(sesion, "create_cylinder", {"radius": radio, "height": 6})
    assert cilindro["ok"], cilindro
    rosca = api.llamar(sesion, "create_thread", {
        "faces": "%CYLINDER", "thread": designacion, "modeled": modelada,
    })
    assert rosca["ok"], rosca
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    caja = geo.caja_envolvente(forma)
    return rosca, caja[1][0] - caja[0][0]


def test_automatico_en_cara_47_9_elige_m48_6g_sin_aviso():
    rosca, diametro = _crear_rosca()
    assert rosca["result"]["threads"][0]["designation"] == "M48x5"
    assert rosca["result"]["threads"][0]["class"] == "6g"
    assert diametro == pytest.approx(47.7, abs=0.2)
    assert rosca["avisos"] == []


def test_m60_en_cara_47_9_se_crea_y_avisa_con_coma_decimal():
    rosca, diametro = _crear_rosca("M60x5.5")
    assert diametro == pytest.approx(59.64, abs=0.05)
    assert any("M60x5.5" in aviso and "Ø47,9" in aviso and "Ø60" in aviso for aviso in rosca["avisos"])


def test_m48_en_cara_47_9_no_avisa():
    rosca, diametro = _crear_rosca("M48x5")
    assert diametro == pytest.approx(47.7, abs=0.2)
    assert rosca["avisos"] == []


@pytest.mark.parametrize("diametro_cara, avisa", [(40, False), (39.99, True), (45, True)])
def test_el_umbral_es_estrictamente_cinco_por_ciento(diametro_cara, avisa):
    rosca, diametro = _crear_rosca("M42x4.5", radio=diametro_cara / 2, modelada=False)
    assert diametro == pytest.approx(diametro_cara, abs=1e-5)
    assert bool(rosca["avisos"]) is avisa


def test_panel_avisa_al_elegir_m60_con_el_teclado():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.nucleo import referencias as refs
    from omnicad.ui import temas
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos.crear import Rosca
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_cylinder", {"radius": 23.95, "height": 6})["ok"]
    cuerpo = next(iter(sesion.doc.estado_final.cuerpos.values()))
    cara = next(c for c in refs.subformas(cuerpo.forma, "cara") if refs.firma_cara(c)["geom"] == "cilindro")
    hit = hit_desde_ref(refs.referencia(cuerpo.id, cara, cuerpo.forma), sesion.doc.estado_final)
    visor = Visor3D()
    visor.set_modelo(sesion.doc.estado_final)
    panel = PanelComando(Rosca(), ContextoComando(sesion.doc), visor, {"caras": [hit]})
    try:
        panel.show()
        combo = panel.widgets["tam_iso_metrica"]
        combo.setFocus()
        QTest.keyClicks(combo, "M60")
        QTest.keyClick(combo, Qt.Key_Tab)
        assert panel.valores["tam_iso_metrica"] == "M60"
        assert panel.valores["des_tipo_rosca"] == "auto"           # Designación automática: la primera de M60, M60x5.5
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        assert panel.mensaje.isVisible()
        assert "Ø47,9" in panel.mensaje.text() and "Ø60" in panel.mensaje.text()
        assert panel.mensaje.property("tipo") == "aviso"
        assert temas.color("aviso") in panel.mensaje.styleSheet()
        assert geo.es_valida(cuerpo.forma)
        caja = geo.caja_envolvente(cuerpo.forma)
        assert caja[1][0] - caja[0][0] == pytest.approx(47.9, abs=1e-5)
        panel.set_valor("tam_iso_metrica", "M48")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok and not panel.mensaje.isVisible()
    finally:
        panel.cancelar()
        panel.close()
        panel.deleteLater()
        visor.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("diametro_agujero, avisa", [(8.5, False), (12, True)])
def test_agujero_se_compara_con_el_diametro_menor(diametro_agujero, avisa):
    """Un agujero roscado M10 lleva el taladro de Ø8,5 (el menor: 8,38): no avisa; uno de Ø12, sí."""
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_box", {"length": 40, "width": 40, "height": 20})["ok"]
    assert api.llamar(sesion, "create_hole", {"diameter": diametro_agujero, "depth": 10, "face": ">Z"})["ok"]
    rosca = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": "M10x1.5", "modeled": False})
    assert rosca["ok"], rosca
    assert bool(rosca["avisos"]) is avisa
