# -*- coding: utf-8 -*-
"""Test para B-71: uniones encadenadas y lazos cerrados (biela-manivela).
Reproduce el bug: al accionar una unión, el componente atado a OTRA unión que
depende de la movida no la sigue, y un mecanismo con lazo cerrado no se resuelve.
"""
import math
import pytest
import numpy as np

from omnicad import api
from omnicad.nucleo import geometria as g


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def caja(s, cid):
    return [round(v, 4) + 0.0 for p in g.caja_envolvente(s.cuerpo(cid).forma) for v in p]


def centro_caja(caja):
    """Centro de una caja envolvente [xmin, ymin, zmin, xmax, ymax, zmax]."""
    return [(caja[0] + caja[3]) / 2, (caja[1] + caja[4]) / 2, (caja[2] + caja[5]) / 2]


# =================================================================== CADENA ABIERTA
def test_b71_cadena_abierta():
    """A fija (ground), B unida a A con revolute, C unida a B con revolute en un
    punto de B fuera del eje. drive_joint de A-B a 90°: C se mueve con B.
    """
    s = api.Sesion()

    # A: base fija 40x40x10 en el origen
    base = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="A", grounded=True)

    # B: brazo 20x10x10, pivote en su extremo en (0,0,10) sobre A
    #    B se modela con su pivote en el origen local, luego se une
    brazo_b = llamar(s, "create_box", length=20, width=10, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[brazo_b], name="B")

    # C: brazo 15x10x10, unido al extremo libre de B (en x=20 de B)
    brazo_c = llamar(s, "create_box", length=15, width=10, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[brazo_c], name="C")

    # Unión A-B: revolute en la cara superior de A (z=10) y cara inferior de B (z=0)
    # B gira alrededor del eje Z que pasa por (0,0,10) en coordenadas globales
    llamar(s, "create_joint",
           origin1="<Z", body1=brazo_b,
           origin2=">Z", body2=base,
           joint_type="revolute", rotation=0, name="J1_AB")

    # Unión B-C: revolute en el extremo libre de B (cara >X, x=+10 local de B)
    # y cara <X de C (x=-7.5 local de C). Las caras se enfrentan (normales opuestas).
    llamar(s, "create_joint",
           origin1="<X", body1=brazo_c,
           origin2=">X", body2=brazo_b,
           joint_type="revolute", rotation=0, name="J2_BC")

    # Estado inicial: C está en el extremo derecho de B (que está en reposo horizontal)
    # B centro en (0,0,10), cara >X en x=10. C centro en (17.5, 0, 10), cara <X en x=10.
    # C x-range: [10, 25]
    c_inicial = caja(s, brazo_c)
    assert c_inicial[0] > 5  # C está a la derecha de A (x > 5)

    # Accionar J1 a 90°: B gira 90° alrededor de Z en (0,0,10)
    # B debería ir de horizontal a vertical (hacia +Y)
    # C debería seguir a B, rotando alrededor del punto de unión en el extremo de B
    llamar(s, "drive_joint", joint="J1_AB", rotation=90)

    # Verificar que C se movió con B
    c_despues = caja(s, brazo_c)
    _ = centro_caja(c_despues)

    # El punto de unión entre B y C (extremo de B) debería estar en aprox (0, 20, 10) a (0, 20, 20)
    # C debería estar rotado alrededor de ese punto
    # Lo importante: C NO debería estar donde estaba antes (cadena rota)
    assert c_despues != c_inicial, "C no se movió: la cadena está rota"

    # Verificar que la unión J2 sigue válida (no REFERENCE_LOST) y que C se movió con B
    ensamblaje = llamar(s, "get_assembly")
    j2 = next(j for j in ensamblaje["joints"] if j["name"] == "J2_BC")
    assert j2["status"] == "ok", f"J2 status: {j2['status']}, msg: {j2.get('message')}"

    # Verificar que C rotó con B: la traslación de C cambió coherentemente
    comp_c = next(c for c in ensamblaje["components"] if c["name"] == "C")
    # C debería haber rotado 90° alrededor del eje de J1 (Z en (0,0,10))
    # Su posición inicial era aprox (17.5, 0, 15), final aprox (0, 17.5, 15) en el centro
    t_c = np.array(comp_c["translation"])
    assert abs(t_c[0]) < 1.0 and abs(t_c[1] - 17.5) < 1.0, f"C no siguió a B: trans={t_c}"


