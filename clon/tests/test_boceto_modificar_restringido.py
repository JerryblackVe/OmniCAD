"""Fase 5: MODIFICAR perfiles acotados, por la API y sin ventana.

La conservación de dof=0 es el contrato de esta auditoría. Las ambigüedades
de la ayuda de Fusion se detallan en D:/PROGRAMA/evidencias/cm_5/informe.md.
"""
import math

import pytest

from omnicad import api


class _FalloAuditoria(AssertionError):
    """Solo los hallazgos medidos admiten xfail; un error de preparación queda rojo."""


def _xfail(razon):
    return pytest.mark.xfail(strict=True, raises=_FalloAuditoria, reason=razon)


def _ok(r):
    assert r["ok"], r
    return r["result"]


def L(s, nombre, **args):
    return _ok(api.llamar(s, nombre, {"sketch": "B", **args}))


def _ids(r):
    return [e["id"] for e in r["entities"]]


def _rectangulo(s):
    L(s, "draw_rectangle", center_x=0, center_y=0, width=100, height=100,
      center_diagonals=True)
    lados = [e["id"] for e in L(s, "get_sketch")["entities"] if not e["construction"]]
    L(s, "add_dimension", type="distance", entities=[lados[0]], value=100)
    L(s, "add_dimension", type="distance", entities=[lados[1]], value=100)
    assert L(s, "get_sketch")["dof"] == 0
    return lados


def _circulo(s):
    r = L(s, "draw_circle", center_x=0, center_y=0, radius=25)
    curva = _ids(r)[0]
    L(s, "add_constraint", type="coincident", entities=[r["points"][0], 0])
    L(s, "add_dimension", type="diameter", entities=[curva], value=50)
    return [curva]


def _ranura(s):
    r = L(s, "draw_slot", kind="center_point", points=[[0, 0], [30, 0]], width=20)
    g = L(s, "get_sketch")
    eje = next(e for e in g["entities"] if e["construction"])
    centro = next(c["entities"][0] for c in g["constraints"] if c["type"] == "midpoint")
    arco = next(e["id"] for e in g["entities"] if e["type"] == "arc")
    L(s, "add_constraint", type="coincident", entities=[centro, 0])
    L(s, "add_constraint", type="horizontal", entities=[eje["id"]])
    L(s, "add_dimension", type="distance", entities=[eje["id"]], value=60)
    L(s, "add_dimension", type="radius", entities=[arco], value=10)
    return [e for e in _ids(r) if e != eje["id"]]


_PERFILES = {"rectangulo": _rectangulo, "circulo": _circulo, "ranura": _ranura}


def _crear(perfil):
    s = api.Sesion()
    _ok(api.llamar(s, "create_sketch", {"name": "B"}))
    curvas = _PERFILES[perfil](s)
    g = L(s, "get_sketch")
    if g["dof"] != 0 or g["status"] != "fully_constrained":
        raise RuntimeError(f"El perfil base {perfil} no está restringido: {g}")
    return s, curvas


def _contorno(g):
    return [e for e in g["entities"] if not e["construction"]]


def _medidas(g):
    """Largos, radios y cuerdas; no confundir un traslado rígido con deformación."""
    medidas = {}
    for e in _contorno(g):
        valores = [e[k] for k in ("length", "radius") if k in e]
        if e["type"] == "arc":
            valores.append(math.dist(e["start"], e["end"]))
        medidas[e["id"]] = valores
    return medidas


def _bajas(antes, despues, r, permitidas):
    fallos = []
    for clave, informe in (("constraints", "constraints_deleted"), ("dimensions", "dimensions_deleted")):
        bajas = {c["id"] for c in antes[clave]} - {c["id"] for c in despues[clave]}
        if bajas != set(r.get(informe, [])):
            fallos.append(f"{informe}: informadas={r.get(informe, [])}, reales={sorted(bajas)}")
        indebidas = bajas - permitidas
        if indebidas:
            fallos.append(f"{clave}: borrados ajenos={sorted(indebidas)}")
    if despues["dof"] != 0 or despues["status"] != "fully_constrained":
        fallos.append(f"dof={despues['dof']}, estado={despues['status']}; esperado=0/fully_constrained")
    return fallos


