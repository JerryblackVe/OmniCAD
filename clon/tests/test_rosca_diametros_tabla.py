"""B-122: las clases de las tablas de Fusion modelan sus diámetros mayor y menor, no solo los flancos. Fusion real
(evidencias/fusion_2026-11-01/p7.py): Tr12×3 7e, Ø 8,3175 y 11,882; 7H, Ø 9,1575 y 12,5. Los diámetros salen del modelo: el
máximo de la caja y la distancia del eje; el volumen, de la cuenta exacta del filete barrido."""
import math

import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GeomAbs import GeomAbs_Plane
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import tablas_rosca, tolerancias as tol
from omnicad.timeline.documento import Documento

EJE = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, -100), gp_Pnt(0, 0, 100)).Edge()


def d_min(forma):
    """Ø de lo más cercano al eje, sin las tapas planas."""
    return 2 * min(BRepExtrema_DistShapeShape(EJE, c).Value() for c in g.caras(forma)
                   if BRepAdaptor_Surface(c).GetType() != GeomAbs_Plane)


def d_max(forma):
    (x0, _, _), (x1, _, _) = g.caja_envolvente(forma)
    return x1 - x0


def area_de_rosca(datos, flancos, interna, r_cresta, r_fondo):
    """Área de metal (eje) o de hueco (agujero) en un corte perpendicular al eje."""
    p, t = datos["paso"], math.tan(math.radians(datos["angulo"] / 2))
    filete = lambda r: p / 2 - 2 * (r - flancos / 2) * t * (1 if not interna else -1)  # noqa: E731
    def integrar(a, b, w):
        f = lambda r: w(r) * 2 * math.pi * r  # noqa: E731
        return (b - a) / 6 * (f(a) + 4 * f((a + b) / 2) + f(b)) / p
    if interna:
        return math.pi * r_cresta ** 2 + integrar(r_cresta, r_fondo, lambda r: p / 2 - 2 * (r - flancos / 2) * t)
    return math.pi * r_fondo ** 2 + integrar(r_fondo, r_cresta, filete)


def test_eje_tr12x3_7e_con_los_diametros_medidos_en_fusion():
    forma = sc.rosca(g.cilindro(6, 24), designacion="Tr12x3", clase="7e")
    assert d_max(forma) == pytest.approx(11.882, abs=1e-3)
    assert d_min(forma) == pytest.approx(8.3175, abs=1e-3)
    datos = sc.datos_rosca("Tr12x3")
    flancos = tol.limites_rosca(datos["familia"], datos["diametro"], datos["paso"], "7e")["diametro_flancos"][0]
    losa = g.booleano(forma, g.caja(40, 40, 3, origen=(-20, -20, 10)), "intersecar")
    assert g.volumen(losa) == pytest.approx(3 * area_de_rosca(datos, flancos, False, 11.882 / 2, 8.3175 / 2), rel=1e-3)


def test_agujero_tr12x3_7h_con_los_diametros_medidos_en_fusion():
    herramienta = sc.herramienta_agujero((0, 0, 24), (0, 0, -1), roscado="Tr12x3", profundidad=24, punta="plana", clase="7H")
    assert d_max(herramienta) == pytest.approx(12.5, abs=1e-3)
    datos = sc.datos_rosca("Tr12x3")
    forma = g.booleano(g.caja(30, 30, 24, origen=(-15, -15, 0)), herramienta, "cortar")
    assert d_min(forma) == pytest.approx(9.1575, abs=1e-3)
    losa = g.booleano(forma, g.caja(40, 40, 3, origen=(-20, -20, 10)), "intersecar")
    assert g.volumen(losa) == pytest.approx(3 * (900 - area_de_rosca(datos, 10.65, True, 9.1575 / 2, 12.5 / 2)), rel=1e-3)


def test_rosca_en_un_agujero_de_otro_diametro_tambien_queda_en_la_tabla():
    bloque = g.booleano(g.caja(30, 30, 24, origen=(-15, -15, 0)), g.cilindro(4.5, 24), "cortar")
    forma = sc.rosca(bloque, designacion="Tr12x3", clase="7H", interna=True)
    assert d_min(forma) == pytest.approx(9.1575, abs=1e-3)


def test_la_holgura_de_impresion_corre_los_dos_diametros():
    forma = sc.rosca(g.cilindro(6, 24), designacion="Tr12x3", clase="7e", holgura=0.1)
    assert d_max(forma) == pytest.approx(11.682, abs=1e-3)
    assert d_min(forma) == pytest.approx(8.1175, abs=1e-3)


@pytest.mark.parametrize("familia, designacion, clase, largo", [
    ("trapezoidal", "Tr12x3", "7e", 12), ("acme", None, None, 16), ("iso_tuberia", None, None, 8), ("din_tuberia", None, None, 8)])
def test_otras_familias_de_la_tabla_dan_sus_diametros(familia, designacion, clase, largo):
    filas = tablas_rosca.CLASES[familia]
    if designacion is None:
        designacion = next(d for d, c in filas.items() if any(h[1] is not None for h in c.values()))
        clase = next(k for k, h in filas[designacion].items() if h[1] is not None)
    mayor, _flancos, menor = filas[designacion][clase][1]
    datos = sc.datos_rosca(designacion)
    forma = sc.rosca(g.cilindro(datos["diametro"] / 2, largo), designacion=designacion, clase=clase)
    assert g.es_valida(forma)
    assert d_max(forma) == pytest.approx(mayor, abs=2e-3)
    assert d_min(forma) == pytest.approx(menor, abs=2e-3)


