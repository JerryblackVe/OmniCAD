# -*- coding: utf-8 -*-
"""Bugs SOL-1 a SOL-6 y SOL-31 a SOL-33 (auditoría de Sólido, 2026-10-24): cada uno con la prueba que lo reproducía."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r


def falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


def _cuerpos(s):
    return list(s.doc.estado_final.cuerpos.values())


def test_sol1_rosca_externa_a_izquierdas():
    s = api.Sesion()
    llamar(s, "create_cylinder", height=20, radius=5)
    cilindro = geo.volumen(_cuerpos(s)[0].forma)
    llamar(s, "create_thread", faces="%CYLINDER", thread="M10", left_hand=False)
    derecha = geo.volumen(_cuerpos(s)[0].forma)
    llamar(s, "undo")
    llamar(s, "create_thread", faces="%CYLINDER", thread="M10", left_hand=True)
    izquierda = _cuerpos(s)[0].forma
    assert geo.es_valida(izquierda)
    assert geo.volumen(izquierda) < cilindro
    assert geo.volumen(izquierda) == pytest.approx(derecha, rel=0.01)


def test_sol2_vaciado_quitando_todas_las_caras_falla():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Caja")
    r = falla(s, "shell", body="Caja", faces="all", thickness=2)
    assert "todas las caras" in r["mensaje"]
    llamar(s, "shell", body="Caja", faces=">Z", thickness=2)          # quitar una sola sigue andando


def test_sol3_agujero_en_un_punto_fuera_de_la_cara_falla():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10)
    r = falla(s, "create_hole", face=">Z", diameter=5, depth=5, points=[[0, 0], [5, 5], [50, 50]])
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "fuera de la cara" in r["mensaje"]
    llamar(s, "create_hole", face=">Z", diameter=5, depth=5, points=[[0, 0], [5, 5]])


def test_sol4_unir_cuerpos_que_no_se_tocan_avisa():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="A")
    llamar(s, "create_box", length=10, width=10, height=10, x=100, name="B")
    r = llamar(s, "boolean_operation", target="A", tools=["B"], operation="join")
    assert "piezas sueltas" in str(r)


def test_sol5_escalar_pasado_del_tope_de_1_km_falla():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Caja")
    r = falla(s, "scale_body", bodies="Caja", factor=1e6)
    assert "1 km" in r["mensaje"]
    llamar(s, "scale_body", bodies="Caja", factor=100)


def test_sol6_patron_circular_de_mas_de_una_vuelta_falla():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, x=30, name="Caja")
    r = falla(s, "circular_pattern", bodies="Caja", count=4, total_angle=720)
    assert "una sobre otra" in r["mensaje"]
    llamar(s, "circular_pattern", bodies="Caja", count=3, total_angle=360)


def _perfil_revolucion():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_rectangle", x1=10, y1=0, x2=20, y2=5)
    return s


def test_sol31_revolucion_de_mas_de_360_falla():
    s = _perfil_revolucion()
    for angulo in (400, 720):
        r = falla(s, "revolve", sketch="Perfil", axis="z", angle=f"{angulo} deg")
        assert "360" in r["mensaje"]
    llamar(s, "revolve", sketch="Perfil", axis="z", angle="360 deg")
    assert geo.volumen(_cuerpos(s)[0].forma) == pytest.approx(math.pi * (400 - 100) * 5, rel=1e-4)


def test_sol31_dos_lados_que_suman_mas_de_una_vuelta_falla():
    s = _perfil_revolucion()
    falla(s, "revolve", sketch="Perfil", axis="z", angle="200 deg", direction="two_sides", angle2="200 deg")
    llamar(s, "revolve", sketch="Perfil", axis="z", angle="100 deg", direction="two_sides", angle2="200 deg")


def test_sol32_patrones_con_copias_encimadas_fallan():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
    r = falla(s, "rectangular_pattern", bodies="Caja", x_count=3, x_spacing="0 mm")
    assert "cero" in r["mensaje"]
    r = falla(s, "circular_pattern", bodies="Caja", count=4, total_angle=0)
    assert "ángulo del patrón circular" in r["mensaje"]
    llamar(s, "rectangular_pattern", bodies="Caja", x_count=3, x_spacing="20 mm")
    assert len(_cuerpos(s)) == 3


def test_sol33_desfase_de_cara_en_cero_y_desmoldeo_en_cero_fallan():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Caja")
    r = falla(s, "offset_faces", faces=">Z", distance=0)
    assert "cero" in r["mensaje"]
    llamar(s, "offset_faces", faces=">Z", distance=1)


def test_sol33_desmoldeo_en_cero_falla():
    from omnicad.nucleo import solidos_modificar as sm
    caja = geo.caja(20, 20, 10)
    lateral = [c for c in geo.caras(caja) if abs(sm._punto_normal(c)[1][2]) < 1e-6][:1]
    plano = geo.Plano("XY")
    with pytest.raises(geo.ErrorGeometria, match="cero"):
        sm.desmoldeo(caja, lateral, (0, 0, 1), 0.0, plano)
    assert geo.es_valida(sm.desmoldeo(caja, lateral, (0, 0, 1), 3.0, plano))


def test_sol33_pulsar_tirar_en_cero_se_rechaza_en_la_ventana():
    from PySide6.QtWidgets import QApplication

    from omnicad.api import selectores as sl
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import CaraDesfase, PulsarTirar
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="10"))
    c, e = sl.elegir_uno(api.Sesion(doc), ">Z", "cara")
    hit = hit_desde_ref(sl.referencia(c, e), doc.estado_final)
    for comando, campo in ((PulsarTirar(), "objetos"), (CaraDesfase(), "caras")):
        ctx = ContextoComando(doc)
        v = {k.clave: k.defecto for k in comando.campos(ctx)}
        v.update({campo: [hit], "distancia": "0 mm"})
        with pytest.raises(Exception, match="cero"):
            doc.previsualizar(comando.construir(v, ctx))
        v["distancia"] = "1 mm"
        doc.previsualizar(comando.construir(v, ctx))


def test_sol35_el_factor_de_escala_no_lleva_unidad():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Caja")
    r = falla(s, "scale_body", bodies="Caja", factor="2 mm")
    assert "no lleva unidad" in r["mensaje"]
    llamar(s, "scale_body", bodies="Caja", factor="2")


def test_sol30_mensajes_que_no_enganan():
    s = api.Sesion()
    llamar(s, "create_box", length=30, width=30, height=30, name="Caja")
    r = falla(s, "create_boss", positions=[[0, 0, 20]])
    assert "el elemento 0" in r["mensaje"] and "no es array" not in r["mensaje"]
    from omnicad.nucleo import solidos_modificar as sm
    from omnicad.nucleo import referencias as refs
    caja = geo.caja(30, 30, 30)
    with pytest.raises(geo.ErrorGeometria, match="no entra"):
        sm.empalme(caja, [{"aristas": refs.subformas(caja, "arista")[:1], "tipo": "constante", "radio": 100.0}])
    llamar(s, "create_construction_plane", plane="XY", offset=100, name="Alto")
    r = falla(s, "split_body", body="Caja", tool="Alto", extend=True)
    assert "probá extenderla" not in r["mensaje"]


def test_sol4_unir_en_cadena_no_avisa_en_falso():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="A")
    llamar(s, "create_box", length=10, width=10, height=10, x=10, name="B")
    llamar(s, "create_box", length=10, width=10, height=10, x=20, name="C")
    r = llamar(s, "boolean_operation", target="A", tools=["B", "C"], operation="join")
    assert "piezas sueltas" not in str(r)                        # C toca a B, que ya está unido a A
    assert len(_cuerpos(s)) == 1
    llamar(s, "create_box", length=10, width=10, height=10, x=100, name="D")
    r = llamar(s, "boolean_operation", target="A", tools=["D"], operation="join")
    assert "piezas sueltas" in str(r)


def test_sol30_lista_anidada_dice_cual_elemento_esta_mal():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="S")
    r = falla(s, "draw_spline", points=[[0, "a"], [1, 1]])
    assert "no es array" not in r["mensaje"] and "'a'" in r["mensaje"]


def test_sol32_patron_en_ruta_con_distancia_cero_y_circular_simetrico_fallan():
    s = api.Sesion()
    llamar(s, "create_box", length=4, width=4, height=4, name="Caja")
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=100, end_y=0)
    r = falla(s, "path_pattern", bodies="Caja", path_sketch="Ruta", count=3, distance=0)
    assert "cero" in r["mensaje"]
    llamar(s, "path_pattern", bodies="Caja", path_sketch="Ruta", count=3, distance=50)
    s = api.Sesion()
    llamar(s, "create_box", length=4, width=4, height=4, x=20, name="Caja")
    r = falla(s, "circular_pattern", bodies="Caja", count=4, total_angle=0, symmetric=True)
    assert "ángulo del patrón circular" in r["mensaje"]
    llamar(s, "circular_pattern", bodies="Caja", count=4, total_angle=90, symmetric=True)


def _toca_cresta(forma, z):
    """Qué ángulos (cada 10°) tocan la cresta de la rosca a r = 4,9 en la altura z."""
    return [geo.punto_toca(forma, (4.9 * math.cos(math.radians(t)), 4.9 * math.sin(math.radians(t)), z), 1e-6)
            for t in range(0, 360, 10)]


def test_sol1_la_cresta_avanza_a_derechas_o_a_izquierdas_segun_el_pedido():
    giro = {}
    for izquierda in (False, True):
        s = api.Sesion()
        llamar(s, "create_cylinder", height=20, radius=5)
        llamar(s, "create_thread", faces="%CYLINDER", thread="M10", left_hand=izquierda)
        forma = _cuerpos(s)[0].forma
        a, b = _toca_cresta(forma, 10.0), _toca_cresta(forma, 10.375)      # un cuarto de paso más arriba
        assert sum(a) == 5                                                  # una cresta: 50° de arco
        giro[izquierda] = [n for n in range(36) if a[n - 9] == b[n]].__len__() == 36 and 9 or (
            -9 if all(a[(n + 9) % 36] == b[n] for n in range(36)) else 0)
    assert giro == {False: 9, True: -9}


@pytest.mark.parametrize("cambio", ["revolucion", "escala", "desmoldeo"])
def test_recetas_viejas_con_valores_que_hoy_se_rechazan_abren_con_el_paso_en_rojo(cambio):
    s = api.Sesion()
    if cambio == "revolucion":
        llamar(s, "create_sketch", plane="XZ", name="Perfil")
        llamar(s, "draw_rectangle", x1=10, y1=0, x2=20, y2=5)
        llamar(s, "revolve", sketch="Perfil", axis="z", angle="90 deg")
        clave, valor = "angulo", "400 deg"
    elif cambio == "escala":
        llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
        llamar(s, "scale_body", bodies="Caja", factor="2")
        clave, valor = "factor", "2 mm"
    else:
        llamar(s, "create_box", length=20, width=20, height=10, name="Caja")
        llamar(s, "draft", faces="|X", angle=3, pull_direction="z")
        clave, valor = "angulo", "0 deg"
    receta = llamar(s, "get_recipe")["result"]["recipe"]
    paso = receta["operaciones"][-1]
    assert clave in paso["params"], paso["params"]
    paso["params"][clave] = valor
    from omnicad.timeline.documento import Documento
    doc = Documento.desde_dict(receta)                                # como abrir un .omnicad viejo: no revienta
    doc.recalcular()
    assert doc.resultados[-1].estado == "error", "el paso debió quedar en rojo"


def test_sol37_revolucion_de_curvas_y_de_geometria_pura_rechaza_mas_de_360():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_line", start_x=10, start_y=0, end_x=20, end_y=5, sketch="Perfil")
    curva = llamar(s, "get_sketch", sketch="Perfil")["result"]["entities"][0]["id"]
    r = falla(s, "create_surface_revolve", profiles={"sketch": "Perfil", "curve": curva}, axis="z", angle="720 deg")
    assert "360" in r["mensaje"]
    llamar(s, "create_surface_revolve", profiles={"sketch": "Perfil", "curve": curva}, axis="z", angle="360 deg")
    with pytest.raises(geo.ErrorGeometria, match="360"):
        geo.revolver([geo.caja(1, 1, 1)], (0, 0, 0), (0, 0, 1), 400.0)
