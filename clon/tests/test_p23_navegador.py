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


def test_menu_del_cuerpo_trae_opacidad_aislar_y_aspecto(v):
    """El menú del cuerpo reusaba el del grupo y la opacidad quedó sin ningún camino en la interfaz."""
    cid = next(iter(v.doc.estado_final.cuerpos))
    menu = menu_de(v, cid)
    textos = {a.text().split("\t")[0] for a in menu.actions()}
    assert {"Mover/copiar", "Material físico…", "Aspecto…", "Quitar", "Control de opacidad", "Aislar",
            "Desaislar", "Buscar en la secuencia temporal"} <= textos
    accion(accion(menu, "Control de opacidad").menu(), "50 %").trigger()
    assert v.doc.propiedades[cid]["opacidad"] == 0.5
    accion(menu_de(v, cid), "Aislar").trigger()
    assert v.ocultos == set(v.doc.estado_final.cuerpos) - {cid}


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


def test_menu_raiz_en_orden_con_separadores_y_no_disponibles(v):
    m = menu_de(v, "__raiz__")
    assert [a.text() if not a.isSeparator() else "---" for a in m.actions()] == [
        "Añadir a ensamblaje", "Crear dibujo", "Configurar", "Grupo rígido", "Activar conjuntos de contactos",
        "---", "Material físico", "Aspecto", "Controles de mapa de textura", "Propiedades", "---",
        "Solo lectura para mí", "Exportar…", "Guardar copia como", "Guardar como malla", "Mostrar en ubicación",
        "Historial", "---", "Control de detalles de visualización", "Mostrar todos los componentes",
        "Mostrar todos los cuerpos", "Control de opacidad", "---", "Buscar en la ventana", "---",
        "Cambiar al modelado directo"]
    for texto in ("Añadir a ensamblaje", "Activar conjuntos de contactos", "Controles de mapa de textura",
                  "Solo lectura para mí", "Guardar copia como", "Mostrar en ubicación", "Historial",
                  "Control de detalles de visualización", "Cambiar al modelado directo"):
        a = accion(m, texto)
        assert not a.isEnabled() and a.toolTip() == "Todavía no disponible"


def test_menu_cuerpo_en_orden_con_separadores_y_no_disponibles(v):
    m = menu_de(v, next(iter(v.doc.estado_final.cuerpos)))
    assert [a.text().split("\t")[0] if not a.isSeparator() else "---" for a in m.actions()] == [
        "Desplazar al grupo", "---", "Nuevo grupo", "Crear conjunto de selección", "---", "Mover/copiar",
        "Crear componentes a partir de cuerpos", "Configurar", "Activar conjuntos de contactos", "Material físico…",
        "Aspecto…", "Controles de mapa de textura", "Eliminar anulación de aspecto", "Propiedades", "---",
        "Guardar como malla", "---", "Copiar", "Cortar", "Suprimir", "Quitar", "Cambiar nombre", "---",
        "Control de detalles de visualización", "Mostrar/ocultar", "Mostrar todo", "Control de opacidad",
        "Seleccionable/no seleccionable", "Aislar", "Desaislar", "---", "Buscar en la ventana",
        "Buscar en la secuencia temporal"]
    for texto in ("Activar conjuntos de contactos", "Controles de mapa de textura", "Copiar", "Cortar",
                  "Control de detalles de visualización", "Seleccionable/no seleccionable"):
        a = accion(m, texto)
        assert not a.isEnabled() and a.toolTip().startswith("Todavía no disponible")


def test_raiz_vacia_deshabilita_acciones_que_necesitan_cuerpos(v):
    v.set_documento(Documento())
    m = menu_de(v, "__raiz__")
    for texto in ("Material físico", "Aspecto", "Propiedades", "Mostrar todos los componentes",
                  "Mostrar todos los cuerpos", "Control de opacidad", "Buscar en la ventana"):
        assert not accion(m, texto).isEnabled()


