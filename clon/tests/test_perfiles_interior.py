# -*- coding: utf-8 -*-
"""Punto interior sin triangulación: caras válidas, contraformas, errores y continuidad del documento.

El fallo del mallador se inyecta sobre geometría válida; el contorno cruzado es un caso inválido sintético,
no una reproducción del archivo REMOVEDOR. La pertenencia se comprueba con OCC y con límites analíticos.
"""
import math

import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.TopoDS import TopoDS_Face
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

from omnicad import api
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas
from omnicad.io_archivos.svg import leer_svg
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles as perfiles_mod
from omnicad.restricciones import Boceto


def _alambre(puntos, sentido=1):
    """Alambre cerrado; con `sentido` -1 lo recorre al revés (un hueco va al revés que el borde exterior)."""
    if sentido < 0:
        puntos = list(reversed(puntos))
    w = BRepBuilderAPI_MakeWire()
    for a, b in zip(puntos, puntos[1:] + [puntos[0]], strict=True):
        w.Add(BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge())
    return w.Wire()


def cara_sin_malla():
    """Cara inválida sintética: el hueco cruza el borde exterior."""
    plano = gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    exterior = _alambre([(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)])
    hueco = _alambre([(5, -5, 0), (15, -5, 0), (15, 5, 0), (5, 5, 0)], -1)
    maker = BRepBuilderAPI_MakeFace(plano, exterior, True)
    maker.Add(hueco)
    return maker.Face()


def cara_degenerada():
    """Una cara de área cero (un contorno colineal): no tiene material, y no se puede triangular."""
    plano = gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    return BRepBuilderAPI_MakeFace(plano, _alambre([(0, 0, 0), (5, 0, 0), (10, 0, 0)]), True).Face()


def anillo(plano):
    b = Boceto()
    b.agregar_rectangulo((0, 0), (10, 10))
    b.agregar_rectangulo((2, 2), (8, 8))
    return max(perfiles_mod.detectar_boceto(b, plano), key=lambda p: p.area).cara


def dentro(cara, punto):
    return BRepClass_FaceClassifier(cara, gp_Pnt(*map(float, punto)), 1e-7).State() == TopAbs_IN


@pytest.fixture(params=["vacia", "error", "sin_area"])
def sin_malla(monkeypatch, request):
    def teselar(*args, **kwargs):
        if request.param == "error":
            raise RuntimeError("Fallo controlado del mallador")
        vertices = np.zeros((3 if request.param == "sin_area" else 0, 3), np.float32)
        return vertices, np.zeros_like(vertices)
    monkeypatch.setattr(geo, "teselar", teselar)


def ok(s, tool, **args):
    r = api.llamar(s, tool, args)
    assert r["ok"], r
    return r["result"]


def svg(tmp_path, contenido):
    ruta = tmp_path / "logo.svg"
    ruta.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" '
                    'viewBox="0 0 100 100">' + contenido + '</svg>', encoding="utf-8")
    return ruta


def test_cara_cruzada_es_invalida_y_no_tiene_malla():
    cara = cara_sin_malla()
    assert not geo.es_valida(cara) and len(geo.teselar(cara)[0]) == 0
    with pytest.raises(geo.ErrorGeometria, match="cara inválida"):
        geo.punto_dentro(cara)


@pytest.mark.parametrize("nombre", ["XY", "XZ", "YZ", "inclinado"])
def test_punto_dentro_de_una_cara_valida_sin_triangulacion(sin_malla, nombre):
    plano = geo.Plano("XY" if nombre == "inclinado" else nombre, 177)
    if nombre == "inclinado":
        plano = plano.girado(37)
    cara = anillo(plano)
    assert geo.es_valida(cara) and geo.area(cara) == pytest.approx(64)
    q = geo.punto_dentro(cara)
    assert np.isfinite(np.asarray(q, float)).all()
    assert dentro(cara, q)
    u, v = plano.a_uv(q)
    assert 0 < u < 10 and 0 < v < 10 and not (2 <= u <= 8 and 2 <= v <= 8)


def test_punto_adentro_de_un_perfil_sin_malla(sin_malla):
    cara = anillo(geo.Plano("XY"))
    assert dentro(cara, perfiles_mod._punto_adentro(cara))


