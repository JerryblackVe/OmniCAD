# -*- coding: utf-8 -*-
"""Test para B-71: uniones encadenadas y lazos cerrados (biela-manivela, cuadrilátero articulado).
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


# =================================================================== LAZOS CERRADOS
# Los eslabones son una barra (caja) más un perno cilíndrico (eje Z) en cada extremo; los pernos miden lo
# mismo, así que dos pernos unidos quedan con sus centros coincidentes. La posición de una pieza es la
# traslación de su componente: el origen local de cada eslabón es su primer perno.
def _eslabon(s, nombre, largo, pernos=None, ancho=10, fijo=False):
    """Componente de una barra de `largo` mm sobre +X con pernos en x = `pernos` (por defecto en 0 y `largo`).
    Devuelve los ids de los cuerpos de los pernos."""
    pernos = [0.0, largo] if pernos is None else pernos
    barra = llamar(s, "create_box", length=largo + 10, width=ancho, height=10, x=largo / 2)["bodies_created"][0]["id"]
    ids = [llamar(s, "create_cylinder", radius=3, height=14, x=x)["bodies_created"][0]["id"] for x in pernos]
    llamar(s, "create_component", bodies=[barra, *ids], name=nombre, grounded=fijo)
    return ids


def _perno(s, nombre, perno, otro, tipo="revolute", **extra):
    """Une el perno `perno` (el componente que se mueve) con el perno `otro` (el componente al que va)."""
    llamar(s, "create_joint", origin1="%CYLINDER", body1=perno, origin2="%CYLINDER", body2=otro,
           joint_type=tipo, name=nombre, **extra)


def _pose(s):
    """{nombre de componente: (R 3x3, traslación)} con la matriz exacta del estado (get_assembly redondea a 4
    decimales, y con brazos de 60 mm eso ya pasa de 0,001 mm)."""
    comps = s.doc.estado_final.componentes
    mats = {c["nombre"]: np.asarray(c["matriz"], float) for c in comps.values()}
    return {n: (m[:3, :3], m[:3, 3]) for n, m in mats.items()}


def _estados(s):
    """{nombre de unión: (estado, mensaje)} desde get_assembly."""
    return {j["name"]: (j["status"], j.get("message") or "") for j in llamar(s, "get_assembly")["joints"]}


def _biela_manivela(r=20.0, l=60.0, theta=0.0):
    """Manivela de radio r, biela de largo l y corredera sobre el eje X que pasa por el eje de la manivela.
    Uniones: J1 manivela-bastidor (se acciona), J2 biela-manivela, J3 corredera-biela y J4 corredera-bastidor
    (deslizante en X), que cierra el lazo."""
    s = api.Sesion()
    (p0,) = _eslabon(s, "Bastidor", 0.0, pernos=[0.0], ancho=60, fijo=True)
    a0, a1 = _eslabon(s, "Manivela", r)
    b1, b2 = _eslabon(s, "Biela", l)
    (pc,) = _eslabon(s, "Corredera", 0.0, pernos=[0.0], ancho=20)
    _perno(s, "J1", a0, p0, rotation=theta)
    _perno(s, "J2", b1, a1, rotation=0)
    _perno(s, "J3", pc, b2, rotation=0)
    _perno(s, "J4", pc, p0, tipo="slider", slide_axis="X", slide=0)
    return s


def _comprobar_biela_manivela(s, theta, r=20.0, l=60.0):
    th = math.radians(theta)
    x_esperado = r * math.cos(th) + math.sqrt(l ** 2 - (r * math.sin(th)) ** 2)
    pose = _pose(s)
    r_man, t_man = pose["Manivela"]
    r_bie, t_bie = pose["Biela"]
    _, t_cor = pose["Corredera"]
    # la corredera queda en x = r·cosθ + sqrt(l² − (r·sinθ)²), sobre el eje X
    assert abs(t_cor[0] - x_esperado) < 1e-3, f"θ={theta}°: corredera x={t_cor[0]:.4f}, esperado {x_esperado:.4f}"
    assert abs(t_cor[1]) < 1e-3, f"θ={theta}°: corredera salió del eje X (y={t_cor[1]:.4f})"
    # el perno de la manivela es el primer perno de la biela, y el segundo de la biela es el perno de la corredera
    perno_manivela = r_man @ np.array([r, 0.0, 0.0]) + t_man
    assert np.linalg.norm(t_bie - perno_manivela) < 1e-3, f"θ={theta}°: J2 abierta"
    perno_biela = r_bie @ np.array([l, 0.0, 0.0]) + t_bie
    assert np.linalg.norm(t_cor - perno_biela) < 1e-3, f"θ={theta}°: J3 abierta"
    assert abs(np.linalg.norm(perno_biela - t_bie) - l) < 1e-3     # la biela no se estira
    for nombre, (estado, mensaje) in _estados(s).items():
        assert estado != "error", f"θ={theta}°: unión {nombre} en error: {mensaje}"


@pytest.mark.parametrize("theta", [0, 30, 90, 135, 180, 270, -40])
def test_b71_biela_manivela(theta):
    """Lazo cerrado biela-manivela: al accionar la manivela a θ, la corredera queda en
    x = r·cosθ + sqrt(l² − (r·sinθ)²) (±1e-3 mm) y los pernos de la biela coinciden con los de la manivela y la
    corredera. Antes del arreglo J4 se aplicaba última y arrastraba a la corredera al origen, rompiendo J3."""
    s = _biela_manivela(theta=0)
    if theta:
        llamar(s, "drive_joint", joint="J1", rotation=theta)
    _comprobar_biela_manivela(s, theta)


def test_b71_biela_manivela_barrido():
    """Accionar la manivela de a pasos seguidos (cada paso recalcula el mecanismo) mantiene el lazo cerrado y
    ninguna unión pierde su referencia."""
    s = _biela_manivela()
    for theta in range(0, 361, 20):
        llamar(s, "drive_joint", joint="J1", rotation=theta)
        _comprobar_biela_manivela(s, theta)
    for nombre, (estado, mensaje) in _estados(s).items():
        assert "REFERENCE_LOST" not in mensaje, nombre


def test_b71_cuadrilatero_articulado():
    """Lazo de cuatro barras con todas las uniones de giro: bastidor con pernos en (0,0) y (50,0); manivela
    a=20, acoplador b=50 y balancín c=40. Para cada θ los pernos de unión coinciden y las barras no se
    estiran (cualquiera de las dos configuraciones del cuadrilátero vale)."""
    a, b, c, d = 20.0, 50.0, 40.0, 50.0
    s = api.Sesion()
    p0, p3 = _eslabon(s, "Bastidor", d, ancho=60, fijo=True)
    m0, m1 = _eslabon(s, "Manivela", a)
    c0, c1 = _eslabon(s, "Acoplador", b)
    r0, r1 = _eslabon(s, "Balancin", c)
    _perno(s, "J1", m0, p0, rotation=0)
    _perno(s, "J2", c0, m1, rotation=0)
    _perno(s, "J3", r1, c1, rotation=0)       # el balancín entra por su extremo libre...
    _perno(s, "J4", r0, p3, rotation=0)       # ...y su otro perno cierra el lazo contra el bastidor
    for theta in (0, 60, 150, 230, 320):
        llamar(s, "drive_joint", joint="J1", rotation=theta)
        pose = _pose(s)
        rm, tm = pose["Manivela"]
        rc, tc = pose["Acoplador"]
        rr, tr = pose["Balancin"]
        perno_m = rm @ np.array([a, 0, 0]) + tm
        perno_c = rc @ np.array([b, 0, 0]) + tc
        perno_r = rr @ np.array([c, 0, 0]) + tr
        assert np.linalg.norm(tc - perno_m) < 1e-3, f"θ={theta}°: J2 abierta"
        assert np.linalg.norm(perno_r - perno_c) < 1e-3, f"θ={theta}°: J3 abierta"
        assert np.linalg.norm(tr[:2] - np.array([d, 0.0])) < 1e-3, f"θ={theta}°: J4 abierta (balancín fuera de su perno)"
        assert abs(np.linalg.norm(perno_m - tm) - a) < 1e-3
        for nombre, (estado, mensaje) in _estados(s).items():
            assert estado != "error", f"θ={theta}°: unión {nombre} en error: {mensaje}"


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
def test_b71_lazo_sin_solucion():
    """Manivela r=50 con biela l=30 (más corta que la manivela): a 0° el lazo cierra, pero a 90° la biela no
    alcanza el eje X. drive_joint se rechaza con un error que habla del lazo y el mecanismo se queda en la última
    posición válida (la de 0°); después, un ángulo alcanzable lo recupera."""
    s = _biela_manivela(r=50.0, l=30.0, theta=0)
    _comprobar_biela_manivela(s, 0, r=50.0, l=30.0)
    r = api.llamar(s, "drive_joint", {"joint": "J1", "rotation": 90})
    assert not r["ok"], r
    assert "lazo" in r["mensaje"].lower(), r
    _comprobar_biela_manivela(s, 0, r=50.0, l=30.0)           # no saltó a una posición arbitraria
    llamar(s, "drive_joint", joint="J1", rotation=30)
    _comprobar_biela_manivela(s, 30, r=50.0, l=30.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
