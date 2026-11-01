# -*- coding: utf-8 -*-
"""Sistema común de los paneles de herramienta (`ui/comando.py` + `ui/formulario.py`): cabecera que sigue al modo,
etiquetas por modo, jerarquía de campos («Más opciones» plegable con resumen), filas de selección que dicen qué hay
elegido, ancho fijo, mensajes tipados, Enter seguro y plegar sin recalcular. Docs: docs/auditorias/ui_paneles_2026-10-31.md."""
import types

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_manipuladores import _doc_caja, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import formulario as F
from omnicad.ui.comando import Campo, Casilla, Comando, Expresion, Opciones, Seleccion, hit_desde_ref, preseleccion
from omnicad.ui.comandos import CATALOGO


def _titulo(panel):
    return panel.titulo.text()


def _hit(doc, ref):
    return hit_desde_ref(ref, doc.estado_final)


# ---------------------------------------------------------------- descripción de lo elegido (sin Qt)
def _ctx():
    cuerpo = types.SimpleNamespace(nombre="Caja1")
    op = types.SimpleNamespace(id="op3", nombre="PlanoMedio")
    return types.SimpleNamespace(estado=types.SimpleNamespace(cuerpos={"op1.c1": cuerpo}),
                                 doc=types.SimpleNamespace(operaciones=[op]))


def test_describir_ref_dice_tipo_rasgo_y_a_que_pertenece():
    c = _ctx()
    cara = {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano", "normal": [0, 0, 1]}}
    assert F.describir_ref(cara, c) == "Cara plana +Z · Caja1"
    inclinada = {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano", "normal": [0.6, 0, 0.8]}}
    assert F.describir_ref(inclinada, c) == "Cara plana · Caja1"
    cil = {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "cilindro", "radio": 5.0}}
    assert F.describir_ref(cil, c) == "Cara cilíndrica Ø10 · Caja1"
    linea = {"tipo": "arista", "cuerpo": "op1.c1", "firma": {"geom": "linea", "largo": 30.0}}
    assert F.describir_ref(linea, c) == "Arista recta 30 mm · Caja1"
    assert F.describir_ref({"tipo": "eje", "id": "Z"}, c) == "Eje Z"
    assert F.describir_ref({"tipo": "plano", "id": "op3"}, c) == "Plano PlanoMedio"
    assert F.describir_ref({"tipo": "cuerpo", "cuerpo": "op9.c1"}, c) == "op9.c1 (ya no existe)"


def test_describir_seleccion_resume_varios_y_marca_el_origen():
    c = _ctx()
    a = {"ref": {"tipo": "arista", "cuerpo": "op1.c1", "firma": {"geom": "linea", "largo": 10.0}}, "origen": "previa"}
    b = {"ref": {"tipo": "arista", "cuerpo": "op1.c1", "firma": {"geom": "circulo", "radio": 4.0}}}
    assert F.describir_seleccion([], c) == ("", "")
    assert F.describir_seleccion([a], c)[0] == "Arista recta 10 mm · Caja1 · preelegida"
    texto, detalle = F.describir_seleccion([a, b], c)
    assert texto == "2 aristas · Caja1" and detalle.count("\n") == 1 and "Ø8" in detalle


def test_texto_filtros_no_repite_la_variante_de_un_tipo_general():
    assert F.texto_filtros({"perfil", "cara_plana"}) == "Elegir perfil o cara plana"
    assert F.texto_filtros({"cara", "cara_plana", "arista"}) == "Elegir cara o arista"
    assert F.texto_filtros({"cuerpo"}) == "Elegir cuerpo"


def test_preseleccion_marca_lo_que_venia_elegido():
    campos = [Seleccion("a", "A", {"cuerpo"}, maximo=None)]
    hit = {"tipo": "cuerpo", "ref": {"tipo": "cuerpo", "cuerpo": "x"}}
    r = preseleccion(campos, [hit])
    assert r["a"][0]["origen"] == "previa" and "origen" not in hit      # copia: el hit del visor no se toca


# ---------------------------------------------------------------- cabecera, etiquetas y jerarquía
def _patron(app_qt, forma="rectangular"):  # noqa: F811
    doc = _doc_caja()
    v = {"cuerpos": [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})]}
    return (*_panel(CATALOGO["patron_rectangular_3d"](), doc, v), doc)


