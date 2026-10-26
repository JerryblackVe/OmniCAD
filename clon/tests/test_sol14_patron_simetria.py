"""SOL-14: patrón y simetría de caras, componentes y operaciones."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _bloque():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Bloque", x=30)    # x de 20 a 40; z de 0 a 10
    return s


def _superficies(s):
    return [c for c in s.doc.estado_final.cuerpos.values() if c.tipo == "superficie"]


def test_patron_rectangular_de_caras_deja_superficies():
    s = _bloque()
    llamar(s, "rectangular_pattern", faces=">Z", x_count=3, x_spacing=50)
    sup = _superficies(s)
    assert len(sup) == 2
    assert all(geo.area(c.forma) == pytest.approx(400) for c in sup)
    xs = sorted(geo.centro_masa(c.forma, True)[0] for c in sup)
    assert xs == pytest.approx([80, 130])
    assert geo.volumen(s.cuerpo("Bloque").forma) == pytest.approx(4000)
    llamar(s, "undo")
    assert not _superficies(s)


def test_patron_circular_de_componentes_copia_componente_y_cuerpos():
    s = _bloque()
    llamar(s, "create_component", bodies=["Bloque"], name="Taco")
    llamar(s, "circular_pattern", count=4, components=["Taco"], axis="z")
    estado = s.doc.estado_final
    assert len(estado.componentes) == 4
    cuerpos = list(estado.cuerpos.values())
    assert len(cuerpos) == 4 and all(geo.volumen(c.forma) == pytest.approx(4000) for c in cuerpos)
    assert len({c.componente for c in cuerpos}) == 4
    nombres = sorted(d["nombre"] for d in estado.componentes.values())
    assert nombres[0].startswith("Taco")


def test_simetria_de_caras_y_de_componentes():
    s = _bloque()
    llamar(s, "mirror", faces=">Z", plane="YZ")
    (sup,) = _superficies(s)
    assert geo.centro_masa(sup.forma, True)[0] == pytest.approx(-30)
    llamar(s, "create_component", bodies=["Bloque"], name="Taco")
    llamar(s, "mirror", components=["Taco"], plane="YZ")
    estado = s.doc.estado_final
    assert len(estado.componentes) == 2
    reflejado = [c for c in estado.cuerpos.values() if c.tipo == "solido" and geo.centro_masa(c.forma)[0] < 0]
    assert len(reflejado) == 1 and geo.centro_masa(reflejado[0].forma)[0] == pytest.approx(-30)


def test_simetria_de_una_operacion_refleja_el_agujero():
    s = api.Sesion()
    llamar(s, "create_box", length=80, width=20, height=10, name="Placa")             # x de -40 a 40
    cil = llamar(s, "create_cylinder", radius=3, height=10, x=25, y=0, operation="cut", target="Placa")
    paso = cil["feature"]["id"]
    una = 80 * 20 * 10 - math.pi * 90
    assert geo.volumen(s.cuerpo("Placa").forma) == pytest.approx(una)
    llamar(s, "mirror", features=[paso], plane="YZ")
    assert geo.volumen(s.cuerpo("Placa").forma) == pytest.approx(una - math.pi * 90)


def test_argumentos_incompatibles():
    s = _bloque()
    llamar(s, "create_component", bodies=["Bloque"], name="Taco")
    for nombre, args in (("mirror", {"bodies": "Bloque", "faces": ">Z"}),
                         ("mirror", {"faces": ">Z", "components": ["Taco"]}),
                         ("mirror", {"components": ["No existe"]}),
                         ("rectangular_pattern", {"faces": ">Z", "x_count": 2, "lightweight": True}),
                         ("mirror", {})):
        r = api.llamar(s, nombre, args)
        assert not r["ok"], (nombre, args)


def test_patron_de_geometria_de_construccion_copia_planos_ejes_y_puntos():
    s = _bloque()
    llamar(s, "create_construction_plane", plane="XY", offset=15, name="Alto")
    llamar(s, "create_construction_point", type="vertice", references=[[20, -10, 10]], name="Esquina")
    llamar(s, "rectangular_pattern", construction=["Alto", "Esquina"], x_count=3, x_spacing=50)
    estado = s.doc.estado_final
    copias_plano = [p for k, p in estado.planos.items() if "_k" in k]
    copias_punto = [p for k, p in estado.puntos.items() if "_k" in k]
    assert len(copias_plano) == 2 and len(copias_punto) == 2
    assert sorted(float(p.origen[0]) for p in copias_plano) == pytest.approx([50, 100])
    assert sorted(float(p[0][0]) for p in copias_punto) == pytest.approx([70, 120])
    assert all(float(p.origen[2]) == pytest.approx(15) for p in copias_plano)
    assert geo.volumen(s.cuerpo("Bloque").forma) == pytest.approx(4000)           # los cuerpos no cambian
    llamar(s, "undo")
    assert not [k for k in s.doc.estado_final.planos if "_k" in k]


def test_simetria_de_geometria_de_construccion():
    s = _bloque()
    llamar(s, "create_construction_point", type="vertice", references=[[20, -10, 10]], name="Esquina")
    llamar(s, "mirror", construction=["Esquina"], plane="YZ")
    (copia,) = [p for k, p in s.doc.estado_final.puntos.items() if "_k" in k]
    assert list(copia[0]) == pytest.approx([-20, -10, 10])
    r = api.llamar(s, "mirror", {"construction": ["Esquina"], "bodies": ["Bloque"], "plane": "YZ"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_calculo_ajustar_omite_las_copias_que_no_tocan_el_cuerpo():
    s = _bloque()
    llamar(s, "create_hole", face=">Z", diameter=4, depth=5, points=[[22, 0]])
    ids = {"features": [p["id"] for p in llamar(s, "get_timeline")["steps"] if p["type"] == "agujero"]}
    volumen_con_un_agujero = geo.volumen(list(s.doc.estado_final.cuerpos.values())[0].forma)
    r = api.llamar(s, "rectangular_pattern", {**ids, "x_count": 3, "x_spacing": 5, "compute": "adjust"})
    assert r["ok"] and not r["avisos"]                                            # las dos copias caen dentro del bloque
    llamar(s, "undo")
    r = api.llamar(s, "rectangular_pattern", {**ids, "x_count": 3, "x_spacing": 15, "compute": "adjust"})
    assert r["ok"] and any("no tocan al cuerpo" in a for a in r["avisos"])
    volumen_ajustado = geo.volumen(list(s.doc.estado_final.cuerpos.values())[0].forma)
    llamar(s, "undo")
    llamar(s, "rectangular_pattern", **ids, x_count=3, x_spacing=15, compute="identical")
    assert volumen_ajustado == pytest.approx(geo.volumen(list(s.doc.estado_final.cuerpos.values())[0].forma), rel=1e-9)
    assert volumen_ajustado < volumen_con_un_agujero                    # la copia que sí toca corta de más
    r2 = api.llamar(s, "rectangular_pattern", {"bodies": ["Bloque"], "x_count": 2, "compute": "adjust"})
    assert not r2["ok"] and "compute solo vale con features" in r2["mensaje"]


def test_las_copias_de_construccion_y_de_componentes_tienen_nombres_unicos():
    s = _bloque()
    llamar(s, "create_construction_plane", plane="XY", offset=15, name="Alto")
    llamar(s, "rectangular_pattern", construction=["Alto"], x_count=3, x_spacing=50)
    nombres = [p.nombre for p in s.doc.estado_final.planos.values()]
    assert len(nombres) == len(set(nombres)), nombres                    # «Alto (copia)» y «Alto (copia 2)»
    llamar(s, "mirror", construction=["Alto (copia)"], plane="XY")        # el nombre ya no es ambiguo


def test_calculo_ajustar_prolonga_un_corte_pasante_en_la_zona_mas_gruesa():
    """Un escalón: zona fina (z de 0 a 10) y zona gruesa (z de 0 a 25). El agujero «Todo» de la fina, copiado con Idéntico,
    queda corto en la gruesa; con Ajustar cada copia se recalcula y la atraviesa."""
    def montar(calculo):
        s = api.Sesion()
        llamar(s, "create_box", length=40, width=20, height=10, name="Base")
        llamar(s, "create_box", length=20, width=20, height=15, x=20, z=10, name="Cima")
        llamar(s, "boolean_operation", target="Base", tools=["Cima"], operation="join")
        llamar(s, "create_hole", face="nearest:[-10,0,10]", diameter=4, through_all=True, points=[[-10, 0]])
        pasos = [p["id"] for p in llamar(s, "get_timeline")["steps"] if p["type"] == "agujero"]
        llamar(s, "rectangular_pattern", features=pasos, x_count=2, x_spacing=25, compute=calculo)
        return list(s.doc.estado_final.cuerpos.values())[0].forma
    ident, ajust = montar("identical"), montar("adjust")
    hueco = math.pi * 2 ** 2
    assert geo.es_valida(ajust)
    assert geo.volumen(ident) - geo.volumen(ajust) == pytest.approx(hueco * 15, rel=1e-3)   # lo que falta de los 15 mm de la zona gruesa


def test_ajustar_no_alarga_copias_giradas_ni_herramientas_que_no_tocan():
    """Corte a lo largo de Y en un tubo, patrón circular de 4: las copias que quedan a lo largo de X no se estiran en Y."""
    def volumen(calculo):
        s = api.Sesion()
        llamar(s, "create_cylinder", radius=10, height=40, name="Tubo")
        llamar(s, "create_sketch", plane="XY", name="Corte")
        llamar(s, "draw_rectangle", x1=-2, y1=-15, x2=2, y2=15, sketch="Corte")
        llamar(s, "extrude", sketch="Corte", distance=4, operation="cut", target="Tubo")
        pasos = [p["id"] for p in llamar(s, "get_timeline")["steps"] if p["type"] == "extrusion"]
        llamar(s, "circular_pattern", features=pasos, count=4, axis="z", compute=calculo)
        return geo.volumen(s.cuerpo("Tubo").forma)
    assert volumen("adjust") == pytest.approx(volumen("identical"), rel=1e-9)
    from omnicad.timeline.ops_solido import _eje_pasante
    placa = geo.caja(40, 20, 10, (-20, -10, 0))

    class C:
        forma = placa
    assert _eje_pasante(geo.caja(4, 4, 10, (-2, -2, 20)), [C]) is None        # una herramienta lejos del cuerpo no es pasante
    assert _eje_pasante(geo.caja(4, 4, 30, (-2, -2, -10)), [C]) == 2