def test_clic_derecho_raiz_llega_al_menu_propio(v, monkeypatch):
    menus = []
    raiz = v.navegador.item("__raiz__")
    m = menu_de(v, "__raiz__")
    monkeypatch.setattr(m, "exec", lambda *_: menus.append(m))
    def crear_menu(item):
        assert item is raiz
        return m
    monkeypatch.setattr(v.navegador, "menu_elemento", crear_menu)
    arbol = v.navegador.arbol
    v.navegador._menu(arbol.visualItemRect(raiz).center())
    assert len(menus) == 1 and menus[0].actions()[0].text() == "Añadir a ensamblaje"


@pytest.mark.parametrize("raiz,texto,clave", [(False, "Mover/copiar", "mover_copiar"),
                                           (False, "Material físico", "material_fisico"),
                                           (True, "Material físico", "material_fisico"),
                                           (False, "Aspecto", "aspecto"), (True, "Aspecto", "aspecto"),
                                           (False, "Quitar", "quitar")])
def test_menu_abre_comando_con_cuerpos_correctos(v, raiz, texto, clave):
    ids = list(v.doc.estado_final.cuerpos)
    objetivo = "__raiz__" if raiz else ids[1]
    etiqueta = texto + ("…" if not raiz and texto in ("Material físico", "Aspecto") else "")
    accion(menu_de(v, objetivo), etiqueta).trigger()
    assert v.panel.comando.CLAVE == clave
    assert [h["ref"]["cuerpo"] for h in v.panel.valores["cuerpos"]] == (ids if raiz else [ids[1]])


def test_crear_componente_desde_cuerpo_usa_seleccion_y_crea_operacion(v):
    ids = list(v.doc.estado_final.cuerpos)
    v.seleccionar_cuerpos([ids[0]])
    accion(menu_de(v, ids[1]), "Crear componentes a partir de cuerpos").trigger()
    assert v.panel.comando.CLAVE == "nuevo_componente"
    assert [h["ref"]["cuerpo"] for h in v.panel.valores["cuerpos"]] == [ids[1]]
    op = v.panel.comando.construir(v.panel.valores, v.panel.ctx)
    v.panel.cancelar()
    v.doc.agregar(op)
    assert v.doc.estado_final.cuerpos[ids[1]].componente == op.id
    assert v.doc.estado_final.cuerpos[ids[0]].componente == ""


@pytest.mark.parametrize("raiz", [False, True])
def test_configurar_abre_tabla_existente(v, monkeypatch, raiz):
    from omnicad.ui.administrar import DialogoConfiguraciones
    abiertos = []
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda dlg: abiertos.append(dlg) or 0)
    accion(menu_de(v, "__raiz__" if raiz else next(iter(v.doc.estado_final.cuerpos))), "Configurar").trigger()
    assert len(abiertos) == 1 and abiertos[0].parent() is v


def test_raiz_crear_dibujo_y_grupo_rigido_reusan_acciones(v, monkeypatch):
    abiertos = []
    monkeypatch.setattr(v, "abrir_espacio", lambda clave: abiertos.append(clave))
    accion(menu_de(v, "__raiz__"), "Crear dibujo").trigger()
    assert abiertos == ["dibujo"]
    accion(menu_de(v, "__raiz__"), "Grupo rígido").trigger()
    assert v.panel.comando.CLAVE == "grupo_rigido"


@pytest.mark.parametrize("raiz,texto", [(True, "Exportar…"), (True, "Guardar como malla"),
                                      (False, "Guardar como malla")])
def test_exportar_reutiliza_accion_y_preselecciona_contexto(v, monkeypatch, raiz, texto):
    ids = list(v.doc.estado_final.cuerpos)
    v.seleccionar_cuerpos([ids[0]])
    llamados = []
    monkeypatch.setattr(v, "exportar", lambda formato: llamados.append((formato, list(v.seleccion))))
    accion(menu_de(v, "__raiz__" if raiz else ids[1]), texto).trigger()
    assert len(llamados) == 1
    formato, seleccion = llamados[0]
    assert formato == (None if texto == "Exportar…" else ("3mf", "stl", "obj", "ply", "glb", "gltf"))
    assert [h["ref"]["cuerpo"] for h in seleccion] == ([] if raiz else [ids[1]])


