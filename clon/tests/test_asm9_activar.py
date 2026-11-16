"""ASM-9: Activar componente: lo que se crea entra en el componente activo y la raíz vuelve a ser el predeterminado."""
from omnicad import api
from omnicad.api.sesion import Sesion


def _llamar(s, nombre, args=None):
    r = api.llamar(s, nombre, args or {})
    assert r["ok"], r
    return r


def test_lo_creado_entra_en_el_componente_activo():
    s = Sesion()
    c = _llamar(s, "create_component", {"name": "Tapa"})["result"]["component"]["id"]
    assert _llamar(s, "activate_component", {"component": "Tapa"})["result"]["active_component"] == c
    assert _llamar(s, "get_assembly", {"summary": True})["result"]["active_component"] == c
    nuevo = _llamar(s, "create_component", {"name": "Hijo"})["result"]["component"]
    assert nuevo["parent"] == c
    _llamar(s, "activate_component")
    assert _llamar(s, "get_assembly", {"summary": True})["result"]["active_component"] == ""
    assert _llamar(s, "create_component", {"name": "Raiz"})["result"]["component"]["parent"] in ("", None)


def test_cuerpos_nuevos_van_al_activo_se_guardan_y_el_timeline_se_filtra():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.ui.panel_timeline import PanelTimeline
    app = QApplication.instance() or QApplication([])      # noqa: F841
    s = Sesion()
    _llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})                    # raíz
    c = _llamar(s, "create_component", {"name": "Tapa"})["result"]["component"]["id"]
    _llamar(s, "activate_component", {"component": c})
    caja = _llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "x": 50})["result"]["bodies_created"][0]["id"]
    assert s.doc.estado_final.cuerpos[caja].componente == c
    copia = Documento.desde_dict(s.doc.a_dict())            # lo anotado en el paso sobrevive al guardar y abrir
    assert copia.estado_final.cuerpos[caja].componente == c
    panel = PanelTimeline()
    panel.actualizar(s.doc)
    filas = [panel.lista.item(i).data(0x0100) for i in range(panel.lista.count())]
    assert caja.split(".")[0] in filas and "op1" not in filas       # solo lo del componente activo
    _llamar(s, "activate_component")
    panel.actualizar(s.doc)
    assert "op1" in [panel.lista.item(i).data(0x0100) for i in range(panel.lista.count())]
