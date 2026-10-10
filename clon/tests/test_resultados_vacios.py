# -*- coding: utf-8 -*-
"""Pasos que daban «ok» con un resultado vacío, inválido o sin cambios (hallazgos L190, L201, L216, L217 y L225
de las pruebas de uso). Ahora fallan con un error claro y el documento queda intacto, o avisan."""
import json
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import solidos_modificar as sm


@pytest.fixture
def s():
    return api.Sesion()


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(sesion, nombre, **args):
    return ok(api.llamar(sesion, nombre, args))


def foto(sesion):
    doc = sesion.doc
    return (json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados],
            len(doc._deshacer), len(doc._rehacer), doc.modificado)


def falla(sesion, nombre, texto, **args):
    """La herramienta falla con OPERATION_FAILED, el mensaje dice `texto` y el documento no cambia."""
    antes = foto(sesion)
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED", r
    assert texto in r["mensaje"], r["mensaje"]
    assert foto(sesion) == antes
    return r


def boceto(sesion, nombre, plano, *entidades):
    llamar(sesion, "sketch_from_spec", name=nombre, plane=plano, entities=list(entidades))


def circulo(x, y, r):
    return {"type": "circle", "center": [x, y], "radius": r}


def cuerpo(sesion, cid):
    return sesion.doc.estado_final.cuerpos[cid]


# ---------------------------------------------------------------- L216: solevación, barrido y escala sin volumen
@pytest.mark.parametrize("desfase", [0, 7])
def test_solevacion_entre_perfiles_coplanares_falla(s, desfase):
    plano = "XY"
    if desfase:
        plano = "Alto"
        llamar(s, "create_construction_plane", plane="XY", offset=desfase, name=plano)
    boceto(s, "A", plano, {"type": "rectangle", "center": [0, 0], "width": 10, "height": 10})
    boceto(s, "B", plano, circulo(20, 0, 4))
    falla(s, "loft", "no encierra volumen", sketches=["A", "B"])


def test_solevacion_cerrada_que_vuelve_sobre_si_misma_falla(s):
    for i, z in enumerate((0, 10, 20)):
        plano = "XY"
        if z:
            plano = f"Z{z}"
            llamar(s, "create_construction_plane", plane="XY", offset=z, name=plano)
        boceto(s, f"C{i}", plano, circulo(10 * (i % 2), 0, 5))
    falla(s, "loft", "no encierra volumen", sketches=["C0", "C1", "C2"], closed=True)


def test_solevacion_legitima_sigue_andando(s):
    llamar(s, "create_construction_plane", plane="XY", offset=20, name="Alto")
    boceto(s, "Base", "XY", {"type": "rectangle", "center": [0, 0], "width": 10, "height": 10})
    boceto(s, "Tope", "Alto", {"type": "rectangle", "center": [0, 0], "width": 4, "height": 4})
    r = api.llamar(s, "loft", {"sketches": ["Base", "Tope"]})
    tronco = ok(r)["bodies_created"][0]
    assert tronco["volume"] == pytest.approx(20 / 3 * (100 + 16 + math.sqrt(1600)), rel=1e-4) and not r["avisos"]
    assert geo.es_valida(cuerpo(s, tronco["id"]).forma)


def test_barrido_con_el_perfil_paralelo_a_la_ruta_falla(s):
    boceto(s, "Perfil", "XZ", circulo(0, 0, 3))
    boceto(s, "Ruta", "XZ", {"type": "line", "start": [10, 0], "end": [10, 40]})
    falla(s, "sweep", "no encierra volumen", sketch="Perfil", profile=0, path_sketch="Ruta")
    boceto(s, "Perfil2", "XY", circulo(0, 0, 3))
    boceto(s, "Recta", "XZ", {"type": "line", "start": [0, 0], "end": [0, 30]})
    r = llamar(s, "sweep", sketch="Perfil2", profile=0, path_sketch="Recta")
    assert r["bodies_created"][0]["volume"] == pytest.approx(math.pi * 9 * 30, rel=1e-4)


@pytest.mark.parametrize("params", [{"factor": "1e-7"}, {"tipo": "no_uniforme", "fx": "1", "fy": "1", "fz": "1e-7"}])
def test_escala_casi_nula_falla(s, params):
    llamar(s, "create_box", length=20, width=20, height=20)
    falla(s, "run_operation", "queda sin volumen", type="escala", params=dict(params, cuerpos=["op1.c1"]))


