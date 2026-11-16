"""B-573: al activar «Boceto 3D», el panel de la paleta entra en su ancho: la ayuda no se corta a la derecha y las
casillas ✔ de las opciones siguen a la vista."""
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from test_p23_navegador import v as v, ventana as ventana  # noqa: F401  (fixtures de la ventana en vivo)

from omnicad.restricciones import Boceto
from omnicad.timeline.operaciones import OpBoceto


def test_b573_el_panel_3d_entra_en_el_ancho_de_la_paleta(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Ruta 3D", plano="XY", boceto=Boceto()))
    assert PuenteAgentes(v, archivo=tmp_path / "puente.json").ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    paleta = v.modo_boceto.paleta
    paleta.checks["boceto3d"].setChecked(True)
    QApplication.processEvents()
    vista = paleta.opciones.viewport()
    for w in [*paleta.checks.values(), *paleta.panel3d.findChildren(object)]:
        if not hasattr(w, "isVisibleTo") or not w.isVisibleTo(paleta):
            continue
        derecha = w.mapTo(vista, QPoint(w.width(), 0)).x()
        assert derecha <= vista.width(), f"{type(w).__name__} {getattr(w, 'text', lambda: '')()!r}: {derecha} > {vista.width()}"
    ayuda = paleta.ayuda3d                                    # la ayuda visible es de 1 renglón (regla 14)
    assert ayuda.fontMetrics().horizontalAdvance(ayuda.text()) <= ayuda.width() and "Esc" in ayuda.toolTip()
    assert ayuda.height() < 2 * ayuda.fontMetrics().lineSpacing()
