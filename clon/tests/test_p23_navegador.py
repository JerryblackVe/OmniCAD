"""P23: efectos de la selección y de los menús del navegador."""
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.navegador import ROL_CLAVE


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("p23") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.fixture
def v(ventana):
    doc = Documento()
    for i in range(3):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), f"Pieza {i + 1}", forma="caja", x=i * 40,
                               ancho=20, largo=20, alto=20))
    ventana.set_documento(doc)
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()


def elegidos(v):
    return {it.data(0, ROL_CLAVE) for it in v.navegador.arbol.selectedItems()}


def test_clic_en_cuerpo_revela_y_selecciona_en_navegador(v, monkeypatch):
    cid = next(iter(v.doc.estado_final.cuerpos))
    it = v.navegador.item(cid)
    it.parent().setExpanded(False)
    v.navegador.filtro.setText("no coincide")
    hit = v._hits_cuerpos([cid])[0]
    monkeypatch.setattr(v.visor, "elegir_entidad", lambda *_: hit)
    QTest.mouseClick(v.visor, Qt.LeftButton, pos=QPoint(600, 300))
    assert elegidos(v) == {cid}
    assert it.parent().isExpanded() and not it.parent().isHidden()
    assert v.navegador.filtro.text() == ""
    assert v.seleccion[0]["ref"]["cuerpo"] == cid


def test_api_selecciona_en_vivo_y_rechaza_cuerpo_inexistente_sin_cambiar(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    cid = next(iter(v.doc.estado_final.cuerpos))
    r = puente.ejecutar("select_bodies", {"bodies": [cid]})
    assert r["ok"] and r["result"]["selected_bodies"] == [cid]
    assert elegidos(v) == {cid}
    assert not puente.ejecutar("select_bodies", {"bodies": ["inexistente"]})["ok"]
    assert elegidos(v) == {cid}
    assert puente.ejecutar("select_bodies", {"bodies": []})["ok"]
    assert not elegidos(v)
    assert api.llamar(api.Sesion(), "select_bodies", {"bodies": []})["error_kind"] == "APP_NOT_RUNNING"


def clicar_fila(v, cid, modificadores=Qt.NoModifier):
    arbol = v.navegador.arbol
    it = v.navegador.item(cid)
    arbol.scrollToItem(it)
    rect = arbol.visualItemRect(it)
    QTest.mouseClick(arbol.viewport(), Qt.LeftButton, modificadores, rect.center())


@pytest.mark.parametrize("modificadores", [Qt.ControlModifier, Qt.ShiftModifier])
def test_tres_cuerpos_desde_navegador_con_ctrl_o_mayus(v, modificadores):
    ids = list(v.doc.estado_final.cuerpos)
    clicar_fila(v, ids[0])
    if modificadores == Qt.ControlModifier:
        clicar_fila(v, ids[1], modificadores)
    clicar_fila(v, ids[2], modificadores)
    assert elegidos(v) == set(ids)
    assert {h["ref"]["cuerpo"] for h in v.seleccion} == set(ids)
    assert len(v.visor._capas["preseleccion"]) == sum(len(h["dibujo"]) for h in v.seleccion)
    v._actualizar()
    assert elegidos(v) == set(ids)  # refrescar el árbol no pierde ni realimenta la selección


def test_ctrl_clic_vista_refleja_tres_cuerpos_y_quita_uno(v, monkeypatch):
    ids = list(v.doc.estado_final.cuerpos)
    for i, cid in enumerate(ids):
        hit = v._hits_cuerpos([cid])[0]
        monkeypatch.setattr(v.visor, "elegir_entidad", lambda *_, h=hit: h)
        QTest.mouseClick(v.visor, Qt.LeftButton, Qt.ControlModifier if i else Qt.NoModifier,
                         QPoint(600, 300))
    assert elegidos(v) == set(ids)
    assert len(v.seleccion) == 3
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.ControlModifier, QPoint(600, 300))
    assert elegidos(v) == set(ids[:2])
    assert len(v.seleccion) == 2


def menu_de(v, clave):
    return v.navegador.menu_elemento(v.navegador.item(clave))


def accion(menu, texto):
    return next(a for a in menu.actions() if a.text().split("\t")[0] == texto)


def test_menu_nuevo_grupo_desplazar_y_deshacer(v, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    ids = list(v.doc.estado_final.cuerpos)
    v.seleccionar_cuerpos(ids[:2])
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("Grupo de piezas", True))
    accion(menu_de(v, ids[0]), "Nuevo grupo").trigger()
    assert v.navegador.item(ids[0]).parent().text(0) == "Grupo de piezas"
    gid = v.navegador.item(ids[0]).parent().data(0, ROL_CLAVE)
    v.seleccionar_cuerpos(ids[2:])
    mover = accion(menu_de(v, ids[2]), "Desplazar al grupo").menu()
    accion(mover, "Grupo de piezas").trigger()
    assert v.navegador.item(ids[2]).parent().data(0, ROL_CLAVE) == gid
    v.doc.deshacer()
    assert v.navegador.item(ids[2]).parent().data(0, ROL_CLAVE) == "__cuerpos__"


def test_conjunto_guarda_y_reselecciona_tres_cuerpos(v, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    ids = list(v.doc.estado_final.cuerpos)
    v.seleccionar_cuerpos(ids)
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("Mis piezas", True))
    accion(menu_de(v, ids[0]), "Crear conjunto de selección").trigger()
    s = api.Sesion(v.doc)
    conjuntos = api.llamar(s, "get_browser_state", {})["result"]["selection_sets"]
    assert conjuntos[0]["items"] == ids
    v._seleccionar([])
    v.navegador._clic(v.navegador.item(conjuntos[0]["id"]), 0)
    assert elegidos(v) == set(ids)