@pytest.mark.parametrize("crear", [cara_degenerada, TopoDS_Face, lambda: None])
def test_cara_degenerada_o_ausente_avisa_con_un_error_claro(crear):
    with pytest.raises(geo.ErrorGeometria, match="cara inválida|cara válida"):
        geo.punto_dentro(crear())


def test_no_encontrar_punto_no_acusa_de_invalida_una_cara_valida(sin_malla, monkeypatch):
    cara = anillo(geo.Plano("XY"))
    monkeypatch.setattr(geo, "_dentro_de_cara", lambda *a: False)
    with pytest.raises(geo.ErrorGeometria, match="cara es válida"):
        geo.punto_dentro(cara)


def test_sin_huecos_preserva_el_svg_valido_sin_malla(tmp_path, sin_malla):
    """La cadena del aviso: sin_huecos → _tinta_svg → _punto_adentro, sin sustituir ninguna cara."""
    b = boceto_desde_primitivas(leer_svg(svg(tmp_path, '<path fill-rule="evenodd" '
                                                             'd="M10 10H30V30H10Z M15 15H25V25H15Z"/>')))
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    assert perfiles
    utiles = perfiles_mod.sin_huecos(perfiles, b)      # antes: ValueError (argmax de una secuencia vacía)
    assert len(utiles) == 1 and utiles[0].area == pytest.approx(300)
    assert geo.es_valida(utiles[0].cara)


def test_el_visor_no_rellena_agujeros_ante_un_error(tmp_path, monkeypatch):
    from omnicad.ui.visor3d import perfiles_a_pintar, tris_perfil_terminado
    from types import SimpleNamespace
    b = boceto_desde_primitivas(leer_svg(svg(tmp_path, '<path fill-rule="evenodd" '
                                                    'd="M10 10H30V30H10Z M15 15H25V25H15Z"/>')))
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    antes = b.a_dict()
    original = perfiles_mod._punto_adentro
    def fallar(cara):
        raise geo.ErrorGeometria("No se pudo clasificar el perfil")
    monkeypatch.setattr(perfiles_mod, "_punto_adentro", fallar)
    avisos = []
    assert perfiles_a_pintar(perfiles, b, avisos.append) == []
    assert len(avisos) == 1 and "No se pudo clasificar" in avisos[0]
    br = SimpleNamespace(boceto=b, perfiles=perfiles)
    assert tris_perfil_terminado(br) == []
    assert b.a_dict() == antes and len(perfiles) == 2
    monkeypatch.setattr(perfiles_mod, "_punto_adentro", original)
    tris = np.concatenate(tris_perfil_terminado(br)).reshape(-1, 3, 3)
    assert np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum() / 2 == pytest.approx(300)


@pytest.mark.parametrize("letra", ["A", "B", "O", "P", "R", "8"])
def test_las_letras_siguen_clasificando_sus_agujeros(letra, sin_malla):
    """El agujero de una letra sigue siendo un hueco: no se convierte en región sólida."""
    b = Boceto()
    b.agregar_texto((0, 0), letra, altura=10.0)
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    utiles = perfiles_mod.sin_huecos(perfiles, b)
    assert len(utiles) == 1, [p.area for p in perfiles]
    assert utiles[0].area > 0
    assert sum(p.area for p in perfiles) > utiles[0].area     # el hueco se descartó


def test_perfiles_anidados_un_circulo_dentro_de_un_cuadrado():
    """Un círculo dentro de un rectángulo da DOS perfiles (el anillo y el disco), como en Fusion."""
    b = Boceto()
    b.agregar_rectangulo((0, 0), (40, 40))
    b.agregar_circulo((20, 20), 10)
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    areas = sorted(p.area for p in perfiles)
    assert areas == pytest.approx([math.pi * 100, 1600 - math.pi * 100], rel=1e-6)
    assert all(geo.es_valida(p.cara) for p in perfiles)


