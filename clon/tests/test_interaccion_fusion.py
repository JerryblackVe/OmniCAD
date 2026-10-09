"""Manipulación como en Fusion: sectores del menú radial, medidas de lo elegido, avisos flotantes y planos
ocultos. Lo que necesita la ventana real con OpenGL se prueba en `OmniCAD.py --prueba-humo`."""
import os

import pytest

from omnicad.nucleo import geometria as g


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("dx, dy, esperado", [
    (0, -50, 0), (40, -40, 1), (60, 0, 2), (40, 40, 3), (0, 50, 4), (-40, 40, 5), (-60, 0, 6), (-40, -40, 7),
    (10, -60, 0), (-10, -60, 0),
])
def test_sector_del_menu_radial_en_sentido_horario_desde_arriba(dx, dy, esperado):
    from omnicad.ui.menu_radial import sector
    assert sector(dx, dy) == esperado


def test_menu_radial_elige_por_sector_y_abre_el_segundo_nivel(app_qt):
    from PySide6.QtCore import QPointF

    from omnicad.ui.menu_radial import ItemRadial, MenuRadial
    llamados = []
    sub = [ItemRadial(f"B{i}", lambda i=i: llamados.append(f"B{i}")) for i in range(8)]
    items = [ItemRadial("Repetir", None, activo=False), None, ItemRadial("Rehacer", lambda: llamados.append("R")), None,
             ItemRadial("Boceto", None, sub=sub), None, ItemRadial("Deshacer", lambda: llamados.append("D")), None]
    m = MenuRadial(items, [("Ajustar", lambda: llamados.append("A"), "F6"), None, ("Dibujo", None)])
    c = m.centro
    assert m._sector_en(c + QPointF(120, 0)) == 2               # derecha: Rehacer
    assert m._sector_en(c + QPointF(40, -40)) is None           # NE vacío: no se resalta nada
    assert m._sector_en(c + QPointF(3, 3)) is None              # el centro cierra, no elige
    m.ejecutado = None
    m.niveles.append(m._ocho(sub))                              # segundo nivel (Boceto ▸)
    assert [i.texto for i in m.items][:2] == ["B0", "B1"]
    assert m.lista is not None and m.lista.height() > 40         # la lista de contexto va debajo


def test_aviso_flotante_cuenta_los_seguidos(app_qt):
    from PySide6.QtWidgets import QWidget

    from omnicad.ui.avisos import AvisoFlotante
    padre = QWidget()
    padre.resize(800, 600)
    padre.show()
    aviso = AvisoFlotante(padre)
    aviso.mostrar("Las restricciones o las cotas se han eliminado durante la operación.")
    assert aviso.isVisible() and aviso.titulo.text() == "1 advertencia(s)"
    aviso.mostrar("Otra cosa")
    assert aviso.titulo.text() == "2 advertencia(s)"
    aviso.mostrar("Falló el paso", "error")
    assert aviso.titulo.text() == "1 error(es)"
    padre.close()


def test_medidas_de_lo_elegido_como_fusion():
    from omnicad.ui.medidas import texto_medidas
    caja = g.caja(10, 20, 30)
    cara = max(g.caras(caja), key=g.area)
    from omnicad.nucleo import referencias as refs
    aristas = refs.subformas(caja, "arista")
    assert texto_medidas([]) == ""
    assert texto_medidas([{"tipo": "cara", "ref": {}, "forma": cara}]) == "1 Cara | Área: 600.000 mm^2"
    larga = max(aristas, key=g.longitud)
    assert texto_medidas([{"tipo": "arista", "ref": {}, "forma": larga}]) == "1 Arista | Longitud: 30.000 mm"
    dos = texto_medidas([{"tipo": "cuerpo", "ref": {}, "forma": caja}] * 2)
    assert dos == "2 Cuerpos | Volumen: 12000.000 mm^3"
    assert texto_medidas([{"tipo": "cara", "ref": {}}, {"tipo": "arista", "ref": {}}]) == "2 objetos"


def test_banda_de_seleccion_con_los_colores_de_fusion(app_qt):
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QWidget

    from omnicad.ui.visor3d import BandaSeleccion
    padre = QWidget()
    padre.resize(200, 200)
    banda = BandaSeleccion(padre)
    banda.setGeometry(10, 10, 60, 40)
    colores = []
    for cruce in (False, True):
        banda.cruce = cruce
        img = banda.grab().toImage().convertToFormat(QImage.Format_ARGB32)
        c = img.pixelColor(30, 20)
        colores.append((c.red(), c.green(), c.blue()))
    naranja, amarillo = colores
    assert naranja[0] > naranja[1] > naranja[2]                 # de izquierda a derecha: naranja
    assert amarillo[0] > amarillo[2] and amarillo[1] > amarillo[2] and abs(amarillo[0] - amarillo[1]) < 30


def test_comentarios_se_guardan_con_el_proyecto():
    from omnicad.timeline.documento import Documento
    doc = Documento()
    doc.agregar_comentario("Revisar el espesor de la pared")
    doc.agregar_comentario("Otra nota")
    doc.borrar_comentario(1)
    copia = Documento.desde_dict(doc.a_dict())
    assert [c["texto"] for c in copia.comentarios] == ["Revisar el espesor de la pared"]
    assert copia.comentarios[0]["fecha"]


def test_panel_comentarios_lista_y_agrega(app_qt):
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comentarios import PanelComentarios
    doc = Documento()
    panel = PanelComentarios()
    panel.set_documento(doc)
    assert panel.titulo.text() == "COMENTARIOS" and panel.lista.isHidden()
    panel.agregar("Primera nota")
    panel.actualizar()
    assert panel.lista.count() == 1 and panel.titulo.text() == "COMENTARIOS (1)" and not panel.lista.isHidden()


def test_extruir_cortar_muestra_en_rojo_lo_que_quita(app_qt):
    from omnicad.restricciones import Boceto
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.manipuladores import ROJO_PREVIA
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    b = Boceto()
    b.agregar_rectangulo((5, 5), (15, 15))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    perfil = doc.estado_final.bocetos["op2"].perfiles[0]
    hit = hit_desde_ref({"tipo": "perfil", "boceto": "op2", **OpExtrusion.referencia_perfil(perfil)}, doc.estado_final)
    cmd, ctx = Extruir(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(perfiles=[hit], distancia="5 mm", operacion="cortar")
    prims = cmd.previa_vista(ctx, v, cmd.construir(v, ctx))
    assert prims and prims[0][2] == ROJO_PREVIA and len(prims[0][1]) > 0
    v["operacion"] = "nuevo"
    assert cmd.previa_vista(ctx, v, cmd.construir(v, ctx)) is None
    assert len(doc.operaciones) == 2 and len(doc.estado_final.cuerpos) == 1     # la vista previa no toca el diseño