def test_la_cabecera_del_patron_sigue_al_modo_elegido(app_qt):  # noqa: F811
    panel, _visor, _est, _doc = _patron(app_qt)
    assert _titulo(panel) == "PATRÓN RECTANGULAR"
    panel.set_valor("forma", "circular")
    assert _titulo(panel) == "PATRÓN CIRCULAR"
    panel.set_valor("forma", "ruta")
    assert _titulo(panel) == "PATRÓN EN TRAYECTORIA"
    panel.set_valor("forma", "puntos")
    assert _titulo(panel) == "PATRÓN EN PUNTOS"
    panel.cancelar()


def test_al_cambiar_de_modo_la_seleccion_activa_pasa_a_un_campo_visible(app_qt):  # noqa: F811
    panel, *_ = _patron(app_qt)
    assert panel.activa is not None and panel.activa.clave == "dir1"
    panel.set_valor("forma", "circular")
    assert panel.activa.clave == "eje"                               # el filtro del visor sigue al campo que se ve
    panel.set_valor("forma", "ruta")
    assert panel.activa.clave == "ruta"
    panel.cancelar()


def test_la_etiqueta_de_la_distancia_dice_que_mide_segun_la_distribucion(app_qt):  # noqa: F811
    panel, *_ = _patron(app_qt)
    assert panel.etiquetas["d1"].text() == "Extensión total"
    panel.set_valor("distribucion", "espaciado")
    assert panel.etiquetas["d1"].text() == "Separación entre instancias"
    panel.cancelar()


def test_editar_antepone_editar_al_titulo_del_modo(app_qt):  # noqa: F811
    from omnicad.ui.comando import ContextoComando, PanelComando
    doc = _doc_caja()
    panel, visor, _e = _panel(CATALOGO["patron_circular_3d"](), doc, {
        "cuerpos": [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})], "eje": [_hit(doc, {"tipo": "eje", "id": "Z"})]})
    panel._calcular_previa()
    op = panel.ultima_op
    panel.cancelar()
    doc.agregar(op)
    editor = PanelComando(CATALOGO["patron_circular_3d"](), ContextoComando(doc, None, op), visor)
    assert _titulo(editor) == "EDITAR PATRÓN CIRCULAR"
    editor.cancelar()


def test_la_seccion_mas_opciones_resume_lo_activo_y_plegar_no_recalcula(app_qt):  # noqa: F811
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO["patron_rectangular_3d"](), doc, {})
    seccion = panel.seccion
    assert seccion is not None and not seccion.abierta and seccion.resumen.isHidden()
    llamadas = []
    original = panel._programar
    panel._programar = lambda: (llamadas.append(1), original())
    seccion.boton.setChecked(True)                                   # desplegar
    seccion.boton.setChecked(False)                                  # plegar
    assert llamadas == []                                            # ver u ocultar opciones no pide ningún cálculo
    panel.set_valor("suprimir", "2")                                 # algo activo dentro de la sección cerrada
    assert "Copias suprimidas: 2" in seccion.resumen.text() and not seccion.resumen.isHidden()
    assert panel.valores["suprimir"] == "2"                          # plegada conserva el valor
    assert panel.valores_visibles()["suprimir"] == "2"
    panel.cancelar()


def test_un_paso_editado_con_algo_avanzado_abre_la_seccion_sola(app_qt):  # noqa: F811
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO["patron_rectangular_3d"](), doc, {"suprimir": "2"})
    assert panel.seccion.abierta
    panel.cancelar()


def test_un_valor_invalido_dentro_de_mas_opciones_abre_la_seccion_y_lo_dice(app_qt):  # noqa: F811
    from omnicad.ui.comandos import solido
    doc = _doc_caja()
    panel, *_ = _panel(solido.Extruir(), doc, {})
    assert not panel.seccion.abierta
    panel.set_valor("conicidad", "abc")
    panel._calcular_previa()
    assert panel.seccion.abierta                                     # el valor inválido no queda escondido
    panel.cancelar()


# ---------------------------------------------------------------- selección legible
def test_la_fila_de_seleccion_vacia_dice_que_espera_y_la_llena_dice_que_hay(app_qt):  # noqa: F811
    from omnicad.ui.comandos import solido
    doc = _doc_caja()
    panel, *_ = _panel(solido.ExtruirCara(), doc, {})
    fila = panel.filas_sel["caras"]
    assert fila.boton.toolTip() == "Elegir cara plana" and fila.boton.text().startswith("Eleg") and not fila.borrar.isVisible()
    panel.set_valor("caras", [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})])
    assert "Cuerpo" in fila.boton.text() or "op1" in fila.boton.text()
    panel.cancelar()


