# -*- coding: utf-8 -*-
import math

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import solidos_modificar as sm


# ---------------------------------------------------------------- ayudas
def cara_en(forma, punto, tol=1e-6):
    """Cara cuyo centroide de superficie está en `punto`."""
    for c in g.caras(forma):
        if np.allclose(g.centro_masa(c, superficie=True), punto, atol=tol):
            return c
    raise AssertionError(f"No hay cara con centro en {punto}")


def arista_en(forma, medio):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    for e in sm._aristas(forma):
        c = BRepAdaptor_Curve(e)
        p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
        if np.allclose((p.X(), p.Y(), p.Z()), medio, atol=1e-6):
            return e
    raise AssertionError(f"No hay arista con medio en {medio}")


def caja10():
    return g.caja(10, 10, 10)


def tapa(forma):
    return max(g.caras(forma), key=lambda c: g.centro_masa(c, True)[2])


def chequear(forma, volumen, rel=1e-6):
    assert g.es_valida(forma)
    assert g.volumen(forma) == pytest.approx(volumen, rel=rel)


# ---------------------------------------------------------------- empalme
def test_empalme_constante_y_cuerda():
    b = caja10()
    e = arista_en(b, (5, 0, 10))
    r = sm.empalme(b, [{"aristas": [e], "tipo": "constante", "radio": 2}])
    chequear(r, 1000 - (4 - math.pi) * 10)
    assert len(g.caras(r)) == 7
    # cuerda 2·√2 entre caras a 90° → radio 2
    r2 = sm.empalme(b, [{"aristas": [e], "tipo": "cuerda", "cuerda": 2 * math.sqrt(2)}])
    chequear(r2, 1000 - (4 - math.pi) * 10)


def test_empalme_variable_entre_extremos():
    b = caja10()
    e = arista_en(b, (5, 0, 10))
    r = sm.empalme(b, [{"aristas": [e], "tipo": "variable", "radios": [(0, 1), (1, 3)]}])
    assert g.es_valida(r)
    quitado = 1000 - g.volumen(r)
    # sección (1 − π/4)·r² con r lineal de 1 a 3 a lo largo de 10 mm: ∫ = (1 − π/4)·(27 − 1)/0,6
    assert quitado == pytest.approx((1 - math.pi / 4) * 26 / 0.6, rel=0.05)


def test_empalme_errores():
    b = caja10()
    with pytest.raises(g.ErrorGeometria):
        sm.empalme(b, [{"aristas": [arista_en(b, (5, 0, 10))], "radio": -1}])
    with pytest.raises(g.ErrorGeometria):
        sm.empalme(b, [{"aristas": [arista_en(b, (5, 0, 10))], "radio": 20}])
    with pytest.raises(g.ErrorGeometria):
        sm.empalme(b, [])


def test_cadena_tangente_y_caras_tangentes():
    c = caja10()
    b = sm.empalme(c, [{"aristas": [arista_en(c, (10, 0, 5))], "radio": 3}])
    frente = arista_en(b, (3.5, 0, 10))
    cadena = sm.aristas_cadena_tangente(b, frente)
    assert len(cadena) == 3              # arista frontal + arco del empalme + arista lateral
    r = sm.empalme(b, [{"aristas": [frente], "radio": 1}])
    assert g.es_valida(r) and g.volumen(r) < g.volumen(b)
    # cara frontal → empalme → cara lateral (la tapa no es tangente)
    assert len(sm.caras_tangentes(b, cara_en(b, (3.5, 0, 5)))) == 3


def test_empalme_reglas():
    b = caja10()
    # todas las aristas de la tapa, r = 1: franja de esquinas vivas en planta
    r = sm.empalme_reglas(b, [tapa(b)], radio=1)
    quitado = 40 * (1 - math.pi / 4) - 4 * (5 / 3 - math.pi / 2)
    chequear(r, 1000 - quitado, rel=1e-4)
    # entre tapa y frente: solo la arista común
    r2 = sm.empalme_reglas(b, [tapa(b)], [cara_en(b, (5, 0, 5))], radio=2, tipo="entre")
    chequear(r2, 1000 - (4 - math.pi) * 10)
    with pytest.raises(g.ErrorGeometria):    # una caja no tiene aristas cóncavas
        sm.empalme_reglas(b, [tapa(b)], radio=1, redondeos="empalmes")