def test_contorno_svg_con_curvas_bezier(tmp_path, sin_malla):
    """Un contorno con Bézier: los perfiles se detectan y el punto interior de cada uno se puede determinar."""
    ruta = svg(tmp_path, '<path d="M10 30C10 10 50 10 50 30C50 50 10 50 10 30Z"/>')
    b = boceto_desde_primitivas(leer_svg(ruta))
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    # Green: 2 × ∫[0,1] 60t(1−t) × 240t(1−t) dt = 960 mm²; no es un círculo.
    assert len(perfiles) == 1 and perfiles[0].area == pytest.approx(960, rel=1e-8)
    for p in perfiles:
        q = geo.punto_dentro(p.cara)
        assert dentro(p.cara, q) and geo.es_valida(p.cara)


@pytest.mark.parametrize("ancho,alto", [(1e-6, 1e-6), (1e-4, 1e-4), (1e-4, 1000)])
def test_cara_diminuta_o_muy_fina_sin_malla(ancho, alto, sin_malla):
    cara = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(), gp_Dir(0, 0, 1)), 0, ancho, 0, alto).Face()
    assert geo.es_valida(cara) and geo.area(cara) == pytest.approx(ancho * alto, rel=1e-9, abs=1e-20)
    q = geo.punto_dentro(cara)
    # Independiente del clasificador de OCC, cuya precisión absoluta no alcanza para el lado de 1e-6 mm.
    assert 0 < q[0] < ancho and 0 < q[1] < alto and q[2] == pytest.approx(0)


@pytest.mark.parametrize("distancia", [0, 1e-9, 1e-7, 1e-5])
def test_tolerancias_geometricas_extremas_no_reventan(distancia):
    """Dos círculos casi tangentes: el boceto se resuelve y los perfiles se pintan sin excepción."""
    b = Boceto()
    b.agregar_circulo((0, 0), 20)
    b.agregar_circulo((40 + distancia, 0), 20)
    plano = geo.Plano("XY")
    perfiles = perfiles_mod.detectar_boceto(b, plano)
    assert perfiles
    assert isinstance(perfiles_mod.sin_huecos(perfiles, b), list)


def test_extruir_recalcular_guardar_y_reabrir_sin_malla(tmp_path, sin_malla):
    """Un anillo conserva agujero, firma, área y volumen a través del flujo completo de la API."""
    s = api.Sesion()
    ruta = svg(tmp_path, '<path fill-rule="evenodd" d="M10 10H30V30H10Z M15 15H25V25H15Z"/>')
    r = ok(s, "insert_svg", path=str(ruta), plane="XZ")
    oid = r["object_ids"][0]
    perfiles = ok(s, "get_vector_regions", objects=[oid])["profiles"]
    assert len(perfiles) == 1 and perfiles[0]["area"] == pytest.approx(300)
    receta = s.doc.a_dict()
    ok(s, "extrude", sketch=r["sketch"]["id"], profile=f"object:{oid}", distance=3)
    ok(s, "recompute_all")
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert sum(geo.volumen(c.forma) for c in cuerpos) == pytest.approx(900, rel=1e-6)
    assert all(geo.es_valida(c.forma) for c in cuerpos)
    ok(s, "undo")
    assert s.doc.a_dict() == receta
    ok(s, "redo")
    archivo = tmp_path / "anillo.omnicad"
    ok(s, "save_document", path=str(archivo))
    t = api.Sesion()
    ok(t, "open_document", path=str(archivo))
    ok(t, "recompute_all")
    assert ok(t, "get_vector_regions", objects=[oid])["profiles"] == perfiles
    assert sum(geo.volumen(c.forma) for c in t.doc.estado_final.cuerpos.values()) == pytest.approx(900)


def test_guardar_y_reabrir_no_revienta(tmp_path):
    """El documento con el boceto se guarda y se reabre: los perfiles se vuelven a calcular sin excepción."""
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY")
    ok(s, "add_text", text="REMOVEDOR", font="Arial", height=8)
    archivo = tmp_path / "removedor.omnicad"
    ok(s, "save_document", path=str(archivo))
    t = api.Sesion()
    ok(t, "open_document", path=str(archivo))
    br = next(iter(t.doc.estado_final.bocetos.values()))
    assert br.perfiles
    assert perfiles_mod.sin_huecos(br.perfiles, br.boceto)


def test_boceto_vacio_no_necesita_un_punto_interior(sin_malla):
    from omnicad.ui.visor3d import perfiles_a_pintar
    b = Boceto()
    assert perfiles_mod.detectar_boceto(b, geo.Plano("XY")) == []
    assert perfiles_mod.sin_huecos([], b) == perfiles_a_pintar([], b) == []


