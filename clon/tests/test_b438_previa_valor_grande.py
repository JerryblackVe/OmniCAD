"""B-438: tras una previa rápida de «15 mm», teclear «1e3 mm» no se calcula en la ventana (el costo crece con el valor)."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_un_valor_mucho_mayor_que_el_de_la_previa_rapida_va_aparte(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"entities": [{"type": "rectangle", "corner1": [0, 0], "corner2": [20, 10]}]})["ok"]
    boceto = s.doc.operaciones[-1].id
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        perfil = s.doc.estado_final.bocetos[boceto].perfiles[0]
        p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, p.ctx.estado))
        p.set_valor("distancia", "15 mm")
        p._t_previa.stop()
        chico = p.comando.construir(p.valores, p.ctx)
        p._ms_previa = comando._firma_previa(chico), 1.0, comando._magnitud_previa(p.ctx, chico)
        assert not p._previa_pesada(chico)
        p.set_valor("distancia", "70 mm")                      # hasta 5 veces: sigue en la ventana
        p._t_previa.stop()
        assert not p._previa_pesada(p.comando.construir(p.valores, p.ctx))
        p.set_valor("distancia", "1e3 mm")
        p._t_previa.stop()
        grande = p.comando.construir(p.valores, p.ctx)
        assert comando._firma_previa(grande) == comando._firma_previa(chico)
        assert p._previa_pesada(grande)                         # 1000 mm tras 15 mm: al proceso aparte
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