# ---------------------------------------------------------------- chaflán
def test_chaflan_tipos():
    b = caja10()
    e = arista_en(b, (5, 0, 10))
    chequear(sm.chaflan(b, [{"aristas": [e], "tipo": "distancia_igual", "distancia": 1}]), 1000 - 5)
    # dos distancias: d1 = 1 sobre la tapa, d2 = 2 sobre el frente
    r = sm.chaflan(b, [{"aristas": [e], "tipo": "dos_distancias", "distancia": 1, "distancia2": 2,
                        "cara": tapa(b)}])
    chequear(r, 1000 - 0.5 * 1 * 2 * 10)
    assert g.area(tapa(r)) == pytest.approx(10 * 9)
    rv = sm.chaflan(b, [{"aristas": [e], "tipo": "dos_distancias", "distancia": 1, "distancia2": 2,
                         "cara": tapa(b), "voltear": True}])
    assert g.area(tapa(rv)) == pytest.approx(10 * 8)
    # cara automática: igual resultado de volumen
    chequear(sm.chaflan(b, [{"aristas": [e], "tipo": "dos_distancias", "distancia": 1, "distancia2": 2}]),
             1000 - 10)
    # distancia y ángulo: d sobre la cara, el otro cateto = d·tan(ángulo)
    ra = sm.chaflan(b, [{"aristas": [e], "tipo": "distancia_angulo", "distancia": 1, "angulo": 60,
                         "cara": tapa(b)}])
    chequear(ra, 1000 - 0.5 * 1 * math.tan(math.radians(60)) * 10)
    assert g.area(tapa(ra)) == pytest.approx(10 * 9)


# ---------------------------------------------------------------- vaciado
def test_vaciado_interior_exterior_ambos():
    b = g.caja(20, 20, 20)
    chequear(sm.vaciado(b, [tapa(b)], espesor_interior=2), 20 ** 3 - 16 * 16 * 18)
    ext = sm.vaciado(b, [tapa(b)], espesor_interior=0, espesor_exterior=2, direccion="exterior")
    chequear(ext, 24 * 24 * 22 - 20 ** 3)
    ambos = sm.vaciado(b, [tapa(b)], espesor_interior=1, espesor_exterior=1, direccion="ambos")
    chequear(ambos, 22 * 22 * 21 - 18 * 18 * 19)
    red = sm.vaciado(b, [tapa(b)], espesor_interior=2, tipo="redondeado")
    chequear(red, 20 ** 3 - 16 * 16 * 18)       # hacia adentro las esquinas quedan vivas igual


def test_vaciado_cerrado_y_tangente():
    b = g.caja(20, 20, 20)
    hueco = sm.vaciado(b, [], espesor_interior=2)
    chequear(hueco, 20 ** 3 - 16 ** 3)
    assert len(g.caras(hueco)) == 12               # cáscara exterior + cavidad interna
    # tapa con empalme en una arista: con cadena tangente se abre también el empalme y el frente
    e = sm.empalme(b, [{"aristas": [arista_en(b, (10, 0, 20))], "radio": 3}])
    assert len(sm.caras_tangentes(e, tapa(e))) == 3
    r = sm.vaciado(e, [tapa(e)], espesor_interior=1)
    assert g.es_valida(r) and g.volumen(r) < g.volumen(e) / 2


# ---------------------------------------------------------------- desmoldeo
def frustum(h, lado_base, ang):
    s = lado_base - 2 * h * math.tan(math.radians(ang))
    return h / 3 * (lado_base ** 2 + s * s + lado_base * s)


def test_desmoldeo_un_lado_y_simetrico():
    b = caja10()
    laterales = [c for c in g.caras(b) if 0.1 < g.centro_masa(c, True)[2] < 9.9]
    r = sm.desmoldeo(b, laterales, (0, 0, 1), 5, g.Plano("XY"))
    chequear(r, frustum(10, 10, 5))
    assert np.allclose(g.caja_envolvente(r), ((0, 0, 0), (10, 10, 10)), atol=1e-6)   # base fija en z = 0
    sim = sm.desmoldeo(b, laterales, (0, 0, 1), 5, g.Plano("XY", 5), lados="simetrico")
    chequear(sim, 2 * frustum(5, 10, 5))
    dos = sm.desmoldeo(b, laterales, (0, 0, 1), 5, g.Plano("XY", 5), lados="dos", angulo2=3)
    chequear(dos, frustum(5, 10, 5) + frustum(5, 10, 3))
    with pytest.raises(g.ErrorGeometria):
        sm.desmoldeo(g.esfera(5), g.caras(g.esfera(5)), (0, 0, 1), 5, g.Plano("XY"))