# =================================================================== BIELA-MANIVELA (LAZO CERRADO)
@pytest.mark.xfail(strict=True, reason="B-71 sigue abierto: el lazo cerrado (biela-manivela) no se resuelve; las uniones se aplican de a una y la última pisa a la corredera")
def test_b71_biela_manivela():
    """Lazo cerrado: bastidor fijo; manivela r=20 revolute al bastidor; biela l=60
    revolute a la manivela; corredera con revolute a la biela y slider al bastidor
    sobre eje X que pasa por el eje de la manivela.

    Accionar manivela a θ = 0, 30, 90, 135°:
    - Corredera queda en x = r·cosθ + sqrt(l² − (r·sinθ)²) (±1e-3 mm)
    - Extremos de la biela coinciden con sus pernos (±1e-3 mm)
    """
    r = 20.0  # radio de manivela (distancia del centro al perno)
    l = 60.0  # largo de biela (distancia entre pernos)

    def posicion_corredera_esperada(theta_deg):
        """x = r*cosθ + sqrt(l² - (r*sinθ)²)"""
        th = math.radians(theta_deg)
        return r * math.cos(th) + math.sqrt(l**2 - (r * math.sin(th))**2)

    for theta in [0, 30, 90, 135]:
        s = api.Sesion()

        # Bastidor fijo: caja 100x50x10 en origen
        bastidor = llamar(s, "create_box", length=100, width=50, height=10)["bodies_created"][0]["id"]
        llamar(s, "create_component", bodies=[bastidor], name="Bastidor", grounded=True)

        # Manivela: caja 40x10x10, modelada horizontal en X, con perno en x=20 (radio r=20)
        # El centro de la manivela está en el origen, el perno en x=20
        manivela = llamar(s, "create_box", length=40, width=10, height=10)["bodies_created"][0]["id"]
        llamar(s, "create_component", bodies=[manivela], name="Manivela")

        # Biela: caja 60x10x10, modelada horizontal en X, pernos en extremos (x=-30 y x=30)
        biela = llamar(s, "create_box", length=60, width=10, height=10)["bodies_created"][0]["id"]
        llamar(s, "create_component", bodies=[biela], name="Biela")

        # Corredera: caja 20x20x10
        corredera = llamar(s, "create_box", length=20, width=20, height=10)["bodies_created"][0]["id"]
        llamar(s, "create_component", bodies=[corredera], name="Corredera")

        # J1: Manivela → Bastidor (revolute en Z en el origen)
        # Cara >Z de manivela (z=5) contra cara >Z de bastidor (z=10)
        # Manivela modelada en X, pero J1 usa >Z para girar en Z
        llamar(s, "create_joint",
               origin1=">Z", body1=manivela,
               origin2=">Z", body2=bastidor,
               joint_type="revolute", rotation=0, name="J1_manivela")

        # J2: Biela → Manivela (revolute en el perno de la manivela en x=20)
        # Biela cara <X (x=-30) contra origen de unión en manivela en x=20
        # Crear origen de unión en manivela en el perno (x=20, y=0, z=5)
        llamar(s, "create_joint_origin", geometry=">X", body=manivela, name="PernoManivela",
               offset=[20, 0, 0])  # en la cara >X de manivela, offset +20 en X local
        llamar(s, "create_joint",
               origin1="<X", body1=biela,
               origin2="PernoManivela",
               joint_type="revolute", rotation=0, name="J2_biela_manivela")

        # J3: Corredera → Biela (revolute en el otro extremo de la biela x=30)
        # Corredera cara <X (x=-10) contra biela cara >X (x=30)
        llamar(s, "create_joint",
               origin1="<X", body1=corredera,
               origin2=">X", body2=biela,
               joint_type="revolute", rotation=0, name="J3_corredera_biela")

        # J4: Corredera → Bastidor (slider en X)
        # Corredera cara <Z (z=-5) contra bastidor cara >Z (z=10), slider en X
        llamar(s, "create_joint",
               origin1="<Z", body1=corredera,
               origin2=">Z", body2=bastidor,
               joint_type="slider", slide_axis="X", slide=0, name="J4_corredera_bastidor")

        # Accionar J1 a theta
        llamar(s, "drive_joint", joint="J1_manivela", rotation=theta)

        # Verificar posición de la corredera
        ensamblaje = llamar(s, "get_assembly")
        comp_corredera = next(c for c in ensamblaje["components"] if c["name"] == "Corredera")
        t_corredera = np.array(comp_corredera["translation"])
        x_esperado = posicion_corredera_esperada(theta)
        assert abs(t_corredera[0] - x_esperado) < 1e-3, \
            f"θ={theta}°: corredera en x={t_corredera[0]:.3f}, esperado {x_esperado:.3f}"

        # Verificar que la biela mantiene su longitud l=60
        comp_biela = next(c for c in ensamblaje["components"] if c["name"] == "Biela")
        m_biela = np.array(comp_biela["rotation_matrix"]).reshape(3, 3)
        t_biela = np.array(comp_biela["translation"])
        # Biela pernos en extremos locales: (-30,0,0) y (30,0,0)
        extremo1 = m_biela @ np.array([-30.0, 0.0, 0.0]) + t_biela
        extremo2 = m_biela @ np.array([30.0, 0.0, 0.0]) + t_biela
        largo_biela = np.linalg.norm(extremo2 - extremo1)
        assert abs(largo_biela - l) < 1e-3, f"θ={theta}°: largo biela = {largo_biela:.3f}, esperado {l}"

        # Verificar J3: extremo de biela coincide con perno de corredera
        comp_corredera = next(c for c in ensamblaje["components"] if c["name"] == "Corredera")
        m_corr = np.array(comp_corredera["rotation_matrix"]).reshape(3, 3)
        t_corr = np.array(comp_corredera["translation"])
        # Corredera: origin1="<X" (cara x=-10, centro (-10,0,0) local)
        perno_j3_corr_local = np.array([-10.0, 0.0, 0.0])
        perno_j3_corr_global = m_corr @ perno_j3_corr_local + t_corr
        extremo_biela_j3 = m_biela @ np.array([30.0, 0.0, 0.0]) + t_biela
        dist_j3 = np.linalg.norm(extremo_biela_j3 - perno_j3_corr_global)
        assert dist_j3 < 1e-3, f"θ={theta}°: J3 abierto, distancia = {dist_j3:.6f}"