def test_escala_chica_legitima_sigue_andando(s):
    llamar(s, "create_box", length=20, width=20, height=20)
    r = llamar(s, "run_operation", type="escala", params={"cuerpos": ["op1.c1"], "factor": "0.001"})
    assert r["status"] == "ok"
    forma = cuerpo(s, "op1.c1").forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(8000 * 1e-9, rel=1e-6)


@pytest.mark.parametrize("nombre, args", [
    ("create_cylinder", {"radius": 1e9, "height": 10}),
    ("create_cylinder", {"radius": 1e-7, "height": 10}),
    ("create_sphere", {"radius": 1e9}),
    ("create_torus", {"major_radius": 1e9, "minor_radius": 5}),
])
def test_primitivas_con_medidas_extremas_fallan(s, nombre, args):
    falla(s, nombre, "demasiado", **args)


def test_primitivas_nucleo_validas():
    for forma, v in ((geo.cilindro(3, 30), math.pi * 9 * 30), (geo.esfera(5), 4 / 3 * math.pi * 125),
                     (geo.toroide(20, 5), 2 * math.pi ** 2 * 20 * 25), (geo.caja(1e9, 1, 1), 1e9)):
        assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(v, rel=1e-6)
    for construir in (lambda: geo.cilindro(1e9, 10), lambda: geo.esfera(1e-7), lambda: geo.caja(1e-8, 1, 1)):
        with pytest.raises(geo.ErrorGeometria, match="demasiado"):
            construir()


def test_sin_volumen():
    assert geo.sin_volumen(geo.caja(1e-4, 1e-4, 1e-4))                    # más chica que TAMANO_MINIMO
    assert not geo.sin_volumen(geo.caja(0.002, 0.002, 0.002))
    assert not geo.sin_volumen(geo.caja(100, 100, 0.01))                 # lámina fina, pero con volumen
    assert not geo.sin_volumen(geo.cilindro(0.25, 1000))                 # alambre


# ---------------------------------------------------------------- L217: revolución que cruza el eje
def test_revolucion_con_el_perfil_cruzando_el_eje_falla(s):
    boceto(s, "Cruza", "XZ", {"type": "rectangle", "center": [0, 10], "width": 10, "height": 10})
    falla(s, "revolve", "cruza el eje", sketch="Cruza", profile=0, axis="sketch_y")
    falla(s, "revolve", "cruza el eje", sketch="Cruza", profile=0, axis="sketch_y", angle=90)
    boceto(s, "SobreX", "XY", {"type": "rectangle", "center": [40, 0], "width": 10, "height": 10})
    falla(s, "revolve", "cruza el eje", sketch="SobreX", profile=0, axis="x")


def test_revolucion_con_el_eje_perpendicular_al_perfil_falla(s):
    boceto(s, "Plano", "XY", circulo(20, 0, 5))
    falla(s, "revolve", "no genera un sólido", sketch="Plano", profile=0, axis="z")


def test_revolucion_apoyada_en_el_eje_sigue_andando(s):
    boceto(s, "Apoyado", "XZ", {"type": "rectangle", "origin": [0, 0], "width": 5, "height": 10})
    r = llamar(s, "revolve", sketch="Apoyado", profile=0, axis="sketch_y")["bodies_created"][0]
    assert r["volume"] == pytest.approx(math.pi * 25 * 10, rel=1e-6)
    assert geo.es_valida(cuerpo(s, r["id"]).forma)


# ---------------------------------------------------------------- L201: vaciado que no cambia nada
def _prisma_con_arcos():
    """Caja con cuatro cortes cilíndricos que cruzan la cara de abajo (MakeThickSolid da IsDone y no vacía)."""
    forma = geo.caja(456, 176, 155.8, (0, -88, 38))
    for x in (82.1, 367.1):
        for y0 in (-90, 54):
            forma = geo.booleano(forma, geo.cilindro(48, 36, (x, y0, 40), (0, 1, 0)), "cortar")
    return forma


def test_vaciado_que_no_quita_la_cara_falla():
    forma = _prisma_con_arcos()
    abajo = min((c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is not None and p.normal[2] < -0.99),
                key=lambda c: geo.centro_masa(c, True)[2])
    for direccion in ("interior", "exterior"):
        with pytest.raises(geo.ErrorGeometria, match="El vaciado falló"):
            sm.vaciado(forma, [abajo], espesor_interior=5, espesor_exterior=5, direccion=direccion)


def _tapa(forma):
    return max(geo.caras(forma), key=lambda c: geo.centro_masa(c, True)[2])


