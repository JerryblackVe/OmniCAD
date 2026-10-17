"""P23e: efectos del menú del boceto y límites visibles fuera de su editor."""
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QInputDialog

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.timeline.operaciones import OpBoceto
from test_p23_navegador import ventana as ventana, v as v, menu_de, accion


@pytest.fixture
def boceto(v):
    b = Boceto()
    b.agregar_rectangulo((50, 20), (70, 30))
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Boceto de prueba", plano="XY", boceto=b))
    return v, ident


def test_grupo_y_conjunto_desde_menu_boceto(boceto, monkeypatch):
    v, ident = boceto
    s = api.Sesion(v.doc)
    r = api.llamar(s, "manage_browser", {"action": "create_group", "name": "Bocetos"})
    gid = r["result"]["id"]
    accion(accion(menu_de(v, ident), "Desplazar al grupo").menu(), "Bocetos").trigger()
    assert v.navegador.item(ident).parent().data(0, Qt.UserRole) == gid
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("Conjunto de boceto", True))
    accion(menu_de(v, ident), "Crear conjunto de selección").trigger()
    assert api.llamar(s, "get_browser_state", {})["result"]["selection_sets"][0]["items"] == [ident]


def test_extruir_del_menu_usa_perfiles_y_crea_volumen(boceto):
    v, ident = boceto
    accion(menu_de(v, ident), "Extruir").trigger()
    assert v.panel.comando.CLAVE == "extruir"
    assert v.panel.valores["perfiles"][0]["ref"]["boceto"] == ident
    v.panel.set_valor("distancia", "5 mm")
    v.panel.aceptar()
    creados = [c for c in v.doc.estado_final.cuerpos.values() if c.op_id == v.doc.operaciones[-1].id]
    assert len(creados) == 1 and geo.es_valida(creados[0].forma)
    assert geo.volumen(creados[0].forma) == pytest.approx(1000)


def test_plano_desfase_del_boceto_crea_plano_en_su_normal(boceto):
    v, ident = boceto
    accion(menu_de(v, ident), "Plano de desfase").trigger()
    assert v.panel.comando.CLAVE == "plano_desfase"
    v.panel.set_valor("distancia", "7 mm")
    v.panel.aceptar()
    plano = v.doc.estado_final.planos[v.doc.operaciones[-1].id]
    assert plano.origen[2] == pytest.approx(7)


def test_editar_y_redefinir_plano_sin_cambiar_geometria_2d(boceto):
    v, ident = boceto
    accion(menu_de(v, ident), "Editar boceto").trigger()
    assert v.modo_boceto.activo and v.modo_boceto.datos["op"].id == ident
    v.modo_boceto.cancelar()
    accion(menu_de(v, ident), "Redefinir el plano de boceto").trigger()
    assert v.visor.modo == "elegir_plano"
    v.visor.plano_elegido.emit({"ref": "XZ", "plano": geo.Plano("XZ"), "marco": None})
    assert v.doc.operacion(ident).p["plano"] == "XZ"
    br = v.doc.estado_final.bocetos[ident]
    assert np.allclose(br.plano.normal, [0, -1, 0])
    assert sum(p.area for p in br.perfiles) == pytest.approx(200)


def test_seleccionar_plano_mirar_encuadrar_y_encontrar_timeline(boceto):
    v, ident = boceto
    accion(menu_de(v, ident), "Seleccionar el plano de boceto").trigger()
    assert v.seleccion[0]["tipo"] == "plano" and np.allclose(v.seleccion[0]["plano"].normal, [0, 0, 1])
    accion(menu_de(v, ident), "Mirar a").trigger()
    assert np.allclose(v.visor.R[2], [0, 0, 1])
    accion(menu_de(v, ident), "Buscar en la ventana").trigger()
    assert np.allclose(v.visor.objetivo, [60, 25, 0])
    accion(menu_de(v, ident), "Buscar en la secuencia temporal").trigger()
    assert v.timeline.lista.currentItem().data(Qt.UserRole) == ident


def test_configurar_aplica_variante_con_misma_accion(boceto, monkeypatch):
    from omnicad.ui.administrar import DialogoConfiguraciones
    v, ident = boceto
    datos = {"activa": "Sin boceto", "columnas": [{"tipo": "suprimir", "op": ident}],
             "filas": [{"nombre": "Sin boceto", "valores": ["sí"]}]}
    monkeypatch.setattr(DialogoConfiguraciones, "exec", lambda _: 1)
    monkeypatch.setattr(DialogoConfiguraciones, "datos", lambda _: datos)
    accion(menu_de(v, ident), "Configurar").trigger()
    assert v.doc.configuraciones["activa"] == "Sin boceto"
    assert ident not in v.doc.estado_final.bocetos
    v.doc.deshacer()
    assert ident in v.doc.estado_final.bocetos


def test_exportar_dxf_renombrar_visibilidad_y_suprimir_boceto(boceto, tmp_path, monkeypatch):
    v, ident = boceto
    ruta = tmp_path / "boceto.dxf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_a, **_kw: (str(ruta), "DXF"))
    accion(menu_de(v, ident), "Exportar DXF").trigger()
    assert ruta.is_file() and b"LINE" in ruta.read_bytes()
    accion(menu_de(v, ident), "Cambiar nombre").trigger()
    v.navegador.item(ident).setText(0, "Renombrado")
    assert v.doc.operacion(ident).nombre == "Renombrado"
    accion(menu_de(v, ident), "Mostrar/ocultar").trigger()
    assert ident in v.ocultos
    assert ident not in {b.op_id for b in v.visor._bocetos_visibles()}
    accion(menu_de(v, ident), "Suprimir").trigger()
    assert ident not in v.doc.estado_final.bocetos


@pytest.mark.parametrize("texto,clave,visible", [("Ocultar perfil", "perfil", False),
    ("Mostrar cota", "cotas", True), ("Ocultar las geometrías proyectadas", "proyectadas", False),
    ("Ocultar geometrías de construcción", "construccion", False)])
def test_capas_actuan_en_editor_y_fuera_quedan_grisadas(boceto, texto, clave, visible):
    v, ident = boceto
    a = accion(menu_de(v, ident), texto)
    assert not a.isEnabled() and "editar" in a.toolTip()
    v.editar_operacion(ident)
    v.modo_boceto.paleta.checks[clave].setChecked(not visible)
    a = accion(menu_de(v, ident), texto)
    assert a.isEnabled()
    a.trigger()
    assert v.modo_boceto.paleta.checks[clave].isChecked() == visible
    if clave == "perfil":
        assert v.visor.opciones_boceto["perfil"] is False
    else:
        assert v.modo_boceto.lienzo.mostrar[clave] == visible


def test_api_sketch_view_actua_en_la_ventana(boceto, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    v, ident = boceto
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "find_in_window"})["ok"]
    assert np.allclose(v.visor.objetivo, [60, 25, 0])
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "projected", "visible": False})["ok"]
    assert v.modo_boceto.lienzo.mostrar["proyectadas"] is False