def test_quitar_anulacion_de_aspecto_reusa_api_y_admite_deshacer(v):
    ids = list(v.doc.estado_final.cuerpos)
    s = api.Sesion(v.doc)
    assert api.llamar(s, "set_material", {"bodies": ids, "material": "Acero"})["ok"]
    assert api.llamar(s, "set_appearance", {"bodies": ids, "color": "#ff0000"})["ok"]
    accion(menu_de(v, ids[0]), "Eliminar anulación de aspecto").trigger()
    assert v.doc.propiedad(ids[0], "apariencia") is None
    assert v.doc.propiedad(ids[0], "material") == "Acero"
    assert v.doc.propiedad(ids[1], "apariencia") == [1, 0, 0]
    v.doc.deshacer()
    assert v.doc.propiedad(ids[0], "apariencia") == [1, 0, 0]


def test_raiz_propiedades_opacidad_y_mostrar_cuerpos(v):
    ids = list(v.doc.estado_final.cuerpos)
    accion(menu_de(v, "__raiz__"), "Propiedades").trigger()
    assert "24000" in v._info_sel
    accion(accion(menu_de(v, "__raiz__"), "Control de opacidad").menu(), "30 %").trigger()
    assert all(v.doc.propiedad(cid, "opacidad") == 0.3 for cid in ids)
    v.doc.deshacer()
    assert all(v.doc.propiedad(cid, "opacidad") is None for cid in ids)
    v.mostrar_elementos(ids, False)
    v.ocultos.add("__xy__")
    accion(menu_de(v, "__raiz__"), "Mostrar todos los cuerpos").trigger()
    assert v.ocultos == {"__xy__"}
    assert {m["id"] for m in v.visor._mallas} == set(ids)


def test_raiz_mostrar_componentes_y_api_conservan_cuerpos_ocultos(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ids = list(v.doc.estado_final.cuerpos)
    r = api.llamar(api.Sesion(v.doc), "create_component", {"bodies": [ids[0]]})
    assert r["ok"], r
    comp = v.doc.estado_final.cuerpos[ids[0]].componente
    v.mostrar_elementos([comp, ids[1]], False)
    accion(menu_de(v, "__raiz__"), "Mostrar todos los componentes").trigger()
    assert v.ocultos == {ids[1]}
    assert {m["id"] for m in v.visor._mallas} == {ids[0], ids[2]}
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("set_browser_visibility", {"items": [comp], "visible": False})["ok"]
    assert comp in v.ocultos and ids[0] not in {m["id"] for m in v.visor._mallas}


@pytest.mark.parametrize("raiz", [False, True])
def test_buscar_en_ventana_selecciona_encuadra_y_resalta_timeline(v, tmp_path, raiz):
    from omnicad.ui.puente import PuenteAgentes
    ids = list(v.doc.estado_final.cuerpos)
    accion(menu_de(v, "__raiz__" if raiz else ids[0]), "Buscar en la ventana").trigger()
    assert elegidos(v) == (set(ids) if raiz else {ids[0]})
    assert v.visor.objetivo == pytest.approx([50 if raiz else 10, 10, 10])
    assert v.timeline.lista.currentItem().data(Qt.UserRole) == v.doc.estado_final.cuerpos[ids[-1] if raiz else ids[0]].op_id
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    r = puente.ejecutar("find_in_window", {"bodies": [ids[1]]})
    assert r["ok"] and r["result"]["bodies"] == [ids[1]]
    assert elegidos(v) == {ids[1]} and v.visor.objetivo == pytest.approx([50, 10, 10])
    antes = list(v.seleccion)
    assert not puente.ejecutar("find_in_window", {"bodies": [ids[0], "inexistente"]})["ok"]
    assert v.seleccion == antes


def test_desaislar_y_buscar_en_timeline_tienen_efecto(v):
    ids = list(v.doc.estado_final.cuerpos)
    v.mostrar_elementos(ids, False)
    accion(menu_de(v, ids[0]), "Desaislar").trigger()
    assert not v.ocultos
    accion(menu_de(v, ids[1]), "Buscar en la secuencia temporal").trigger()
    assert v.timeline.lista.currentItem().data(Qt.UserRole) == v.doc.estado_final.cuerpos[ids[1]].op_id