def _arrastrar(s, g):
    # Elegir todos los puntos del contorno, incluidos los nuevos del corte o las copias.
    puntos = {p for e in _contorno(g) for p in e["points"]}
    medidas = _medidas(g)
    for p in g["points"]:
        if p["id"] not in puntos:
            continue
        r = api.llamar(s, "move_sketch_point", {"sketch": "B", "point": p["id"],
                                               "x": p["x"] + 7, "y": p["y"] + 11})
        actual = L(s, "get_sketch")
        if not r["ok"]:
            assert actual == g, r
            continue
        nuevas = _medidas(actual)
        for cid, valores in medidas.items():
            if nuevas.get(cid) != pytest.approx(valores, abs=5e-4):
                return [f"arrastre punto {p['id']}, curva {cid}: {valores} -> {nuevas.get(cid)}"]
        if actual["dof"] != g["dof"] or actual["status"] == "over_constrained":
            return [f"arrastre punto {p['id']}: dof {g['dof']} -> {actual['dof']}, estado={actual['status']}"]
        g = actual
    return []


def _guardar_abrir(s):
    receta = _ok(api.llamar(s, "get_recipe", {}))
    otra = api.Sesion()
    _ok(api.llamar(otra, "apply_recipe", {"recipe": receta}))
    assert L(otra, "get_sketch") == L(s, "get_sketch")


@pytest.mark.parametrize("perfil", _PERFILES)
def test_perfil_base_acotado(perfil):
    s, _ = _crear(perfil)
    g = L(s, "get_sketch")
    areas = {"rectangulo": 10000, "circulo": math.pi * 25**2,
             "ranura": 60 * 20 + math.pi * 10**2}
    assert g["profiles"][0]["area"] == pytest.approx(areas[perfil], abs=5e-4)
    assert not any(c["reference"] for c in g["dimensions"])
    _guardar_abrir(s)


@pytest.mark.parametrize("perfil", [
    "rectangulo", "circulo",
    "ranura",
])
def test_perfil_base_no_se_deforma(perfil):
    s, _ = _crear(perfil)
    fallos = _arrastrar(s, L(s, "get_sketch"))
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))


def test_b242_empalme_conserva_cotas_y_cero_grados_de_libertad():
    """Separado del arrastre: la pérdida de restricciones de B-242 no debe quedar tapada por otro xfail."""
    s, lados = _crear("rectangulo")
    antes = L(s, "get_sketch")
    r = L(s, "sketch_fillet", entity1=lados[0], entity2=lados[1], radius=5)
    despues = L(s, "get_sketch")
    assert despues["dof"] == 0
    assert not _bajas(antes, despues, r, set())
    assert [(c["id"], c["value"]) for c in despues["dimensions"][:2]] == [
        (c["id"], c["value"]) for c in antes["dimensions"]]
    _guardar_abrir(s)


_ESQUINAS = [
    "empalme",
    "chaflan_igual",
    "chaflan_dos_distancias",
    "chaflan_angulo",
]


@pytest.mark.parametrize("herramienta", _ESQUINAS)
def test_esquina_rectangulo_restringido(herramienta):
    s, lados = _crear("rectangulo")
    antes = L(s, "get_sketch")
    if herramienta == "empalme":
        r = L(s, "sketch_fillet", entity1=lados[0], entity2=lados[1], radius=5)
        area = 10000 - 25 * (1 - math.pi / 4)
    else:
        args = {"chaflan_igual": {}, "chaflan_dos_distancias": {"distance2": 8},
                "chaflan_angulo": {"angle": 30}}[herramienta]
        r = L(s, "sketch_chamfer", line1=lados[0], line2=lados[1], distance=5, **args)
        segunda = {"chaflan_igual": 5, "chaflan_dos_distancias": 8,
                   "chaflan_angulo": 5 * math.tan(math.radians(30))}[herramienta]
        area = 10000 - 5 * segunda / 2
    despues = L(s, "get_sketch")
    assert len(_contorno(despues)) == 5
    assert despues["profiles"][0]["area"] == pytest.approx(area, abs=5e-4)
    esquina = set(antes["entities"][0]["points"]) & set(antes["entities"][1]["points"])
    permitidas = {c["id"] for c in antes["constraints"]
                  if c["type"] == "coincident" and set(c["entities"]) <= esquina}
    fallos = _bajas(antes, despues, r, permitidas)
    _guardar_abrir(s)
    fallos += _arrastrar(s, despues)
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))


def _guia(s, x1, y1, x2, y2):
    curva = _ids(L(s, "draw_line", start_x=x1, start_y=y1, end_x=x2, end_y=y2,
                   construction=True))[0]
    L(s, "add_constraint", type="fix", entities=[curva])
    assert L(s, "get_sketch")["dof"] == 0
    return curva


