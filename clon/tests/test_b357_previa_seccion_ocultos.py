# -*- coding: utf-8 -*-
"""B-357: con la carpeta Cuerpos oculta, la PREVIA del comando Análisis de sección seguía cortando y rayando los cuerpos
(B-311 había arreglado solo el dibujo de los análisis guardados)."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.comando import hits
from omnicad.ui.comandos.inspeccionar import Seccion
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_la_previa_de_la_seccion_no_corta_la_carpeta_cuerpos_oculta(tmp_path):
    s = api.Sesion()
    for x in (0, 30):
        assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": x})["ok"]
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        tapas = lambda: [t for t in v.visor._capas.get("analisis", []) if t[0] == "tris"]       # noqa: E731
        p = v.ejecutar_comando(Seccion(), valores={"plano": hits([{"tipo": "plano", "id": "XY"}], s.doc.estado_final),
                                                    "desfase": "5 mm"})
        p._t_previa.stop()
        p._calcular_previa()
        assert len(tapas()) == 2
        v._ojo("__cuerpos__")                         # clic en el ojo de la carpeta Cuerpos con el panel abierto
        p._t_previa.stop()
        p._calcular_previa()
        assert tapas() == []
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
