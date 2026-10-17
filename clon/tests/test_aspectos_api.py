# -*- coding: utf-8 -*-
"""Aspectos (MODIFICAR › Aspecto de Fusion): biblioteca, Mis aspectos, favoritos, «En este diseño», asignación a
cuerpos y a CARAS, y las herramientas set_appearance / edit_appearance / manage_appearance / list_appearances."""
import json

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.nucleo import aspectos as asp
from omnicad.nucleo import geometria as geo
from omnicad.timeline import aspectos_doc as ad
from omnicad.timeline.documento import Documento


@pytest.fixture(autouse=True)
def usuario(tmp_path, monkeypatch):
    """«Mis aspectos» y los favoritos van a un archivo de prueba: nunca el del usuario."""
    monkeypatch.setenv("OMNICAD_ASPECTOS", str(tmp_path / "aspectos.json"))
    return tmp_path / "aspectos.json"


def _escena():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    assert api.llamar(s, "create_cylinder", {"height": 30, "radius": 10, "x": 90})["ok"]
    return s


def _ok(s, herramienta, **args):
    r = api.llamar(s, herramienta, args)
    assert r["ok"], r
    return r["result"]


def _falla(s, herramienta, tipo, **args):
    r = api.llamar(s, herramienta, args)
    assert not r["ok"] and r["error_kind"] == tipo, r


# ---------------------------------------------------------------- núcleo: ficha, biblioteca, miniaturas
def test_la_biblioteca_trae_las_familias_de_fusion_y_todo_es_valido():
    familias = asp.categorias_con_aspectos(asp.BIBLIOTECA)
    assert {"Acondicionamiento del terreno", "Cristal", "Espejo", "Hormigón", "Líquido", "Madera", "Madera (sólido)",
            "Metal", "Otro", "Piedra", "Pintura", "Plástico"} == set(familias)
    assert len(asp.BIBLIOTECA) > 60 and len({n.casefold() for n in asp.BIBLIOTECA}) == len(asp.BIBLIOTECA)
    for nombre, a in asp.BIBLIOTECA.items():
        assert a["nombre"] == nombre and asp.normalizar(a) == a            # ya viene normalizado: no cambia


def test_normalizar_acota_y_rechaza_lo_que_no_es_un_aspecto():
    a = asp.normalizar({"nombre": "  X  ", "reflectancia": 5, "aspereza": -2, "color": [255, 0, 0],
                        "resalte": {"anisotropia": 9, "forma": "no existe"}})
    assert a["nombre"] == "X" and a["reflectancia"] == 1.0 and a["aspereza"] == 0.0 and a["color"] == [1.0, 0.0, 0.0]
    assert a["resalte"]["anisotropia"] == 1.0 and a["resalte"]["forma"] == asp.FORMAS_RESALTE[0]
    for malo in ({"color": "rojo"}, {"color": [1, 2]}, {"reflectancia": "mucha"}, {"relieve": {"archivo": "x"}},
                 {"aspereza": float("nan")}):
        with pytest.raises(geo.ErrorGeometria):
            asp.normalizar(malo)
    with pytest.raises(geo.ErrorGeometria):
        asp.normalizar([1, 2, 3])


def test_acabado_de_es_lo_que_entiende_el_render():
    from omnicad.nucleo import render_cpu as rc
    acabado = asp.acabado_de(asp.BIBLIOTECA["Latón - Pulido"])
    assert set(acabado) == set(rc.ACABADO_DEFECTO) and acabado["rugosidad"] == asp.BIBLIOTECA["Latón - Pulido"]["aspereza"]
    assert rc.acabado_normalizado(acabado)["metalico"] == 1.0


def test_miniatura_es_una_esfera_iluminada():
    metal, goma = (asp.miniatura_rgba(asp.BIBLIOTECA[n], 48) for n in ("Cromo - Pulido", "Goma - Negra"))
    assert metal.shape == (48, 48, 4) and metal.dtype == np.uint8
    assert metal[0, 0, 3] == 0 and metal[24, 24, 3] == 255                 # las esquinas son aire; el centro, esfera
    assert metal[..., :3].max() > goma[..., :3].max() + 80                 # el cromo brilla más que la goma negra
    vidrio = asp.miniatura_rgba(asp.BIBLIOTECA["Vidrio - Transparente"], 48)
    assert vidrio[24, 24, 3] < 200                                         # lo transparente se ve traslúcido


