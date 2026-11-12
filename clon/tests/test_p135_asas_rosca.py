"""P-135: Rosca sin «Longitud completa» muestra las flechas de Desfase y Longitud sobre la pared, como Fusion."""
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.ui import manipuladores as mp
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _arrastrar(visor, desde, hasta):
    """Como una persona: apretar, varios movimientos y soltar (eventos al widget, no el cursor real)."""
    def ev(tipo, p, boton, botones):
        p = QPointF(*p)
        QApplication.sendEvent(visor, QMouseEvent(tipo, p, visor.mapToGlobal(p), boton, botones, Qt.NoModifier))
    ev(QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, 6):
        ev(QEvent.MouseMove, [a + (b - a) * k / 5 for a, b in zip(desde, hasta, strict=True)], Qt.NoButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


def test_p135_flechas_de_desfase_y_longitud_sobre_la_pared(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_cylinder", {"radius": 10, "height": 60, "name": "Perno"})["ok"]
    v = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1300, 850)
    v.show()
    try:
        QTest.qWait(300)
        v.acciones["vista_frente"].trigger()
        v.visor.encuadrar()
        QTest.qWait(200)
        forma = next(iter(v.doc.estado_final.cuerpos.values())).forma
        panel = v.ejecutar_comando(CATALOGO["rosca"]())
        QTest.qWait(200)
        cara = next(c for c in refs.subformas(forma, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
        QTest.mouseClick(v.visor, Qt.LeftButton, pos=v.visor.proyectar(np.array(refs.firma_cara(cara)["centro"])).toPoint())
        assert panel.valores["caras"]
        assert panel.manipuladores.manips == []             # con largo completo no hay flechas

        casilla = panel.widgets["largo_completo"]
        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        QTest.qWait(100)
        assert not panel.valores["largo_completo"] and panel.widgets["desfase"].isVisible()
        gestor = panel.manipuladores
        desfase, largo = gestor.manips
        assert isinstance(desfase, mp.FlechaCilindro) and (desfase.clave, largo.clave) == ("desfase", "longitud")

        ojo = np.asarray(v.visor.R[2], float)
        for m in (desfase, largo):
            base = m.puntos(gestor)[0]
            assert abs(np.hypot(base[0], base[1]) - 10) < 1e-6      # sobre la cara de Ø20
            assert base @ ojo > 0                           # sobre la pared que se ve, no adentro ni atrás
        assert abs(largo.puntos(gestor)[0][2] - 10) < 1e-6  # la Longitud nace en el fin del tramo (0 + 10 mm)

        a, b = (v.visor.proyectar(p) for p in desfase.puntos(gestor))
        medio = (a + b) / 2
        mm = v.visor.proyectar(np.array([0, -10.0, 5])) - v.visor.proyectar(np.array([0, -10.0, 0]))
        _arrastrar(v.visor, (medio.x(), medio.y()), (medio.x() + mm.x(), medio.y() + mm.y()))
        QTest.qWait(100)
        nuevo = v.doc.parametros.evaluar(panel.valores["desfase"])
        assert 3 < nuevo < 7, panel.valores["desfase"]
        assert abs(gestor.manips[1].puntos(gestor)[0][2] - (nuevo + 10)) < 1e-6   # la Longitud sigue al Desfase
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