@pytest.mark.parametrize("medidas, espesor, volumen", [
    ((20, 20, 10), 1, 4000 - 18 * 18 * 9),
    ((20, 20, 10), 4.9, 4000 - 10.2 * 10.2 * 5.1),          # pared gruesa: el vaciado quita poco volumen
    ((100, 100, 1.5), 1, 15000 - 98 * 98 * 0.5),            # lámina: el fondo queda a 0,5 mm de la abertura
])
def test_vaciado_legitimo_sigue_andando(medidas, espesor, volumen):
    caja = geo.caja(*medidas)
    r = sm.vaciado(caja, [_tapa(caja)], espesor_interior=espesor)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(volumen, rel=1e-6)


def test_vaciado_de_un_tronco_de_cono_chato_sigue_andando():
    """Paredes a 27° de la tapa: el canto interior entra 2,2 espesores; el control de la cara no lo confunde."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    tronco = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 40, 20, 10).Shape()
    v0 = math.pi * 10 / 3 * (40 ** 2 + 40 * 20 + 20 ** 2)
    r = sm.vaciado(tronco, [_tapa(tronco)], espesor_interior=4)
    assert geo.es_valida(r) and 0.5 * v0 < geo.volumen(r) < 0.95 * v0


class _VaciadoFalso:
    """MakeThickSolid que da IsDone y devuelve el cuerpo apenas tocado, con la cara quitada todavía puesta: lo que
    hacía el kernel con el modelo de la prueba (vaciado de 40 mm: −0,007 % de volumen y la cara de abajo intacta)."""

    def MakeThickSolidByJoin(self, forma, *args):
        self.entrada = forma

    def Build(self):
        pass

    def IsDone(self):
        return True

    def Shape(self):
        return geo.booleano(self.entrada, geo.caja(2, 2, 2, (2, 2, -1)), "cortar")    # mella abajo; la tapa sigue


class _VaciadoQueRevienta(_VaciadoFalso):
    def MakeThickSolidByJoin(self, forma, *args):
        raise RuntimeError("BRep_Tool:: no parameter on edge")      # Standard_NoSuchObject de OCC


def test_vaciado_que_deja_la_cara_puesta_falla(monkeypatch):
    caja = geo.caja(20, 20, 10)
    monkeypatch.setattr(sm, "BRepOffsetAPI_MakeThickSolid", _VaciadoFalso)
    with pytest.raises(geo.ErrorGeometria, match="El vaciado falló: el kernel no pudo quitar esas caras"):
        sm.vaciado(caja, [_tapa(caja)], espesor_interior=2)
    monkeypatch.setattr(sm, "BRepOffsetAPI_MakeThickSolid", _VaciadoQueRevienta)
    with pytest.raises(geo.ErrorGeometria, match="El vaciado falló: el kernel no pudo con ese espesor"):
        sm.vaciado(caja, [_tapa(caja)], espesor_interior=2)


# ---------------------------------------------------------------- L190: borrar caras que no se pueden curar
def test_borrar_la_tapa_de_una_caja_falla():
    caja = geo.caja(20, 20, 20)
    tapa = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[2])
    with pytest.raises(geo.ErrorGeometria, match="No se pueden borrar esas caras"):
        sm.quitar_caras(caja, [tapa])
    agujereada = geo.booleano(caja, geo.cilindro(3, 20, (10, 10, 0)), "cortar")
    cil = [c for c in geo.caras(agujereada) if geo.plano_de_cara(c) is None]
    with pytest.raises(geo.ErrorGeometria, match="No se pueden borrar esas caras"):
        sm.quitar_caras(agujereada, cil + [max(geo.caras(agujereada), key=lambda c: geo.centro_masa(c, True)[2])])
    r = sm.quitar_caras(agujereada, cil)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(8000, rel=1e-6)


def test_borrar_caras_en_el_timeline_falla_y_no_cambia_el_documento(s):
    llamar(s, "create_box", length=20, width=20, height=20)
    forma = cuerpo(s, "op1.c1").forma
    tapa = max(geo.caras(forma), key=lambda c: geo.centro_masa(c, True)[2])
    falla(s, "run_operation", "No se pueden borrar esas caras", type="borrar_caras",
          params={"caras": [refs.referencia("op1.c1", tapa, forma)]})


# ---------------------------------------------------------------- L225: booleanas entre cuerpos que no se tocan
def _dos_cajas(s, x=50):
    a = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=10, width=10, height=10, x=x)["bodies_created"][0]["id"]
    return a, b


def test_unir_cuerpos_que_no_se_tocan_deja_un_cuerpo_de_dos_piezas(s):
    """Como Combinar › Unir de Fusion («combina los sólidos en un solo cuerpo»): no es un error ni avisa (el modelo
    de ejemplo une el aro y el toroide, que no se tocan)."""
    a, b = _dos_cajas(s)
    assert llamar(s, "boolean_operation", target=a, tools=[b], operation="join")["bodies_removed"] == [b]
    forma = cuerpo(s, a).forma
    assert len(geo.solidos(forma)) == 2 and geo.volumen(forma) == pytest.approx(2000) and geo.es_valida(forma)


def test_cortar_con_una_herramienta_que_no_toca_avisa(s):
    a, b = _dos_cajas(s)
    r = api.llamar(s, "boolean_operation", {"target": a, "tools": [b], "operation": "cut"})
    assert r["ok"] and any("no toca" in x and "no le cortó nada" in x for x in r["avisos"])
    assert geo.volumen(cuerpo(s, a).forma) == pytest.approx(1000)


def _caja_ya_cortada(s):
    """Caja de 40 con una mella: después de una booleana el cuerpo es un COMPOUND (63 968 mm³)."""
    a = llamar(s, "create_box", length=40, width=40, height=40)["bodies_created"][0]["id"]
    llamar(s, "create_box", length=4, width=4, height=4, x=20, operation="cut", target=a)
    assert cuerpo(s, a).forma.ShapeType().name == "TopAbs_COMPOUND"
    return a


ESFERA_5 = 4 / 3 * math.pi * 125


def test_se_tocan_ve_lo_que_queda_adentro_de_un_compound():
    caja = geo.caja(40, 40, 40)
    mellada = geo.booleano(caja, geo.caja(4, 4, 4, (38, 0, 0)), "cortar")
    adentro = geo.esfera(5, (20, 20, 20))
    assert geo.se_tocan(caja, adentro) and geo.se_tocan(mellada, adentro) and geo.se_tocan(adentro, mellada)
    assert not geo.se_tocan(mellada, geo.esfera(5, (100, 0, 0)))
    hueca = geo.booleano(caja, geo.caja(30, 30, 30, (5, 5, 5)), "cortar")      # la cavidad es aire: no toca
    assert not geo.se_tocan(hueca, geo.esfera(3, (20, 20, 20))) and geo.se_tocan(hueca, geo.esfera(1, (2, 20, 20)))


def test_cortar_una_cavidad_interna_no_avisa(s):
    a = _caja_ya_cortada(s)
    b = llamar(s, "create_sphere", radius=5, z=20)["bodies_created"][0]["id"]
    r = api.llamar(s, "boolean_operation", {"target": a, "tools": [b], "operation": "cut"})
    assert ok(r) and not r["avisos"] and s.doc.resultados[-1].estado == "ok"
    assert geo.volumen(cuerpo(s, a).forma) == pytest.approx(63968 - ESFERA_5)


@pytest.mark.parametrize("con_objetivo", [False, True])
def test_primitiva_que_corta_una_cavidad_interna(s, con_objetivo):
    """Con objetivo automático el corte se salteaba (se_tocan daba False con un COMPOUND) y no cambiaba nada."""
    a = _caja_ya_cortada(s)
    args = {"radius": 5, "z": 20, "operation": "cut", **({"target": a} if con_objetivo else {})}
    r = api.llamar(s, "create_sphere", args)
    assert ok(r) and not r["avisos"]
    assert geo.volumen(cuerpo(s, a).forma) == pytest.approx(63968 - ESFERA_5)


def test_booleanas_que_se_tocan_no_avisan(s):
    a, b = _dos_cajas(s, x=5)
    r = api.llamar(s, "boolean_operation", {"target": a, "tools": [b], "operation": "join"})
    assert ok(r)["bodies_modified"][0]["volume"] == pytest.approx(1500) and not r["avisos"]


def test_primitiva_con_objetivo_que_no_toca_avisa(s):
    a = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    r = api.llamar(s, "create_box", {"length": 4, "width": 4, "height": 4, "x": 50, "operation": "cut", "target": a})
    assert r["ok"] and any("no toca a Cuerpo1: no le cortó nada" in x for x in r["avisos"])
    assert geo.volumen(cuerpo(s, a).forma) == pytest.approx(1000)
    r = api.llamar(s, "create_box", {"length": 4, "width": 4, "height": 4, "x": 4, "operation": "cut", "target": a})
    assert r["ok"] and not any("no toca" in x for x in r["avisos"])        # la caja va de x 2 a 6: corta 3 × 4 × 4
    assert geo.volumen(cuerpo(s, a).forma) == pytest.approx(1000 - 3 * 4 * 4)