def test_mis_aspectos_y_favoritos_viajan_por_un_archivo_que_no_se_corrompe(usuario):
    propio = asp.agregar_mio({"nombre": "Mi verde", "color": [0.1, 0.6, 0.2], "aspereza": 0.7})
    assert asp.cargar_usuario()["mis"]["Mi verde"] == propio and asp.buscar("mi VERDE") == propio
    with pytest.raises(geo.ErrorGeometria):
        asp.agregar_mio({"nombre": "Mi verde"})                           # ya existe: pide reemplazar
    assert asp.agregar_mio({"nombre": "Mi verde", "color": [0, 0, 1]}, reemplazar=True)["color"] == [0.0, 0.0, 1.0]
    with pytest.raises(geo.ErrorGeometria):
        asp.agregar_mio({"nombre": "Acero - Pulido"})                     # no pisa la biblioteca
    assert asp.marcar_favorito("Mi verde") == ["Mi verde"] and asp.marcar_favorito("Cromo - Pulido")[-1] == "Cromo - Pulido"
    assert asp.marcar_favorito("Mi verde", False) == ["Cromo - Pulido"]
    assert asp.quitar_mio("Mi verde") and not asp.quitar_mio("Mi verde")
    assert [p.name for p in usuario.parent.iterdir()] == ["aspectos.json"]       # sin temporales sueltos
    usuario.write_text("{ esto no es json", encoding="utf-8")
    assert asp.cargar_usuario() == {"mis": {}, "favoritos": []}              # un archivo dañado no tumba a nadie
    usuario.write_text(json.dumps({"mis": {"malo": {"color": "rojo"}, "bueno": {"nombre": "bueno"}},
                                   "favoritos": ["x", 5]}), encoding="utf-8")
    assert list(asp.cargar_usuario()["mis"]) == ["bueno"] and asp.cargar_usuario()["favoritos"] == ["x"]


# ---------------------------------------------------------------- set_appearance: cuerpos y caras
def test_set_appearance_con_la_biblioteca_crea_el_aspecto_del_diseno_y_lo_reusa():
    s = _escena()
    r = _ok(s, "set_appearance", bodies=["op1.c1"], appearance="hormigón - liso")
    assert r["appearance_id"] == "asp1" and r["bodies"][0]["appearance"] == "Hormigón - Liso"
    props = s.doc.propiedades["op1.c1"]
    assert props["aspecto"] == "asp1" and props["apariencia"] == asp.BIBLIOTECA["Hormigón - Liso"]["color"]
    assert props["acabado"]["nombre"] == "Hormigón - Liso"
    r = _ok(s, "set_appearance", bodies=["op2.c1"], appearance="Hormigón - Liso")        # el mismo: no se duplica
    assert r["appearance_id"] == "asp1" and len(ad.lista(s.doc)) == 1
    cuerpos, caras = ad.usos(s.doc, "asp1")
    assert sorted(cuerpos) == ["op1.c1", "op2.c1"] and caras == []
    r = _ok(s, "set_appearance", bodies=["op2.c1"], appearance="asp1", color="#112233")   # por id y con otro color
    assert r["appearance_id"] == "asp2" and ad.buscar(s.doc, "asp2")["nombre"] == "Hormigón - Liso (1)"
    _falla(s, "set_appearance", "NOT_FOUND", bodies=["op1.c1"], appearance="Plutonio")
    _falla(s, "set_appearance", "INVALID_ARGUMENTS", bodies=["op1.c1"], faces=">Z")


def test_set_appearance_en_caras_pinta_la_cara_y_no_el_cuerpo():
    s = _escena()
    r = _ok(s, "set_appearance", faces=">Z", body="op1.c1", appearance="Granito - Gris")
    assert r["faces"] == 1 and r["bodies"][0]["id"] == "op1.c1"
    props = s.doc.propiedades["op1.c1"]
    assert "apariencia" not in props and len(props["caras"]) == 1
    cara = props["caras"][0]
    assert cara["ref"]["tipo"] == "cara" and cara["apariencia"] == asp.BIBLIOTECA["Granito - Gris"]["color"]
    assert ad.caras_con_aspecto(s.doc, s.doc.estado_final) == [("op1.c1", cara["ref"], cara["apariencia"])]
    _ok(s, "set_appearance", faces=">Z", body="op1.c1", color="#ff0000")           # la misma cara: se reemplaza
    assert len(s.doc.propiedades["op1.c1"]["caras"]) == 1
    assert s.doc.propiedades["op1.c1"]["caras"][0]["apariencia"] == [1.0, 0.0, 0.0]
    _ok(s, "set_appearance", faces="<Z", body="op1.c1", color="#00ff00")
    assert len(s.doc.propiedades["op1.c1"]["caras"]) == 2
    _ok(s, "undo")                                                                 # cada llamada es UN paso
    assert len(s.doc.propiedades["op1.c1"]["caras"]) == 1
    r = _ok(s, "set_appearance", faces=">Z", body="op1.c1")                         # sin nada: quita la de esa cara
    assert r["cleared"] and "caras" not in s.doc.propiedades.get("op1.c1", {})