# ---------------------------------------------------------------- escala y transformaciones
def test_escalar():
    b = caja10()
    chequear(sm.escalar(b, (0, 0, 0), factor=2), 8000)
    r = sm.escalar(b, (10, 10, 10), factor=2)
    assert np.allclose(g.caja_envolvente(r), ((-10, -10, -10), (10, 10, 10)), atol=1e-6)
    nu = sm.escalar(b, (0, 0, 0), factores=(2, 3, 0.5))
    chequear(nu, 3000)
    assert np.allclose(g.caja_envolvente(nu)[1], (20, 30, 5), atol=1e-6)
    with pytest.raises(g.ErrorGeometria):
        sm.escalar(b, (0, 0, 0), factor=2, factores=(1, 1, 1))


def test_matrices_y_transformar():
    m = sm.matriz_rotacion((0, 0, 0), (0, 0, 1), 90)
    assert np.allclose(m[:3, :3] @ (1, 0, 0), (0, 1, 0))
    r = sm.transformar(caja10(), m)
    assert np.allclose(g.caja_envolvente(r), ((-10, 0, 0), (0, 10, 10)), atol=1e-6)
    t = sm.matriz_desde_puntos((1, 2, 3), (4, 6, 3))
    assert np.allclose(t[:3, 3], (3, 4, 0))
    r = sm.transformar(caja10(), t @ m)
    assert np.allclose(g.caja_envolvente(r), ((-7, 4, 0), (3, 14, 10)), atol=1e-6)
    assert np.allclose(sm.matriz_traslacion((1, 2, 3)) @ (0, 0, 0, 1), (1, 2, 3, 1))
    # rotación alrededor de un eje desplazado: el punto del eje queda fijo
    m2 = sm.matriz_rotacion((5, 5, 0), (0, 0, 1), 180)
    assert np.allclose(m2 @ (5, 5, 7, 1), (5, 5, 7, 1)) and np.allclose(m2 @ (0, 0, 0, 1), (10, 10, 0, 1))
    chequear(sm.transformar(caja10(), np.diag([2.0, 2.0, 2.0, 1.0])), 8000)
    espejo = sm.transformar(caja10(), np.diag([-1.0, 1.0, 1.0, 1.0]))
    chequear(espejo, 1000)
    assert np.allclose(g.caja_envolvente(espejo), ((-10, 0, 0), (0, 10, 10)), atol=1e-6)
    corte = np.eye(4)
    corte[0, 1] = 0.5                                # cizalla: va por gp_GTrsf, conserva el volumen
    chequear(sm.transformar(caja10(), corte), 1000)


def test_alinear():
    # plano z=0 (normal +z) sobre el plano x=20 (normal +x): enfrentados → la normal pasa a −x
    o = {"tipo": "plano", "origen": (0, 0, 0), "normal": (0, 0, 1)}
    d = {"tipo": "plano", "origen": (20, 0, 0), "normal": (1, 0, 0)}
    forma, m = sm.alinear(caja10(), o, d)
    assert np.allclose(m[:3, :3] @ (0, 0, 1), (-1, 0, 0)) and np.allclose(m @ (0, 0, 0, 1), (20, 0, 0, 1))
    assert g.caja_envolvente(forma)[1][0] == pytest.approx(20)
    _, mv = sm.alinear(None, o, d, voltear=True)
    assert np.allclose(mv[:3, :3] @ (0, 0, 1), (1, 0, 0))
    # eje sobre eje
    _, me = sm.alinear(None, {"tipo": "eje", "punto": (1, 1, 1), "direccion": (1, 0, 0)},
                       {"tipo": "eje", "punto": (0, 0, 5), "direccion": (0, 1, 0)})
    assert np.allclose(me[:3, :3] @ (1, 0, 0), (0, 1, 0)) and np.allclose(me @ (1, 1, 1, 1), (0, 0, 5, 1))
    # punto sobre punto
    _, mp = sm.alinear(None, {"tipo": "punto", "punto": (1, 2, 3)}, {"tipo": "punto", "punto": (0, 0, 0)})
    assert np.allclose(mp, sm.matriz_traslacion((-1, -2, -3)))
    # plano antiparalelo ya enfrentado: solo traslada
    _, ma = sm.alinear(None, o, {"tipo": "plano", "plano": g.Plano.desde_marco((0, 0, 9), (0, 0, -1), (1, 0, 0))})
    assert np.allclose(ma, sm.matriz_traslacion((0, 0, 9)))