@pytest.mark.parametrize(("perfil", "herramienta"), [
    pytest.param("rectangulo", "recortar", marks=_xfail("Duda: recortar deja dof=2; arrastre 50 -> 43 mm")),
    ("circulo", "recortar"),
    pytest.param("ranura", "recortar", marks=_xfail("Duda: recortar deja dof=1; arrastre 30 -> 28.2843 mm")),
    pytest.param("rectangulo", "partir", marks=_xfail("Duda: partir deja dof=1; arrastre 50 -> 43 mm")),
    ("circulo", "partir"),
    pytest.param("ranura", "partir", marks=_xfail("Duda: partir deja dof=1; arrastre 30 -> 28.2843 mm")),
    pytest.param("rectangulo", "alargar", marks=_xfail("Duda: alargar borra cota 18; dof=2; arrastre 130 -> 123 mm")),
    pytest.param("ranura", "alargar", marks=_xfail("Duda: alargar deja dof=1; cuerda 20 -> 19.5907 mm")),
])
def test_editar_curva_restringida(perfil, herramienta):
    s, curvas = _crear(perfil)
    if herramienta == "alargar":
        _guia(s, 80, -100, 80, 100)
        punto = [49, -50] if perfil == "rectangulo" else [29, 10]
    else:
        _guia(s, 0, -80, 0, 80)
        punto = {"rectangulo": [25, -50], "circulo": [25, 0], "ranura": [15, 10]}[perfil]
    antes = L(s, "get_sketch")
    objetivo = next(e for e in antes["entities"] if e["id"] == curvas[0])
    if herramienta == "recortar":
        r = L(s, "trim_sketch_curve", entity=curvas[0], x=punto[0], y=punto[1])
    else:
        nombre = "split_sketch_curve" if herramienta == "partir" else "extend_sketch_curve"
        r = L(s, nombre, curve=curvas[0], point=punto)
    despues = L(s, "get_sketch")
    # La cota del lado que se corta puede reemplazarse; no la de su vecino ni la del eje.
    # Duda documental: los artículos no enumeran esas bajas (ver informe).
    permitidas = {c["id"] for c in antes["dimensions"]
                  if c["entities"] == [objetivo["id"]] and c["type"] in {"distance", "horizontal", "vertical"}
                  } if herramienta != "alargar" else set()
    fallos = _bajas(antes, despues, r, permitidas)
    cantidad = len(_contorno(antes)) + (1 if herramienta == "partir" else 0)
    assert len(_contorno(despues)) == cantidad
    if herramienta == "alargar":
        linea = next(e for e in despues["entities"] if e["id"] == curvas[0])
        assert linea["length"] == pytest.approx(130 if perfil == "rectangulo" else 110, abs=5e-4)
    else:
        piezas = r["pieces"] if herramienta == "partir" else [curvas[0]]
        assert len(piezas) == (2 if herramienta == "partir" else 1)
        for e in _contorno(despues):
            if e["id"] not in piezas:
                continue
            if perfil == "circulo":
                assert e["radius"] == 25
                assert math.dist(e["start"], e["end"]) == 50
            else:
                assert e["length"] == (50 if perfil == "rectangulo" else 30)
    _guardar_abrir(s)
    fallos += _arrastrar(s, despues)
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))


@pytest.mark.parametrize("perfil", [
    "rectangulo",
    "circulo",
    pytest.param("ranura", marks=_xfail("Desfase: dof=4; arrastre cambia lado 60 -> 56.5685 mm")),
])
def test_desfase_restringido(perfil):
    s, curvas = _crear(perfil)
    antes = L(s, "get_sketch")
    r = L(s, "offset_sketch_curves", entity=curvas[0], distance=5)
    despues = L(s, "get_sketch")
    fallos = _bajas(antes, despues, r, set())
    assert len(_contorno(despues)) == 2 * len(curvas)
    originales = {e["id"]: e for e in _contorno(antes)}
    assert {e["id"]: e for e in _contorno(despues) if e["id"] in originales} == originales
    nuevas = [e for e in _contorno(despues) if e["id"] not in curvas]
    if perfil == "circulo":
        assert nuevas[0]["radius"] == 30
    elif perfil == "rectangulo":
        assert [e["length"] for e in nuevas] == [110] * 4
    else:
        assert sorted(e["radius"] for e in nuevas if e["type"] == "arc") == [15, 15]
    _guardar_abrir(s)
    fallos += _arrastrar(s, despues)
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))