def test_el_color_suelto_no_crea_un_aspecto_del_diseno():
    s = _escena()
    _ok(s, "set_appearance", bodies=["op1.c1"], color="#336699")
    assert ad.lista(s.doc) == [] and s.doc.propiedad("op1.c1", "aspecto") is None
    assert s.doc.propiedad("op1.c1", "apariencia") == pytest.approx([0.2, 0.4, 0.6])
    assert s.doc.propiedad("op1.c1", "acabado") is None


# ---------------------------------------------------------------- edit_appearance
def test_editar_un_aspecto_del_diseno_pone_al_dia_cuerpos_y_caras_en_un_paso():
    s = _escena()
    _ok(s, "set_appearance", bodies=["op1.c1"], appearance="Acero - Pulido")
    _ok(s, "set_appearance", faces=">Z", body="op2.c1", appearance="Acero - Pulido")
    r = _ok(s, "edit_appearance", appearance="Acero - Pulido", color="#224466", roughness=0.9, reflectance=0.3,
            highlight_shape="Nítida", anisotropy=0.4)
    assert r["bodies_updated"] == ["op1.c1"] and r["faces_updated"] == 1
    a = r["appearance"]
    assert a["color"] == "#224466" and a["roughness"] == 0.9 and a["highlights"]["shape"] == "Nítida"
    assert a["highlights"]["anisotropy"] == 0.4 and a["highlights"]["color"] == "#ffffff"      # el resto del resalte sigue
    assert s.doc.propiedades["op1.c1"]["apariencia"] == pytest.approx([0x22 / 255, 0x44 / 255, 0x66 / 255])
    assert s.doc.propiedades["op1.c1"]["acabado"]["rugosidad"] == 0.9
    assert s.doc.propiedades["op2.c1"]["caras"][0]["apariencia"] == s.doc.propiedades["op1.c1"]["apariencia"]
    _ok(s, "undo")
    assert s.doc.propiedades["op1.c1"]["apariencia"] == asp.BIBLIOTECA["Acero - Pulido"]["color"]
    assert ad.buscar(s.doc, "asp1")["aspereza"] == asp.BIBLIOTECA["Acero - Pulido"]["aspereza"]


def test_editar_uno_de_la_biblioteca_hace_una_copia_y_no_toca_el_original():
    s = _escena()
    r = _ok(s, "edit_appearance", appearance="Cromo - Pulido", color="#ff8800")
    assert r["copied_from"] == "Cromo - Pulido" and r["scope"] == "design" and r["appearance"]["id"] == "asp1"
    assert asp.BIBLIOTECA["Cromo - Pulido"]["color"] == [0.95, 0.95, 0.96]            # el original no cambió
    assert ad.buscar(s.doc, "asp1")["color"] == pytest.approx([1.0, 0x88 / 255, 0.0])
    r = _ok(s, "edit_appearance", appearance="Cromo - Pulido", name="Naranja cromado")
    assert r["appearance"]["name"] == "Naranja cromado" and r["bodies_updated"] == []
    _falla(s, "edit_appearance", "NOT_FOUND", appearance="No existe", color="#ffffff")
    _falla(s, "edit_appearance", "INVALID_ARGUMENTS", appearance="Naranja cromado", name="  ")
    _falla(s, "edit_appearance", "INVALID_ARGUMENTS", appearance="Naranja cromado", color="rojo")


