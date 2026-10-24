# -*- coding: utf-8 -*-
"""Herramientas del documento, de parámetros, de boceto y de preferencias de la ola 4 de B-80: configuraciones
(MCP-27), comentarios (MCP-51), proyectos recientes (MCP-52), preferencias (MCP-54), redefinir el plano de un
boceto (MCP-78), CSV de parámetros (MCP-82) y las opciones nuevas de select_bodies (MCP-93)."""
import math

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo


@pytest.fixture
def s():
    return api.Sesion(crear_documento_ejemplo())


def ok(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(sesion, nombre, kind="INVALID_ARGUMENTS", **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    return r


def _volumen_placa(sesion):
    return next(c["volume"] for c in ok(sesion, "get_scene_info")["bodies"] if c["id"] == "op2.c1")


# ---------------------------------------------------------------- MCP-27: configuraciones
def test_configuraciones_tabla_aplicar_y_deshacer(s):
    base = _volumen_placa(s)
    assert ok(s, "manage_configurations") == {"columns": [], "rows": [], "active": ""}
    r = ok(s, "manage_configurations", action="set", columns=[{"type": "parameter", "name": "ancho"}],
           rows=[{"name": "Chica", "values": ["30 mm"]}, {"name": "Grande", "values": ["90 mm"]}])
    assert [f["name"] for f in r["rows"]] == ["Chica", "Grande"] and r["active"] == ""
    assert _volumen_placa(s) == pytest.approx(base)                      # set solo guarda la tabla
    ok(s, "manage_configurations", action="apply", row="Grande")
    assert ok(s, "get_parameters")["parameters"][0]["expression"] == "90 mm"
    assert _volumen_placa(s) > base
    ok(s, "manage_configurations", action="apply", row="Chica")
    assert _volumen_placa(s) < base
    ok(s, "undo")                                                         # volver a Grande de un solo paso
    assert ok(s, "manage_configurations")["active"] == "Grande"
    r = ok(s, "manage_configurations", action="add_row", row="Mediana", values=["60 mm"])
    assert [f["name"] for f in r["rows"]] == ["Chica", "Grande", "Mediana"]
    r = ok(s, "manage_configurations", action="delete_row", row="Grande")
    assert r["active"] == "" and [f["name"] for f in r["rows"]] == ["Chica", "Mediana"]
    assert ok(s, "manage_configurations", action="clear") == {"columns": [], "rows": [], "active": ""}


def test_configuraciones_errores_no_dejan_nada(s):
    falla(s, "manage_configurations", action="set", columns=[{"type": "parameter", "name": "no_existe"}], rows=[],
          kind="PARAMETER_NOT_FOUND")
    falla(s, "manage_configurations", action="set", columns=[{"type": "parameter", "name": "ancho"}],
          rows=[{"name": "A", "values": ["1 mm"]}, {"name": "A", "values": ["2 mm"]}])
    falla(s, "manage_configurations", action="set", columns=[{"type": "parameter", "name": "ancho"}],
          rows=[{"name": "A", "values": []}])
    falla(s, "manage_configurations", action="apply", row="Ausente")
    falla(s, "manage_configurations", action="set")
    assert ok(s, "manage_configurations")["rows"] == []


# ---------------------------------------------------------------- MCP-51: comentarios
def test_comentarios_agregar_listar_y_borrar(s):
    assert ok(s, "manage_comments")["comments"] == []
    ok(s, "manage_comments", action="add", text="  Revisar el radio  ")
    r = ok(s, "manage_comments", action="add", text="Cambiar el material")
    assert [c["text"] for c in r["comments"]] == ["Revisar el radio", "Cambiar el material"]
    assert r["comments"][1]["index"] == 1 and r["comments"][0]["date"]
    assert [c["text"] for c in ok(s, "manage_comments", action="delete", index=0)["comments"]] == ["Cambiar el material"]
    falla(s, "manage_comments", action="delete", index=5)
    falla(s, "manage_comments", action="add", text="   ")
    assert s.doc.comentarios[0]["texto"] == "Cambiar el material"        # el mismo dato que ve la ventana


# ---------------------------------------------------------------- MCP-52 y MCP-54: preferencias y recientes
def _ini(tmp_path, nombre="prefs.ini", **valores):
    from PySide6.QtCore import QSettings
    ruta = tmp_path / nombre
    q = QSettings(str(ruta), QSettings.IniFormat)
    for clave, valor in valores.items():
        q.setValue(clave, valor)
    q.sync()
    return str(ruta)


def test_proyectos_recientes_existentes_y_en_orden(s, tmp_path, monkeypatch):
    a, b = tmp_path / "uno.omnicad", tmp_path / "dos.omnicad"
    a.write_text("x")
    b.write_text("y")
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", _ini(tmp_path, recientes=[str(b), str(tmp_path / "borrado.omnicad"), str(a)]))
    docs = ok(s, "list_recent_documents")["documents"]
    assert [d["name"] for d in docs] == ["dos", "uno"]                   # sin el que ya no existe
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", _ini(tmp_path, "vacio.ini"))
    assert ok(s, "list_recent_documents")["documents"] == []
    falla(s, "list_recent_documents", settings_path="otro.ini")            # un agente no elige el archivo de ajustes


def test_preferencias_consultar_validar_y_lista_blanca(s, tmp_path, monkeypatch):
    ini = _ini(tmp_path)
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", ini)
    falla(s, "get_preferences", settings_path=str(tmp_path / "otro.ini"))     # un agente no elige el archivo de ajustes
    falla(s, "set_preference", key="general/camara", value="ortografica", settings_path=str(tmp_path / "otro.ini"))
    por_clave = {p["key"]: p for p in ok(s, "get_preferences")["preferences"]}
    assert por_clave["general/camara"]["value"] == "perspectiva" and "ortografica" in por_clave["general/camara"]["options"]
    r = ok(s, "set_preference", key="general/camara", value="ortografica")
    assert r["value"] == "ortografica"
    assert ok(s, "get_preferences", keys=["general/camara"])["preferences"][0]["value"] == "ortografica"
    ok(s, "set_preference", key="graficos/preset", value="calidad")
    assert ok(s, "get_preferences", keys=["vista/efecto_suelo"])["preferences"][0]["value"] is True
    ok(s, "set_preference", key="vista/efecto_suelo", value=False)       # tocar un efecto = «personalizar»
    assert ok(s, "get_preferences", keys=["graficos/preset"])["preferences"][0]["value"] == "personalizar"
    for clave, valor in (("general/puente_agentes", True), ("general/puente_codigo", True), ("geometria/motor", "omnikernel"),
                         ("general/tema", "x"), ("general/camara", "inventada"), ("general/autoguardado_min", 999),
                         ("general/invertir_zoom", "si")):
        falla(s, "set_preference", key=clave, value=valor)
    falla(s, "get_preferences", keys=["general/puente_agentes"])


def test_las_preferencias_autorizadas_existen_en_la_ventana():
    """Las claves y los valores por defecto de la lista blanca no se desvían de ui/preferencias.py."""
    from omnicad.api.herramientas_preferencias import _OPCIONES
    from omnicad.ui.preferencias import DEFECTOS
    for clave, (defecto, _opciones) in _OPCIONES.items():
        assert clave in DEFECTOS, clave
        assert DEFECTOS[clave] == defecto, clave


# ---------------------------------------------------------------- MCP-78: redefinir el plano de un boceto
def test_redefinir_el_plano_mueve_el_boceto_conservando_la_forma():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY", name="Base")
    ok(s, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    ok(s, "extrude", sketch="Base", distance=5)
    caja = ok(s, "get_physical_properties")["total"]["bounding_box"]
    assert caja["size"] == [20, 10, 5]
    r = ok(s, "redefine_sketch_plane", sketch="Base", plane="XZ")
    assert r["outside_profiles"] == [] and r["sketch"]["plane"] == "XZ"
    caja = ok(s, "get_physical_properties")["total"]["bounding_box"]
    assert caja["size"] == pytest.approx([20, 5, 10]) or sorted(caja["size"]) == [5, 10, 20]
    assert ok(s, "get_physical_properties")["total"]["volume"] == pytest.approx(1000)
    falla(s, "redefine_sketch_plane", sketch="Base", plane="no_existe", kind="PLANE_NOT_FOUND")
    ok(s, "undo")
    assert ok(s, "get_physical_properties")["total"]["bounding_box"]["size"] == [20, 10, 5]


# ---------------------------------------------------------------- MCP-82: CSV de parámetros
def test_exportar_e_importar_parametros_ida_y_vuelta(s, tmp_path):
    csv_ruta = tmp_path / "carpeta nueva" / "parametros.csv"
    r = ok(s, "export_parameters", path=str(csv_ruta))
    assert r["count"] == 3 and csv_ruta.read_text(encoding="utf-8").splitlines()[0] == "Name,Unit,Expression,Value,Comments"
    falla(s, "export_parameters", path=str(csv_ruta), kind="FILE_EXISTS")
    ajeno = tmp_path / "inicio.bat"
    ajeno.write_text("echo hola")
    falla(s, "export_parameters", path=str(ajeno), overwrite=True)           # solo escribe .csv: no pisa archivos ajenos
    assert ajeno.read_text() == "echo hola"
    ok(s, "export_parameters", path=str(csv_ruta), overwrite=True)
    nueva = api.Sesion()
    ok(nueva, "import_parameters", path=str(csv_ruta))
    original = {p["name"]: p["expression"] for p in ok(s, "get_parameters")["parameters"] if "source" not in p}   # los dN de cotas no se exportan
    assert {p["name"]: p["expression"] for p in ok(nueva, "get_parameters")["parameters"]} == original
    ok(nueva, "undo")
    assert ok(nueva, "get_parameters")["parameters"] == []                # un solo paso de deshacer


def test_importar_parametros_valida_y_no_cambia_nada(s, tmp_path):
    antes = ok(s, "get_parameters")["parameters"]
    casos = {"sin_cabecera.csv": "a,b\n1,2\n", "unidad.csv": "Name,Unit,Expression\nx,parsec,10\n",
             "vacia.csv": "Name,Unit,Expression\n", "duplicado.csv": "Name,Unit,Expression\nx,mm,1\nx,mm,2\n",
             "mala_expresion.csv": "Name,Unit,Expression\nx,mm,1 +\n", "nombre.csv": "Name,Unit,Expression\n1x,mm,3\n"}
    for nombre, contenido in casos.items():
        ruta = tmp_path / nombre
        ruta.write_text(contenido, encoding="utf-8")
        r = api.llamar(s, "import_parameters", {"path": str(ruta)})
        assert not r["ok"], nombre
    falla(s, "import_parameters", path=str(tmp_path / "no_existe.csv"), kind="FILE_NOT_FOUND")
    assert ok(s, "get_parameters")["parameters"] == antes
    actualizar = tmp_path / "ok.csv"
    actualizar.write_text("Name,Unit,Expression,Comments\nancho,mm,100,nuevo\nextra,deg,45,\n", encoding="utf-8")
    ok(s, "import_parameters", path=str(actualizar), mode="merge")
    parametros = {p["name"]: p for p in ok(s, "get_parameters")["parameters"]}
    assert parametros["ancho"]["value"] == 100 and parametros["extra"]["value"] == pytest.approx(45)
    assert "alto_placa" in parametros                                      # merge conserva lo ajeno al CSV


# ---------------------------------------------------------------- MCP-93: select_bodies con filtros
def test_select_bodies_por_nombre_tamano_e_invertido():
    s = api.Sesion()
    for nombre, lado, x in (("Tornillo", 5, 0), ("Tuerca", 8, 20), ("Placa grande", 40, 60)):
        ok(s, "create_box", length=lado, width=lado, height=lado, x=x, name=nombre)
    elegidos = []
    s.seleccionar_cuerpos = lambda ids: elegidos.append(list(ids))        # el hook que arma la ventana en vivo
    nombres = {c["name"]: c["id"] for c in ok(s, "get_scene_info")["bodies"]}

    def ids(*ns):
        return [nombres[n] for n in ns]

    assert ok(s, "select_bodies", by_name="tu")["selected_bodies"] == ids("Tuerca")
    assert ok(s, "select_bodies", by_name="T*")["selected_bodies"] == ids("Tornillo", "Tuerca")
    assert ok(s, "select_bodies", by_size={"min": 10})["selected_bodies"] == ids("Tuerca", "Placa grande")
    diagonal = lambda lado: lado * math.sqrt(3)                           # noqa: E731
    assert ok(s, "select_bodies", by_size={"max": diagonal(8)})["selected_bodies"] == ids("Tornillo", "Tuerca")
    assert ok(s, "select_bodies", by_name="T*", by_size={"min": 10})["selected_bodies"] == ids("Tuerca")
    assert ok(s, "select_bodies", by_name="T*", invert=True)["selected_bodies"] == ids("Placa grande")
    assert ok(s, "select_bodies", bodies=["Tornillo"], invert=True)["selected_bodies"] == ids("Tuerca", "Placa grande")
    assert ok(s, "select_bodies", bodies=[])["selected_bodies"] == []
    assert elegidos[-1] == [] and len(elegidos) == 8
    falla(s, "select_bodies", by_size={"min": 5, "max": 1})
    falla(s, "select_bodies", by_size={"ancho": 1})
    falla(s, "select_bodies", by_size={"min": -1})
    s.seleccionar_cuerpos = None
    falla(s, "select_bodies", by_name="T", kind="APP_NOT_RUNNING")
