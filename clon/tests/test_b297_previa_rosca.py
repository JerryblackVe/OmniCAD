"""B-297: la selección deja ver el material de la previa de Rosca modelada; P-145: las crestas siguen en azul.
P-78: esa previa va al proceso aparte."""
import time

import numpy as np
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _esperar_previa(panel):
    limite = time.monotonic() + 30
    while (panel._t_previa.isActive() or panel._hijo_previa is not None) and time.monotonic() < limite:
        QTest.qWait(50)
    assert panel._previa_ok, panel.mensaje.text()
    assert panel._hijo_previa is None
    QTest.qWait(200)


def test_b297_previa_modelada_muestra_material_y_restaura_seleccion(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_cylinder", {"radius": 5, "height": 20, "name": "Perno"})["ok"]
    preferencias = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(sesion.doc, prefs=preferencias)
    v.resize(1500, 900)
    v.show()
    try:
        QTest.qWait(500)
        v.visor.encuadrar()
        QTest.qWait(200)
        cid = next(iter(v.doc.estado_final.cuerpos))
        original = v.doc.estado_final.cuerpos[cid].forma
        panel = v.ejecutar_comando(CATALOGO["rosca"]())
        QTest.qWait(200)
        cara = next(c for c in refs.subformas(original, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
        firma = refs.firma_cara(cara)
        punto = v.visor.proyectar(np.array(firma.get("centro", firma.get("medio"))))
        hit = v.visor.elegir_entidad(punto, {"cara"})
        assert hit is not None and refs.firma_cara(hit["forma"])["geom"] == "cilindro"
        QTest.mouseClick(v.visor, Qt.LeftButton, pos=punto.toPoint())
        assert panel.valores["caras"]
        _esperar_previa(panel)
        assert not panel._previa_pesada(panel.ultima_op)     # la cosmética no corta nada: sigue en la ventana

        casilla = panel.widgets["modelada"]
        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        assert panel.valores["modelada"]
        # P-78: cortar la hélice congelaba la ventana (M20×100: 25 s); su previa sale del proceso aparte
        assert panel._previa_pesada(panel.comando.construir(panel.valores, panel.ctx))
        _esperar_previa(panel)
        assert cid in v.visor._estado._mallas_previa           # la malla que dibuja el visor vino del proceso aparte
        assert v.visor._estado.cuerpos[cid].forma is not original
        assert len(refs.subformas(v.visor._estado.cuerpos[cid].forma, "cara")) > 3
        # P-145, como Fusion: sigue en azul solo lo que quedó de la cara (tramos de afuera y crestas), no los flancos
        tris = np.concatenate([p[1] for p in v.visor._capas["seleccion"]])
        assert len(tris) and np.hypot(tris[:, 0], tris[:, 1]).min() > 4.8, "la cara elegida tiñe los flancos de la rosca"

        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        _esperar_previa(panel)
        assert "seleccion" in v.visor._capas      # sin Modelado, la cara elegida vuelve a resaltarse
        QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
        _esperar_previa(panel)
        panel.cancelar()
        assert "seleccion" not in v.visor._capas
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