def test_isla_en_un_agujero_svg_se_conserva(tmp_path, sin_malla):
    ruta = svg(tmp_path, '<path fill-rule="evenodd" '
                        'd="M10 10H50V50H10Z M20 20H40V40H20Z M25 25H35V35H25Z"/>')
    b = boceto_desde_primitivas(leer_svg(ruta))
    perfiles = perfiles_mod.detectar_boceto(b, geo.Plano("XY"))
    utiles = perfiles_mod.sin_huecos(perfiles, b)
    assert sorted(p.area for p in utiles) == pytest.approx([100, 1200])
    assert all(geo.es_valida(p.cara) for p in utiles)


@pytest.mark.parametrize("lado,origen", [(1e-6, 0), (1e-3, 100000), (1e-3, 100000.0032)])
def test_malla_real_diminuta_o_colapsada_por_float32(lado, origen):
    cara = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(), gp_Dir(0, 0, 1)),
                                  origen, origen + lado, origen, origen + lado).Face()
    assert geo.es_valida(cara)
    q = geo.punto_dentro(cara)
    assert origen < q[0] < origen + lado and origen < q[1] < origen + lado


def test_temporizador_y_terminar_boceto_contienen_fallos_del_mallador(tmp_path, sin_malla, monkeypatch):
    import sys
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    r = ok(s, "insert_svg", path=str(svg(tmp_path, '<path fill-rule="evenodd" '
                                                'd="M10 10H30V30H10Z M15 15H25V25H15Z"/>')), plane="XY")
    errores = []
    monkeypatch.setattr(sys, "excepthook", lambda *e: errores.append(e))
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    try:
        v.set_documento(s.doc)
        v.editar_operacion(r["sketch"]["id"])
        modo = v.modo_boceto
        assert modo.activo
        receta = modo.boceto.a_dict()
        modo._t_perfiles.start(0)
        QTest.qWait(100)
        assert not modo._t_perfiles.isActive() and not errores
        with monkeypatch.context() as parche:
            def fallar(cara):
                raise geo.ErrorGeometria("No se pudo calcular el centro geométrico")
            parche.setattr(perfiles_mod, "_punto_adentro", fallar)
            modo.lienzo.seleccion = r["object_ids"]
            modo.objetos.pivotes.activated.emit(1)
            assert "No se pudo calcular" in modo.objetos.error.text()
            assert modo.boceto.a_dict() == receta and not errores
        QTest.mouseClick(modo.paleta.b_terminar, Qt.LeftButton)
        app.processEvents()
        assert not modo.activo and not errores
        br = v.doc.estado_final.bocetos[r["sketch"]["id"]]
        assert br.boceto.a_dict() == receta
        assert sum(p.area for p in perfiles_mod.sin_huecos(br.perfiles, br.boceto)) == pytest.approx(300)
    finally:
        if v.modo_boceto.activo:
            v.modo_boceto.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_chapa_comparte_el_punto_interior_sin_malla(sin_malla):
    from omnicad.nucleo.chapa import _punto_en_cara
    cara = anillo(geo.Plano("XY"))
    assert dentro(cara, _punto_en_cara(cara))


def test_error_de_clasificacion_por_api_no_modifica_el_documento(tmp_path, monkeypatch):
    s = api.Sesion()
    r = ok(s, "insert_svg", path=str(svg(tmp_path, '<path fill-rule="evenodd" '
                                                'd="M10 10H30V30H10Z M15 15H25V25H15Z"/>')), plane="XY")
    receta = s.doc.a_dict()
    def fallar(cara):
        raise geo.ErrorGeometria("El perfil tiene una cara inválida o sin área interior.")
    monkeypatch.setattr(perfiles_mod, "_punto_adentro", fallar)
    fallo = api.llamar(s, "extrude", {"sketch": r["sketch"]["id"],
                                     "profile": f"object:{r['object_ids'][0]}", "distance": 3})
    assert not fallo["ok"] and fallo["error_kind"] != "INTERNAL_ERROR", fallo
    assert "cara inválida" in fallo["mensaje"] and s.doc.a_dict() == receta
