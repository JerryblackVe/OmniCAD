# -*- coding: utf-8 -*-
"""P-194 / P-195: con el panel de un comando abierto la paleta se compacta y al cerrarlo vuelve; dentro del boceto
los Comentarios arrancan plegados y se pueden volver a abrir."""
from PySide6.QtWidgets import QApplication, QFrame

from omnicad.ui import superposiciones as sup
from omnicad.ui import visor3d as vis
from omnicad.ui.comentarios import PanelComentarios


class _Paleta(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.plegada = False

    def plegar_por_ventana(self, plegar):
        cambio = self.plegada != plegar
        self.plegada = plegar
        return cambio


def test_paleta_se_compacta_con_el_panel_de_comando():
    app = QApplication.instance() or QApplication([])
    area = sup.AreaVisor(vis.Visor3D())
    area.resize(900, 600)
    area.show()
    area.paleta = paleta = _Paleta(area)
    panel = QFrame(area)
    area.agregar_lateral(panel)
    area.de_comando.append(panel)
    panel.show()
    app.processEvents()
    assert paleta.plegada
    panel.hide()
    app.processEvents()
    assert not paleta.plegada
    area.close()


def test_comentarios_plegados_y_reabribles():
    QApplication.instance() or QApplication([])
    p = PanelComentarios()
    p.show()
    p.lista.show()                                    # abiertos, como cuando hay comentarios
    assert p.plegar_por_ventana(True) and p.lista.isHidden()
    assert not p.plegar_por_ventana(True)            # ya plegado: no cambia nada
    assert p.plegar_por_ventana(False) and not p.lista.isHidden()
    p.close()


def test_otro_boceto_no_arrastra_los_paneles_del_anterior():
    QApplication.instance() or QApplication([])
    area = sup.AreaVisor(vis.Visor3D())
    area.de_comando.append(QFrame(area))
    area._paleta_plegada = True
    area.set_capa_boceto(None, None)
    assert area.de_comando == [] and not area._paleta_plegada
    area.close()