def test_crear_un_aspecto_en_el_diseno_y_en_mis_aspectos(usuario):
    s = _escena()
    r = _ok(s, "edit_appearance", appearance="Resina", create=True, base="Plástico - Mate (Gris)", color="#aa00aa",
            translucency=True, translucency_depth=0.5, emissive=True, luminance=250)
    a = r["appearance"]
    assert a["id"] == "asp1" and a["translucency"] == {"enabled": True, "depth_mm": 0.5, "color": "#00ebcc"}
    assert a["emissive"]["enabled"] and a["emissive"]["luminance_cd_m2"] == 250 and a["roughness"] == 0.6
    _falla(s, "edit_appearance", "NAME_EXISTS", appearance="resina", create=True)
    r = _ok(s, "edit_appearance", appearance="Mi barniz", scope="mine", create=True, base="Pintura - Brillante (Azul)",
            varnish=0.5)
    assert r["saved"] and asp.cargar_usuario()["mis"]["Mi barniz"]["barniz"] == 0.5 and usuario.exists()
    r = _ok(s, "edit_appearance", appearance="Mi barniz", scope="mine", name="Mi barniz 2", roughness=0.2)
    assert list(asp.cargar_usuario()["mis"]) == ["Mi barniz 2"] and r["appearance"]["roughness"] == 0.2
    _falla(s, "edit_appearance", "NOT_FOUND", appearance="Mi barniz", scope="mine", color="#ffffff")


def test_relieve_y_corte_van_embebidos_y_se_validan(tmp_path):
    s = _escena()
    png = tmp_path / "ruido.png"
    Image.new("L", (16, 16), 128).save(png)
    _ok(s, "edit_appearance", appearance="Relieve", create=True, bump_image=str(png), bump_amount=2.5,
        cutout_image=str(png))
    a = ad.buscar(s.doc, "Relieve")
    assert a["relieve"]["archivo"] == "ruido.png" and a["relieve"]["cantidad"] == 2.5 and a["corte"]["archivo"] == "ruido.png"
    r = _ok(s, "edit_appearance", appearance="Relieve", bump_amount=4)
    assert r["appearance"]["bump"]["amount"] == 4
    r = _ok(s, "edit_appearance", appearance="Relieve", bump_image="")
    assert r["appearance"]["bump"] is None and r["appearance"]["cutout"]["file"] == "ruido.png"
    _falla(s, "edit_appearance", "INVALID_ARGUMENTS", appearance="Relieve", bump_amount=1)        # sin relieve
    _falla(s, "edit_appearance", "FILE_NOT_FOUND", appearance="Relieve", bump_image=str(tmp_path / "no.png"))
    falso = tmp_path / "falso.png"
    falso.write_bytes(b"esto no es una imagen")
    _falla(s, "edit_appearance", "INVALID_ARGUMENTS", appearance="Relieve", cutout_image=str(falso))


# ---------------------------------------------------------------- manage_appearance y list_appearances
def test_menu_de_en_este_diseno_duplicar_renombrar_suprimir_mis_aspectos_y_favoritos(usuario):
    s = _escena()
    _ok(s, "set_appearance", bodies=["op1.c1"], appearance="Madera - Roble")
    r = _ok(s, "manage_appearance", action="duplicate", appearance="Madera - Roble")
    assert r["appearance"]["name"] == "Madera - Roble (1)" and r["appearance"]["id"] == "asp2"
    r = _ok(s, "manage_appearance", action="rename", appearance="asp2", name="Roble claro")
    assert r["appearance"]["name"] == "Roble claro"
    _falla(s, "manage_appearance", "INVALID_ARGUMENTS", action="delete", appearance="asp1")       # lo usa op1.c1
    r = _ok(s, "manage_appearance", action="delete", appearance="asp1", remove_users=True)
    assert r["bodies_cleared"] == ["op1.c1"] and "op1.c1" not in s.doc.propiedades
    assert [a["id"] for a in ad.lista(s.doc)] == ["asp2"]
    r = _ok(s, "manage_appearance", action="copy_to_mine", appearance="Roble claro")
    assert r["scope"] == "mine" and "Roble claro" in asp.cargar_usuario()["mis"]
    r = _ok(s, "manage_appearance", action="copy_to_mine", appearance="Roble claro")                   # otra copia: lleva el número
    assert r["appearance"]["name"] == "Roble claro (1)"
    assert _ok(s, "manage_appearance", action="delete_mine", appearance="Roble claro (1)")["deleted"] == "Roble claro (1)"
    assert _ok(s, "manage_appearance", action="add_favorite", appearance="Roble claro")["favorites"] == ["Roble claro"]
    assert _ok(s, "manage_appearance", action="add_favorite", appearance="Hormigón - Liso")["favorites"][-1] == "Hormigón - Liso"
    assert _ok(s, "manage_appearance", action="remove_favorite", appearance="Roble claro")["favorites"] == ["Hormigón - Liso"]
    assert _ok(s, "manage_appearance", action="delete_mine", appearance="Roble claro")["deleted"] == "Roble claro"
    _falla(s, "manage_appearance", "NOT_FOUND", action="delete_mine", appearance="Roble claro")
    _falla(s, "manage_appearance", "NOT_FOUND", action="duplicate", appearance="nada")