def test_los_diametros_de_toda_la_tabla_dejan_un_surco_que_se_puede_barrer():
    """Ningún tipo de `tablas_rosca.CLASES` deja el fondo sin ancho ni la cresta sin espesor."""
    for filas in tablas_rosca.CLASES.values():
        for designacion, clases in filas.items():
            d = sc.datos_rosca(designacion)
            for clase, hilos in clases.items():
                for interna, hilo in ((True, hilos[0]), (False, hilos[1])):
                    if hilo is None:
                        continue
                    a = tol.desfases_rosca(d["familia"], d["diametro"], d["paso"], clase, interna, d["diametro_flancos"],
                                           d["diametro_menor"])
                    t = math.tan(math.radians(d["angulo"] / 2))
                    medio = d["diametro_flancos"] / 2 + (a["flancos"] if interna else -a["flancos"])
                    ancho = lambda r: d["paso"] / 2 + (-1 if interna else 1) * 2 * (r - medio) * t  # noqa: E731, B023
                    assert a["fondo"] is not None and a["cresta"] is not None
                    assert ancho(a["fondo"] / 2) > 0.02 * d["paso"], (designacion, clase, interna)
                    assert ancho(a["cresta"] / 2) < 0.97 * d["paso"], (designacion, clase, interna)


def test_thread_info_da_el_diametro_menor_del_eje():
    lim = tol.limites_rosca("trapezoidal", 12, 3, "7e")
    assert lim["diametro_menor"] == [8.3175, 8.3175] and lim["diametro_mayor"] == [11.882, 11.882]


def test_las_clases_iso_y_un_no_cambian():
    d = sc.datos_rosca("M10")
    a = tol.desfases_rosca(d["familia"], d["diametro"], d["paso"], "6g", False, d["diametro_flancos"], d["diametro_menor"])
    assert a["fondo"] is None and a["cresta"] is None


def test_receta_vieja_de_rosca_de_tabla_conserva_su_geometria():
    s = api.Sesion()
    r = api.llamar(s, "create_cylinder", {"radius": 6, "height": 24})
    assert r["ok"], r
    r = api.llamar(s, "create_thread", {"faces": "%CYLINDER", "thread": "Tr12x3", "thread_class": "7e"})
    assert r["ok"], r
    forma = lambda d: next(iter(d.estado_final.cuerpos.values())).forma  # noqa: E731
    assert d_max(forma(s.doc)) == pytest.approx(11.882, abs=1e-3)
    datos = s.doc.a_dict()
    del datos["operaciones"][-1]["params"]["version_rosca"]
    viejo = Documento.desde_dict(datos)
    assert viejo.operaciones[-1].p["version_rosca"] == 1
    assert d_max(forma(viejo)) == pytest.approx(12, abs=1e-3) and d_min(forma(viejo)) == pytest.approx(8.803, abs=1e-3)


@pytest.mark.parametrize("familia, mayor", [("unificada", 19.05), ("metrica_plasticos", 10.0)])
def test_b247_un_cilindro_mas_grueso_que_la_rosca_se_tornea_a_su_diametro(familia, mayor):
    """B-247 (video de Fusion del 2026-11-07): Ø20 con un tipo cuyo tamaño mayor es más fino (3/4 UNC, plástico 10)
    no falla: el cilindro queda en el Ø mayor de la rosca, como en Fusion."""
    forma = sc.rosca(g.cilindro(10, 12), familia=familia)
    assert g.es_valida(forma)
    assert d_max(forma) == pytest.approx(mayor, abs=2e-3)


def test_b247_un_agujero_mas_chico_que_la_rosca_se_agranda_al_menor():
    bloque = g.booleano(g.caja(30, 30, 12, origen=(-15, -15, 0)), g.cilindro(3, 12), "cortar")
    forma = sc.rosca(bloque, designacion="M10")
    assert g.es_valida(forma)
    assert d_min(forma) == pytest.approx(sc.datos_rosca("M10")["diametro_menor"], abs=2e-3)


def test_b247_las_recetas_viejas_siguen_rechazando_el_cilindro_grueso():
    with pytest.raises(g.ErrorGeometria, match="más grueso"):
        sc.rosca(g.cilindro(10, 12), designacion="M9", tabla=False)


@pytest.mark.parametrize("radio, designacion, desfase, longitud", [(10, "M30", 0.0, None), (10, "M30", 5.0, 10.0)])
def test_b248_un_eje_mas_fino_que_el_nucleo_se_engrosa_al_mayor(radio, designacion, desfase, longitud):
    """B-248 (video de Fusion del 2026-11-07: M22×3 sobre Ø20 deja r 10,882): el tramo roscado crece al Ø mayor."""
    forma = sc.rosca(g.cilindro(radio, 30), designacion=designacion, desfase=desfase, longitud=longitud)
    assert g.es_valida(forma) and len(g.solidos(forma)) == 1
    assert d_max(forma) == pytest.approx(30.0, abs=2e-3)


def test_b248_un_agujero_mas_ancho_que_el_mayor_se_rellena_al_menor():
    bloque = g.booleano(g.caja(40, 40, 12, origen=(-20, -20, 0)), g.cilindro(7, 12), "cortar")
    forma = sc.rosca(bloque, designacion="M10")
    assert g.es_valida(forma) and len(g.solidos(forma)) == 1
    assert d_min(forma) == pytest.approx(sc.datos_rosca("M10")["diametro_menor"], abs=2e-3)