def test_el_menu_de_la_fila_quita_un_elemento_sin_borrar_los_demas(app_qt):  # noqa: F811
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO["patron_rectangular_3d"](), doc, {})
    a = _hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})
    b = dict(a, ref={"tipo": "cuerpo", "cuerpo": "op1.c2"})
    panel.set_valor("cuerpos", [a, b])
    fila = panel.filas_sel["cuerpos"]
    assert fila.boton.toolTip().count("\n") == 1 and not fila.revisar.isHidden()
    panel._quitar(panel._por_clave["cuerpos"], 0)
    assert [h["ref"]["cuerpo"] for h in panel.valores["cuerpos"]] == ["op1.c2"]
    panel.cancelar()


# ---------------------------------------------------------------- tamaño, mensajes y teclado
@pytest.mark.parametrize("clave,ancho", [("extruir_cara", "simple"), ("extruir", "normal"), ("multitransformar", "ancho")])
def test_el_ancho_es_fijo_por_tipo_de_formulario_y_no_cambia_al_teclear(app_qt, clave, ancho):  # noqa: F811
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO[clave](), doc, {})
    assert panel.desplazador.width() == F.ANCHOS[ancho]
    antes = panel.width()
    for campo in panel.campos:
        if isinstance(campo, Expresion):
            panel.set_valor(campo.clave, "123456789012345678901234567890 mm")
            break
    assert panel.width() == antes
    panel.cancelar()


def test_ningun_panel_del_catalogo_desborda_en_horizontal(app_qt):  # noqa: F811
    """Abre cada comando que se puede abrir con un documento mínimo: nada se recorta a la derecha."""
    doc = _doc_caja()
    malos = []
    for clave, clase in sorted(CATALOGO.items()):
        try:
            panel, *_ = _panel(clase(), doc, {})
        except Exception:  # noqa: BLE001 — los que piden otro contexto (malla, chapa…) los cubre el inventario de la ventana
            continue
        panel.show()
        QApplication.processEvents()
        if panel.desplazador.widget().minimumSizeHint().width() > panel.desplazador.viewport().width() + 1:
            malos.append(clave)
        panel.cancelar()
    assert not malos, malos


def test_los_mensajes_se_distinguen_por_clase_y_llevan_simbolo(app_qt):  # noqa: F811
    from omnicad.ui.comandos import solido
    doc = _doc_caja()
    panel, *_ = _panel(solido.ExtruirCara(), doc, {})
    panel._calcular_previa()
    assert panel.mensaje.property("tipo") == "instruccion" and panel.icono_mensaje.text() == "➜"
    panel._mostrar("Valor mal escrito", tipo="invalido")
    assert panel.icono_mensaje.text() == "✖" and panel.mensaje.property("tipo") == "invalido"
    panel._mostrar("Calculando…", tipo="calculando")
    assert panel.icono_mensaje.text() == "⏳"
    panel._mostrar("")
    assert panel.mensaje.isHidden() and panel.icono_mensaje.isHidden()
    panel.cancelar()


def test_el_aviso_de_antes_se_va_al_elegir_sin_esperar_a_la_previa(app_qt):  # noqa: F811
    """Duplicar con uniones: tras «Elegí al menos un destino», elegir uno limpia el aviso al instante (no queda a la vista
    hasta que corre la previa). El «Calculando…» de la previa aparte no se toca."""
    from test_duplicar_con_uniones import _escena
    from omnicad.ui.comandos.ensamblar import DuplicarConUniones
    s, *_ = _escena()
    panel, *_ = _panel(DuplicarConUniones(), s.doc, {})
    panel.show()
    panel.aceptar()
    assert "destino" in panel.mensaje.text() and not panel.mensaje.isHidden()
    panel._activar(next(c for c in panel.campos if c.clave == "destinos"))
    panel._t_previa.stop()
    panel._elegida({"ref": "Destino A", "tipo": "origen_union", "dibujo": []})
    assert panel.mensaje.text() == "" and panel.mensaje.isHidden() and panel.icono_mensaje.isHidden()
    panel._mostrar("Calculando…", tipo="calculando")
    panel._programar()
    assert panel.mensaje.text() == "Calculando…"
    panel.cancelar()


