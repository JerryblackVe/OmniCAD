"""GZ-26: el radio de Rosca cambia el Tamaño desde el visor y desde su caja flotante."""
import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import solidos_crear as sc
from omnicad.ui import manipuladores as mp
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def perno(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_cylinder", {"radius": 10, "height": 20, "name": "Perno"})["ok"]
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    ventana.resize(1300, 850)
    ventana.show()
    try:
        QTest.qWait(200)
        ventana.acciones["vista_frente"].trigger()
        ventana.visor.encuadrar()
        QTest.qWait(100)
        panel = ventana.ejecutar_comando(CATALOGO["rosca"]())
        assert panel.manipuladores.manips == []
        forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
        cara = next(c for c in refs.subformas(forma, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
        punto = ventana.visor.proyectar(np.array(refs.firma_cara(cara)["centro"])).toPoint()
        QTest.mouseClick(ventana.visor, Qt.LeftButton, pos=punto)
        assert panel.valores["caras"]
        yield ventana, panel
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        sesion.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def _asa(panel):
    return next(m for m in panel.manipuladores.manips if isinstance(m, mp.AsaTamanoRosca))


def _previa_sana(panel):
    estados = []
    panel.previa.connect(estados.append)
    try:
        panel._t_previa.stop()
        panel._calcular_previa()
        for _ in range(500):
            if not panel._previa_aparte:
                break
            QTest.qWait(20)
        assert panel._previa_ok, panel.mensaje.text()
        assert estados and estados[-1] is not None
        forma = next(iter(estados[-1].cuerpos.values())).forma
        assert geo.es_valida(forma) and geo.volumen(forma) > 0
        return forma
    finally:
        panel.previa.disconnect(estados.append)


@pytest.mark.parametrize("completa", [True, False])
def test_asa_tamano_con_y_sin_longitud_completa(perno, completa):
    _, panel = perno
    panel.set_valor("largo_completo", completa)
    panel.set_valor("desfase", "3 mm")
    gestor = panel.manipuladores
    assert [m.clave for m in gestor.manips] == (["tam_iso_metrica"] if completa else
                                               ["desfase", "longitud", "tam_iso_metrica"])
    asa = _asa(panel)
    assert isinstance(asa, mp.AsaRadial)
    assert np.linalg.norm(asa.puntos(gestor)[0] - asa.origen) == pytest.approx(10)       # tamaño automático: el radio de la cara
    panel.set_valor("tam_iso_metrica", "M20")
    assert asa.puntos(gestor)[0][2] == pytest.approx(0 if completa else 3)
    assert np.linalg.norm(asa.puntos(gestor)[0] - asa.origen) == pytest.approx(9.895, abs=1e-3)   # como Fusion: 6g, no el nominal
    panel.set_valor("tam_iso_metrica", "M24")
    assert np.linalg.norm(_asa(panel).puntos(gestor)[0] - asa.origen) == pytest.approx(11.882, abs=1e-3)
    assert gestor.cajas["tam_iso_metrica"].text() == "11,882"
    _previa_sana(panel)


@pytest.mark.parametrize("completa", [True, False])
def test_arrastre_real_del_radio_cambia_tamano_y_conserva_previa(perno, completa):
    ventana, panel = perno
    panel.set_valor("largo_completo", completa)
    panel.set_valor("tam_iso_metrica", "M20")
    gestor, asa = panel.manipuladores, _asa(panel)
    desde = asa.puntos(gestor)[0]
    puntos, visibles = gestor.pantalla([desde, desde + asa.direccion * 4])
    assert visibles.all()

    def enviar(tipo, punto, boton, botones):
        p = QPointF(*punto)
        QApplication.sendEvent(ventana.visor, QMouseEvent(tipo, p, ventana.visor.mapToGlobal(p), boton, botones,
                                                        Qt.NoModifier))

    enviar(QEvent.MouseButtonPress, puntos[0], Qt.LeftButton, Qt.LeftButton)
    assert gestor.arrastrando and gestor._arrastre["m"] is asa
    for k in range(1, 7):
        enviar(QEvent.MouseMove, puntos[0] + (puntos[1] - puntos[0]) * k / 6, Qt.NoButton, Qt.LeftButton)
        QTest.qWait(15)
    enviar(QEvent.MouseButtonRelease, puntos[1], Qt.LeftButton, Qt.NoButton)
    assert not gestor.arrastrando
    tamano = panel.valores["tam_iso_metrica"]
    diametro = sc.datos_rosca(sc.designaciones_rosca("iso_metrica", tamano)[0])["diametro"]
    assert tamano == "M28" and diametro > 20
    assert panel.widgets["tam_iso_metrica"].currentData() == tamano
    assert np.linalg.norm(_asa(panel).puntos(gestor)[0] - asa.origen) == pytest.approx(asa.radios[tamano])
    _previa_sana(panel)
    panel.set_valor("modelada", True)
    forma = _previa_sana(panel)
    caja = geo.caja_envolvente(forma)
    assert caja[1][0] - caja[0][0] == pytest.approx(diametro, abs=0.5)


def test_teclear_radio_en_caja_elige_tamano_y_rechaza_errores(perno):
    ventana, panel = perno
    panel.set_valor("tam_iso_metrica", "M20")
    panel.set_valor("des_tipo_rosca", "M20x2.5")
    gestor = panel.manipuladores
    caja = gestor.cajas["tam_iso_metrica"]
    assert caja.text() == "9,895" and caja.isVisible()
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "12")
    QTest.keyClick(caja, Qt.Key_Return)
    assert panel.valores["tam_iso_metrica"] == "M24"
    assert panel.widgets["tam_iso_metrica"].currentData() == "M24"
    assert caja.text() == "11,882"
    _previa_sana(panel)
    assert sc.datos_rosca(panel.ultima_op.p["designacion"])["tamano"] == "M24"

    for texto in ("sin_radio +", "0", "-2", "12 deg"):
        caja.setText(texto)
        assert gestor.aplicar_caja(caja) is False
        assert panel.valores["tam_iso_metrica"] == "M24"
        assert caja.toolTip()
    caja.setText("11,9 mm")
    assert gestor.aplicar_caja(caja) is True
    assert panel.valores["tam_iso_metrica"] == "M24" and caja.text() == "11,882"
    caja.setText("99")
    QTest.keyClick(caja, Qt.Key_Escape)
    assert caja.text() == "11,882"
    ventana.visor.setFocus()
    panel.set_valor("tipo_rosca", "unificada")
    assert "tam_iso_metrica" not in gestor.cajas
    caja = gestor.cajas["tam_unificada"]
    caja.setText("3,2 mm")
    assert gestor.aplicar_caja(caja) is True
    assert panel.valores["tam_unificada"] == "1/4"
    assert caja.text() == "3,11"
    _previa_sana(panel)