@pytest.mark.parametrize(("perfil", "herramienta"), [
    ("rectangulo", "mover"), ("circulo", "mover"),
    pytest.param("ranura", "mover", marks=_xfail("Mover dx200 responde ok pero centro sigue x=0; cuerda 20 -> 0 mm")),
    pytest.param("rectangulo", "copiar", marks=_xfail("Duda: copia dx200 deja dof=2 en vez de 0")),
    pytest.param("circulo", "copiar", marks=_xfail("Duda: copia dx200 deja dof=2 en vez de 0")),
    pytest.param("ranura", "copiar", marks=_xfail("Duda: copia dx200 deja dof=2; cuerda 20 -> 0 mm")),
    ("rectangulo", "escalar"), ("circulo", "escalar"), ("ranura", "escalar"),
])
def test_transformacion_restringida(perfil, herramienta):
    s, curvas = _crear(perfil)
    antes = L(s, "get_sketch")
    factor = 2 if herramienta == "escalar" else 1
    dx = 0 if herramienta == "escalar" else 200
    respuesta = api.llamar(s, "transform_sketch", {"sketch": "B", "dx": dx, "scale": factor,
                                                  "center_x": 0, "center_y": 0,
                                                  "copy": herramienta == "copiar"})
    despues = L(s, "get_sketch")
    if not respuesta["ok"]:
        assert despues == antes, respuesta
        # Mover un perfil anclado puede ser rechazado: debe quedar entero y acotado.
        assert herramienta in {"mover", "escalar"} and respuesta["error_kind"] in {
            "INVALID_GEOMETRY", "SKETCH_OVERCONSTRAINED"}, respuesta
        _guardar_abrir(s)
        assert not _arrastrar(s, despues)
        return
    r = respuesta["result"]
    fallos = _bajas(antes, despues, r, set())
    copias = herramienta == "copiar"
    assert len(_contorno(despues)) == len(curvas) * (2 if copias else 1)
    nuevas = [e for e in _contorno(despues) if not copias or e["id"] not in curvas]
    if copias:
        assert [e for e in _contorno(despues) if e["id"] in curvas] == _contorno(antes)
    for original, nueva in zip(_contorno(antes), nuevas, strict=True):
        for clave in ("start", "end", "center"):
            if clave in original:
                esperado = [original[clave][0] * factor + dx, original[clave][1] * factor]
                if nueva[clave] != pytest.approx(esperado, abs=5e-4):
                    fallos.append(f"{clave} curva {nueva['id']}: {nueva[clave]}, esperado={esperado}")
        for clave in ("length", "radius"):
            if clave in original:
                assert nueva[clave] == pytest.approx(original[clave] * factor, abs=5e-4)
    _guardar_abrir(s)
    fallos += _arrastrar(s, despues)
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))


@pytest.mark.parametrize("perfil", [
    "rectangulo", "circulo",
    "ranura",
])
@pytest.mark.parametrize("herramienta", ["simetria", "patron_rectangular", "patron_circular"])
def test_repeticion_restringida(perfil, herramienta):
    s, curvas = _crear(perfil)
    if herramienta == "simetria":
        eje = _guia(s, 100, -150, 100, 150)
    antes = L(s, "get_sketch")
    if herramienta == "simetria":
        r = L(s, "mirror_sketch", entities=curvas, axis=eje)
    elif herramienta == "patron_rectangular":
        r = L(s, "sketch_rectangular_pattern", entities=curvas, count1=2, distance1=200)
    else:
        r = L(s, "sketch_circular_pattern", entities=curvas, count=2, total_angle=180,
              center_x=200, center_y=0)
    despues = L(s, "get_sketch")
    assert len(_contorno(despues)) == 2 * len(curvas)
    originales = {e["id"]: e for e in _contorno(antes)}
    assert {e["id"]: e for e in _contorno(despues) if e["id"] in originales} == originales
    nuevas = [e for e in _contorno(despues) if e["id"] not in curvas]
    for original, nueva in zip(_contorno(antes), nuevas, strict=True):
        for clave in ("length", "radius"):
            if clave in original:
                assert nueva[clave] == original[clave]
        for clave in ("start", "end", "center"):
            if clave not in original:
                continue
            # El espejo invierte la orientación del arco y por eso intercambia sus extremos.
            origen = original["end" if clave == "start" else "start"] if (
                herramienta == "simetria" and original["type"] == "arc" and clave != "center"
            ) else original[clave]
            x, y = origen
            esperado = {"simetria": [200 - x, y], "patron_rectangular": [200 + x, y],
                        "patron_circular": [400 - x, -y]}[herramienta]
            assert nueva[clave] == pytest.approx(esperado, abs=5e-4)
    fallos = _bajas(antes, despues, r, set())
    _guardar_abrir(s)
    fallos += _arrastrar(s, despues)
    if fallos:
        raise _FalloAuditoria("; ".join(fallos))