# ---------------------------------------------------------------- desfase y reemplazo de caras
def test_desfasar_caras_plana_y_cilindrica():
    b = caja10()
    r = sm.desfasar_caras(b, [tapa(b)], 5)
    chequear(r, 1000 + 100 * 5)
    assert len(g.caras(r)) == 6
    chequear(sm.desfasar_caras(b, [tapa(b)], -2), 800)
    agujereada = g.booleano(g.caja(20, 20, 10), g.cilindro(3, 10, (10, 10, 0)), "cortar")
    cil = [c for c in g.caras(agujereada) if g.area(c) == pytest.approx(60 * math.pi)]
    r = sm.desfasar_caras(agujereada, cil, 1)       # hacia afuera del material: el agujero se achica
    chequear(r, g.volumen(agujereada) + math.pi * (9 - 4) * 10)


def test_desfasar_caras_alternativa_por_extrusion(monkeypatch):
    class Falla:
        def __init__(self, *a):
            raise RuntimeError("kernel")
    monkeypatch.setattr(sm, "BRepOffset_MakeOffset", Falla)
    b = caja10()
    r = sm.desfasar_caras(b, [tapa(b)], 5)
    chequear(r, 1500)
    assert len(g.caras(r)) == 6
    chequear(sm.desfasar_caras(b, [tapa(b), cara_en(b, (5, 0, 5))], -1), 9 * 9 * 10)


def test_reemplazar_cara_planos_y_curva():
    b = caja10()
    r = sm.reemplazar_cara(b, [tapa(b)], g.Plano("XY", 15))
    chequear(r, 1500)
    assert len(g.caras(r)) == 6
    chequear(sm.reemplazar_cara(b, [tapa(b)], g.Plano("XY", 7)), 700)
    # plano inclinado z = 10 + 0,2·x  → volumen 10·∫(10 + 0,2x)dx = 1100
    n = np.array([-0.2, 0, 1.0])
    chequear(sm.reemplazar_cara(b, [tapa(b)], g.Plano.desde_marco((0, 0, 10), n, (1, 0, 0))), 1100)
    # destino = cara de un cilindro R = 20 de eje Y a la altura z = −5 (techo abovedado, sobre el frente)
    cil = g.cilindro(20, 30, (5, -10, -5), (0, 1, 0))
    curva = max(g.caras(cil), key=g.area)
    r = sm.reemplazar_cara(b, [tapa(b)], curva)
    xs = np.linspace(0, 10, 2001)
    esperado = 10 * np.trapezoid(np.sqrt(400 - (xs - 5) ** 2) - 5, xs)
    chequear(r, esperado, rel=1e-5)


def test_mover_caras():
    b = caja10()
    chequear(sm.mover_caras(b, [tapa(b)], sm.matriz_traslacion((0, 0, 3))), 1300)
    # girar la tapa sobre su línea media: de un lado extiende y del otro recorta (z = 10 + 0,2·(x − 5))
    giro = sm.matriz_rotacion((5, 5, 10), (0, -1, 0), math.degrees(math.atan(0.2)))
    r = sm.mover_caras(b, [tapa(b)], giro)
    chequear(r, 1000)
    assert len(g.caras(r)) == 6 and g.caja_envolvente(r)[1][2] == pytest.approx(11)
    assert g.centro_masa(r)[0] > 5
    # saliente 4x4x4 sobre la tapa movido 2 mm en +x
    s = g.booleano(b, g.caja(4, 4, 4, (3, 3, 10)), "unir")
    caras = [c for c in g.caras(s) if g.centro_masa(c, True)[2] > 10 + 1e-6]
    r = sm.mover_caras(s, caras, sm.matriz_traslacion((2, 0, 0)))
    chequear(r, 1000 + 64)
    assert np.allclose(g.caja_envolvente(r)[1], (10, 10, 14), atol=1e-6)
    assert g.centro_masa(r)[0] == pytest.approx((1000 * 5 + 64 * 7) / 1064)
    with pytest.raises(g.ErrorGeometria):
        sm.mover_caras(g.cilindro(5, 10), [max(g.caras(g.cilindro(5, 10)), key=g.area)],
                       sm.matriz_traslacion((1, 0, 0)))