def test_list_appearances_por_alcance(usuario):
    s = _escena()
    assert _ok(s, "list_appearances")["appearances"] == []
    _ok(s, "set_appearance", bodies=["op1.c1"], appearance="Hormigón - Liso")
    _ok(s, "manage_appearance", action="copy_to_mine", appearance="Hormigón - Liso", name="Mi hormigón")
    _ok(s, "manage_appearance", action="add_favorite", appearance="Granito - Gris")
    diseno = _ok(s, "list_appearances")["appearances"]
    assert [(a["id"], a["name"], a["bodies"]) for a in diseno] == [("asp1", "Hormigón - Liso", ["op1.c1"])]
    biblioteca = _ok(s, "list_appearances", scope="library", query="piedra")["appearances"]
    assert {a["category"] for a in biblioteca} == {"Piedra"} and all(a["scope"] == "library" for a in biblioteca)
    assert [a["name"] for a in _ok(s, "list_appearances", scope="mine")["appearances"]] == ["Mi hormigón"]
    assert [a["name"] for a in _ok(s, "list_appearances", scope="favorites")["appearances"]] == ["Granito - Gris"]
    todo = _ok(s, "list_appearances", scope="all")
    assert {a["scope"] for a in todo["appearances"]} == {"design", "library", "mine"} and "Piedra" in todo["categories"]


# ---------------------------------------------------------------- guardado y reemplazo de la lista del panel
def test_el_diseno_guarda_y_abre_con_sus_aspectos_y_las_caras_pintadas(tmp_path):
    s = _escena()
    _ok(s, "set_appearance", bodies=["op1.c1"], appearance="Hormigón - Liso")
    _ok(s, "set_appearance", faces=">Z", body="op2.c1", appearance="Granito - Gris")
    ruta = proyecto.guardar(s.doc, tmp_path / "con_aspectos.omnicad")
    d = proyecto.abrir(ruta)
    assert [a["nombre"] for a in ad.lista(d)] == ["Hormigón - Liso", "Granito - Gris"]
    assert d.propiedades["op1.c1"]["aspecto"] == "asp1"
    assert [c[0] for c in ad.caras_con_aspecto(d, d.estado_final)] == ["op2.c1"]


def test_reemplazar_lista_renumera_los_nuevos_y_pone_al_dia_a_los_que_cambiaron():
    s = _escena()
    _ok(s, "set_appearance", bodies=["op1.c1"], appearance="Cerámica - Blanca")
    base = ad.lista(s.doc)
    editado = dict(base[0], color=[0.0, 0.0, 1.0])
    duplicado = dict(base[0], id="nuevo1", nombre="Cerámica - Blanca (1)")
    mapa = ad.reemplazar_lista(s.doc, [editado, duplicado])
    assert mapa == {"nuevo1": "asp2"} and [a["id"] for a in ad.lista(s.doc)] == ["asp1", "asp2"]
    assert s.doc.propiedades["op1.c1"]["apariencia"] == [0.0, 0.0, 1.0]
    with pytest.raises(geo.ErrorGeometria):                                   # sacar uno que se usa es un error
        ad.reemplazar_lista(s.doc, [duplicado])
    assert [a["id"] for a in ad.lista(s.doc)] == ["asp1", "asp2"]             # y no cambió nada


def test_set_propiedades_es_un_solo_paso_de_deshacer_y_no_renombra():
    doc = Documento()
    doc.set_propiedades({"a": {"x": 1}, "b": {"y": 2}})
    assert doc.propiedades == {"a": {"x": 1}, "b": {"y": 2}} and len(doc._deshacer) == 1
    doc.set_propiedades({"a": {"x": None}})
    assert "a" not in doc.propiedades
    doc.deshacer()
    assert doc.propiedades["a"] == {"x": 1}
    with pytest.raises(Exception, match="nombres"):
        doc.set_propiedades({"a": {"nombre": "z"}})