def test_propiedades_mide_los_cuerpos_del_grupo(v):
    ids = list(v.doc.estado_final.cuerpos)
    r = api.llamar(api.Sesion(v.doc), "manage_browser", {"action": "create_group", "name": "G", "items": ids})
    accion(menu_de(v, r["result"]["id"]), "Propiedades").trigger()
    assert "24000" in v._texto_estado or "24000" in v._info_sel or "24000" in v.timeline.estado.text()


@pytest.mark.parametrize("texto", ["Copiar", "Cortar"])
def test_portapapeles_no_implementado_queda_gris_con_razon(v, texto):
    a = accion(menu_de(v, next(iter(v.doc.estado_final.cuerpos))), texto)
    assert not a.isEnabled() and "portapapeles" in a.toolTip()


def test_suprimir_cuerpo_y_grupo_conserva_contenido(v):
    ids = list(v.doc.estado_final.cuerpos)
    s = api.Sesion(v.doc)
    r = api.llamar(s, "manage_browser", {"action": "create_group", "name": "G", "items": ids})
    accion(menu_de(v, r["result"]["id"]), "Suprimir").trigger()
    assert len(v.doc.estado_final.cuerpos) == 3
    assert not api.llamar(s, "get_browser_state", {})["result"]["groups"]
    accion(menu_de(v, ids[0]), "Suprimir").trigger()
    assert ids[0] not in v.doc.estado_final.cuerpos
    v.doc.deshacer()
    assert ids[0] in v.doc.estado_final.cuerpos


def test_cambiar_nombre_cuerpo_en_linea_y_grupo(v, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    cid = next(iter(v.doc.estado_final.cuerpos))
    accion(menu_de(v, cid), "Cambiar nombre").trigger()
    v.navegador.item(cid).setText(0, "Pieza renombrada")
    assert v.doc.estado_final.cuerpos[cid].nombre == "Pieza renombrada"
    r = api.llamar(api.Sesion(v.doc), "manage_browser", {"action": "create_group", "name": "G"})
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("Nuevo nombre", True))
    accion(menu_de(v, r["result"]["id"]), "Cambiar nombre").trigger()
    assert v.navegador.item(r["result"]["id"]).text(0) == "Nuevo nombre"


@pytest.mark.parametrize("propiedades", [{}, {"organizacion": {}}])
def test_ojo_y_mostrar_todo_tienen_efecto_en_vista(v, propiedades):
    v.doc.propiedades["__navegador__"] = dict(propiedades)
    ids = list(v.doc.estado_final.cuerpos)
    accion(menu_de(v, ids[0]), "Mostrar/ocultar").trigger()
    assert ids[0] in v.ocultos
    assert v.doc.propiedad("__navegador__", "ocultos") == [ids[0]]
    assert ids[0] not in {m["id"] for m in v.visor._mallas}
    accion(menu_de(v, ids[1]), "Mostrar todo").trigger()
    assert not v.ocultos
    assert v.doc.propiedades.get("__navegador__") == (propiedades or None)
    assert {m["id"] for m in v.visor._mallas} == set(ids)


def test_cuerpo_oculto_persiste_al_guardar_y_reabrir(v, tmp_path):
    from omnicad.io_archivos import proyecto
    cid = next(iter(v.doc.estado_final.cuerpos))
    deshacer = list(v.doc._deshacer)
    v._ojo(cid)
    assert v.doc._deshacer == deshacer
    ruta = proyecto.guardar(v.doc, tmp_path / "ocultos.omnicad")
    v.set_documento(Documento())
    assert not v.ocultos
    v.set_documento(proyecto.abrir(ruta))
    assert v.ocultos == {cid}
    assert cid not in {m["id"] for m in v.visor._mallas}
    assert {m["id"] for m in v.visor._mallas} == set(v.doc.estado_final.cuerpos) - {cid}


@pytest.mark.parametrize("ocultos", [None, "op1.c1", {}, 42, ["op1.c1", 1], [[]]])
def test_ocultos_invalidos_se_ignoran_al_abrir(v, ocultos):
    v.doc.propiedades["__navegador__"] = {"ocultos": ocultos}
    v.set_documento(v.doc)
    assert not v.ocultos
    assert "__navegador__" not in v.doc.propiedades
    assert {m["id"] for m in v.visor._mallas} == set(v.doc.estado_final.cuerpos)


def test_grupos_persisten_y_entrada_invalida_no_modifica(v, tmp_path):
    from omnicad.io_archivos import proyecto
    ids = list(v.doc.estado_final.cuerpos)
    s = api.Sesion(v.doc)
    assert api.llamar(s, "manage_browser", {"action": "create_group", "name": "G", "items": ids})["ok"]
    antes = v.doc.a_dict()
    assert not api.llamar(s, "manage_browser", {"action": "move", "group": "nada", "items": ids})["ok"]
    assert v.doc.a_dict() == antes
    ruta = proyecto.guardar(v.doc, tmp_path / "grupos.omnicad")
    assert api.llamar(api.Sesion(proyecto.abrir(ruta)), "get_browser_state", {}) == api.llamar(s, "get_browser_state", {})


def test_api_visibilidad_y_atajo_v_comparten_efecto(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ids = list(v.doc.estado_final.cuerpos)
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("set_browser_visibility", {"items": ids, "visible": False})["ok"]
    assert v.ocultos.issuperset(ids)
    v.seleccionar_cuerpos(ids)
    v.acciones["alternar_visibilidad"].trigger()
    assert not v.ocultos.intersection(ids)