# =================================================================== ACCIONAR VARIAS VECES
def test_b71_accionar_varias_veces():
    """Accionar varias veces seguidas no deja ninguna unión en REFERENCE_LOST."""
    s = api.Sesion()

    base = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="A", grounded=True)

    brazo_b = llamar(s, "create_box", length=20, width=10, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[brazo_b], name="B")

    brazo_c = llamar(s, "create_box", length=15, width=10, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[brazo_c], name="C")

    llamar(s, "create_joint",
           origin1="<Z", body1=brazo_b,
           origin2=">Z", body2=base,
           joint_type="revolute", rotation=0, name="J1_AB")

    llamar(s, "create_joint",
           origin1=">X", body1=brazo_c,
           origin2="<X", body2=brazo_b,
           joint_type="revolute", rotation=0, name="J2_BC")

    # Accionar varias veces
    for ang in [0, 30, 60, 90, 120, 180, 270, 360, 45, 10]:
        llamar(s, "drive_joint", joint="J1_AB", rotation=ang)

    # Verificar que todas las uniones están OK
    ensamblaje = llamar(s, "get_assembly")
    for j in ensamblaje["joints"]:
        assert j["status"] != "error", f"Unión {j['name']} en error: {j['message']}"
        assert "REFERENCE_LOST" not in j.get("message", ""), f"Unión {j['name']} perdió referencia"


# =================================================================== LAZO SIN SOLUCIÓN
@pytest.mark.xfail(strict=True, reason="B-71 sigue abierto: el lazo cerrado (biela-manivela) no se resuelve; las uniones se aplican de a una y la última pisa a la corredera")
def test_b71_lazo_sin_solucion():
    """Biela más corta de lo necesario: el paso avisa y deja la última posición válida."""
    s = api.Sesion()

    # Bastidor fijo
    bastidor = llamar(s, "create_box", length=100, width=50, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[bastidor], name="Bastidor", grounded=True)

    # Manivela r=50
    manivela = llamar(s, "create_cylinder", radius=5, height=25)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[manivela], name="Manivela")

    # Biela l=30 (demasiado corta: r=50 > l=30, no puede alcanzar)
    biela = llamar(s, "create_box", length=30, width=10, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[biela], name="Biela")

    # Corredera
    corredera = llamar(s, "create_box", length=20, width=20, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[corredera], name="Corredera")

    # J1: Manivela → Bastidor
    llamar(s, "create_joint",
           origin1=">Z", body1=manivela,
           origin2=">Z", body2=bastidor,
           joint_type="revolute", rotation=0, name="J1")

    # J2: Biela → Manivela
    llamar(s, "create_joint",
           origin1="<X", body1=biela,
           origin2="%CYLINDER", body2=manivela,
           joint_type="revolute", rotation=0, name="J2")

    # J3: Corredera → Biela
    llamar(s, "create_joint",
           origin1="<X", body1=corredera,
           origin2=">X", body2=biela,
           joint_type="revolute", rotation=0, name="J3")

    # J4: Corredera → Bastidor (slider X)
    llamar(s, "create_joint",
           origin1="<Z", body1=corredera,
           origin2=">Z", body2=bastidor,
           joint_type="slider", slide_axis="X", slide=0, name="J4")

    # Accionar a 90°: manivela en (0, 50), biela de 30 no alcanza el slider en X
    r = api.llamar(s, "drive_joint", {"joint": "J1", "rotation": 90})

    # Debe avisar que el lazo no tiene solución
    assert not r["ok"] or any("lazo" in a.lower() or "sin solución" in a.lower() or "imposible" in a.lower()
                               for a in r.get("avisos", [])), \
        f"Debe avisar de lazo imposible, avisos: {r.get('avisos')}, error: {r.get('mensaje')}"

    # Verificar que quedó en la última posición válida (θ=0 o cercano)
    ensamblaje = llamar(s, "get_assembly")
    comp_corredera = next(c for c in ensamblaje["components"] if c["name"] == "Corredera")
    # En θ=0, corredera debería estar en x = 50 + 30 = 80
    # Si falló, no debería haber saltado a una posición aleatoria
    assert comp_corredera["translation"][0] > 70, "Corredera en posición inválida tras fallo"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])