# ---------------------------------------------------------------- división
def test_dividir_cara():
    b = caja10()
    r = sm.dividir_cara(b, [tapa(b)], g.Plano("YZ", 5))
    chequear(r, 1000)
    assert len(g.caras(r)) == 7                  # solo la tapa se parte (el plano también corta la base)
    assert sorted(round(g.area(c), 6) for c in g.caras(r))[:2] == [50, 50]
    # herramienta = cara chica que no atraviesa, sin extender → error; extendida → parte
    chica = g.caras(g.caja(2, 2, 2, (4, 4, 9)))
    lateral = [c for c in chica if abs(g.centro_masa(c, True)[0] - 4) < 1e-9][0]
    with pytest.raises(g.ErrorGeometria):
        sm.dividir_cara(b, [tapa(b)], lateral, extender=False)
    assert len(g.caras(sm.dividir_cara(b, [tapa(b)], lateral))) == 7


def test_dividir_cuerpo():
    b = caja10()
    piezas = sm.dividir_cuerpo(b, g.Plano("YZ", 5))
    assert [round(g.volumen(p), 6) for p in piezas] == [500, 500]
    assert g.centro_masa(piezas[0])[0] < g.centro_masa(piezas[1])[0]
    assert all(g.es_valida(p) for p in piezas)
    # herramienta = cuerpo: cilindro que atraviesa la caja
    piezas = sm.dividir_cuerpo(b, g.cilindro(2, 20, (5, 5, -5)))
    assert sorted(round(g.volumen(p), 4) for p in piezas) == sorted([round(math.pi * 40, 4),
                                                                    round(1000 - math.pi * 40, 4)])
    with pytest.raises(g.ErrorGeometria):
        sm.dividir_cuerpo(b, g.Plano("YZ", 50))


def test_division_silueta():
    cil = g.cilindro(5, 10)
    r = sm.division_silueta(cil, (1, 0, 0))
    assert len(g.caras(r)) == 4 and g.es_valida(r)
    assert g.volumen(r) == pytest.approx(g.volumen(cil))
    laterales = [g.area(c) for c in g.caras(r) if g.area(c) > 100]
    assert laterales == pytest.approx([50 * math.pi] * 2)
    esf = sm.division_silueta(g.esfera(5), (0, 0, 1))
    assert sorted(round(g.area(c), 6) for c in g.caras(esf)) == [round(50 * math.pi, 6)] * 2
    tor = g.toroide(10, 2)
    r = sm.division_silueta(tor, (0, 0, 1))
    assert len(g.caras(r)) == 2 and g.area(r) == pytest.approx(g.area(tor))
    r = sm.division_silueta(tor, (1, 0, 0))     # perpendicular: meridianos + círculos de arriba/abajo
    assert len(g.caras(r)) >= 4 and g.es_valida(r)    # la costura doble del toro puede dejar piezas extra
    assert g.area(r) == pytest.approx(g.area(tor))
    for c in g.caras(r):                            # ninguna cara cruza la silueta
        assert abs(sm._punto_normal(c)[1] @ (1, 0, 0)) > 1e-3
    with pytest.raises(g.ErrorGeometria):
        sm.division_silueta(caja10(), (0, 0, 1))


def test_division_silueta_numerica_toroide_oblicuo():
    tor = g.toroide(10, 2)
    r = sm.division_silueta(tor, (1, 0, 1))
    assert g.es_valida(r) and len(g.caras(r)) > 1
    assert g.area(r) == pytest.approx(g.area(tor), rel=1e-6)
    # en cada cara nueva la normal no cambia de lado respecto de la vista (salvo en el borde)
    d = np.array([1.0, 0, 1.0]) / math.sqrt(2)
    for c in g.caras(r):
        _, n = sm._punto_normal(c)
        assert abs(n @ d) > 1e-3


# ---------------------------------------------------------------- quitar caras
def test_quitar_caras_agujero():
    agujereada = g.booleano(g.caja(20, 20, 10), g.cilindro(3, 10, (10, 10, 0)), "cortar")
    cil = [c for c in g.caras(agujereada) if g.area(c) == pytest.approx(60 * math.pi)]
    r = sm.quitar_caras(agujereada, cil)
    chequear(r, 4000)
    assert len(g.caras(r)) == 6
    # quitar un empalme devuelve la arista viva
    c = caja10()
    e = sm.empalme(c, [{"aristas": [arista_en(c, (5, 0, 10))], "radio": 2}])
    curva = [c for c in g.caras(e) if g.area(c) == pytest.approx(math.pi * 10)]
    chequear(sm.quitar_caras(e, curva), 1000)