def test_enter_no_acepta_si_el_foco_lo_atiende_un_control(app_qt, monkeypatch):  # noqa: F811
    from PySide6.QtWidgets import QListWidget
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO["multitransformar"](), doc, {})
    aceptados = []
    panel.aceptar = lambda: aceptados.append(1)
    lista = QListWidget(panel)
    monkeypatch.setattr(QApplication, "focusWidget", staticmethod(lambda: lista))
    QTest.keyClick(panel, Qt.Key_Return)
    assert aceptados == []                                           # una lista con foco se queda con el Enter
    monkeypatch.setattr(QApplication, "focusWidget", staticmethod(lambda: panel.boton_cancelar))
    cancelados = []
    panel.cancelado.connect(lambda: cancelados.append(1))
    QTest.keyClick(panel, Qt.Key_Return)
    assert aceptados == [] and cancelados == [1]                     # Enter sobre Cancelar cancela, no acepta
    monkeypatch.setattr(QApplication, "focusWidget", staticmethod(lambda: None))
    QTest.keyClick(panel, Qt.Key_Return)
    assert aceptados == [1]                                          # sin nada especial con foco, Enter acepta


def test_los_botones_dicen_su_tecla_y_el_pie_de_teclas_solo_aparece_con_modificadores(app_qt):  # noqa: F811
    doc = _doc_caja()
    panel, *_ = _panel(CATALOGO["caja"](), doc, {})
    assert "Enter" in panel.boton_ok.toolTip() and "Esc" in panel.boton_cancelar.toolTip()
    assert panel.pie_teclas.isHidden()
    panel.cancelar()


def test_un_campo_nuevo_acepta_grupo_avanzado_y_etiqueta_dinamica():
    c = Campo("x", "X", grupo="G", avanzado=True, etiqueta_si=lambda v: "Y")
    assert (c.grupo, c.avanzado, c.etiqueta_si({})) == ("G", True, "Y")
    assert Casilla("c", "C").avanzado is False and Opciones("o", "O", {"a": "A"}).grupo is None
    assert Comando().titulo_icono({}) == ("", "")


def test_el_editor_de_materiales_cabe_en_pantalla_con_los_botones_siempre_a_la_vista(app_qt):  # noqa: F811
    from PySide6.QtWidgets import QPushButton, QScrollArea
    from omnicad.ui.aspectos_ui import EditorMateriales
    d = EditorMateriales({})
    d.show()
    QApplication.processEvents()
    tope = d.screen().availableGeometry().height()
    assert d.height() <= tope and d.findChildren(QScrollArea)
    assert not d.g_transl.isChecked() and all(not w.isVisible() for w in d.g_transl.findChildren(QPushButton))
    for b in (d.b_aceptar, d.b_cancelar, d.b_aplicar):
        assert d.rect().contains(b.mapTo(d, b.rect().center()))
    d.g_transl.setChecked(True)                                      # un grupo encendido muestra su contenido
    assert d.profundidad.isVisible()
    d.close()


def test_un_campo_avanzado_con_grupo_cuelga_de_su_propio_rotulo(app_qt):  # noqa: F811
    class _Prueba(Comando):
        CLAVE, TITULO, ICONO = "prueba_grupos", "Prueba", "caja"

        def campos(self, ctx):
            return [Expresion("a", "A", grupo="Uno"), Expresion("b", "B", grupo="Uno"),
                    Expresion("c", "C", grupo="Dos", avanzado=True), Expresion("d", "D", grupo="Uno")]

    panel, *_ = _panel(_Prueba(), _doc_caja(), {})
    por_claves = {tuple(c): r for r, c in panel.rotulos}
    assert sorted(por_claves) == [("a", "b", "d"), ("c",)] or sorted(por_claves) == [("a", "b"), ("c",), ("d",)]
    for (rotulo, claves) in panel.rotulos:                           # cada rótulo manda solo sobre sus campos
        assert all(panel._por_clave[k].grupo == rotulo.text() for k in claves)
    panel.cancelar()


def test_la_seleccion_no_salta_a_un_campo_escondido_en_mas_opciones(app_qt):  # noqa: F811
    class _Prueba(Comando):
        CLAVE, TITULO, ICONO = "prueba_sel_avanzada", "Prueba", "caja"

        def campos(self, ctx):
            return [Seleccion("a", "A", {"cuerpo"}), Seleccion("b", "B", {"cuerpo"}, avanzado=True)]

    doc = _doc_caja()
    panel, *_ = _panel(_Prueba(), doc, {})
    assert panel.activa.clave == "a" and not panel.seccion.abierta
    panel._elegida(_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"}))
    assert panel.activa.clave == "a"                                 # «B» está plegada: la selección se queda donde se ve
    panel.seccion.boton.setChecked(True)
    panel._activar(panel._por_clave["b"])
    assert panel.activa.clave == "b"
    panel.cancelar()
