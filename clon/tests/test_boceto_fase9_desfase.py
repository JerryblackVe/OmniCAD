"""BOC-14b: desfase asociativo sobre la normal de splines y elipses (Offset de Fusion)."""
import json
import math

import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_resuelto
from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones.boceto import evaluar_primitiva, mas_cercano


def _madre(b, tipo):
    if tipo == "elipse":
        return b.agregar_elipse((20, 20), (30, 20), 6, ejes=False)
    return b.agregar_spline([(10, 10), (20, 16), (30, 16), (40, 10)], modo=tipo)


def _mover_madre(b, madre):
    c = b.curvas[madre]
    pid = c.mayor if c.tipo == "elipse" else c.pts[1]
    b.puntos[pid].y += 3
    return pid


def _distancias(b, madre, copia):
    prim = b.primitivas(madre)[0]
    return [mas_cercano(prim, b.coords(p))[1] for p in b.curvas[copia].pts]


@pytest.mark.parametrize("tipo", ["ajuste", "control", "elipse"])
@pytest.mark.parametrize("invertir", [False, True])
def test_desfase_sigue_la_deformacion_de_la_madre(tipo, invertir):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1, invertir=invertir)
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    b.agregar_restriccion("fijo", [madre])
    pid = _mover_madre(b, madre)
    objetivo = b.coords(pid)
    valores = {k.id: 1 for k in b.cotas.values() if k.tipo == "desfase"}
    resultado = resolver(b, valores)
    assert resultado.ok, resultado.descripcion()
    assert b.coords(pid) == objetivo
    assert _distancias(b, madre, copia) == pytest.approx([1] * len(antes), abs=1e-3)
    assert max(math.dist(a, b.coords(p)) for a, p in zip(antes, b.curvas[copia].pts, strict=True)) > 0.1
    assert b.separacion(madre, copia) == pytest.approx(1, abs=1e-3)


@pytest.mark.parametrize("tipo", ["ajuste", "elipse"])
def test_cota_de_desfase_conserva_expresion_lado_y_asociacion_al_serializar(tipo):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1, expresion="separacion", invertir=True)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    assert cota.entidades == [madre, copia] and cota.expresion == "separacion"
    b = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))
    b.agregar_restriccion("fijo", [madre])
    _mover_madre(b, madre)
    assert resolver(b, {cota.id: 1.5}).ok
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    prim = b.primitivas(madre)[0]
    for pid in b.curvas[copia].pts:
        p = b.coords(pid)
        t, _, q = mas_cercano(prim, p)
        _, d = evaluar_primitiva(prim, t, 1)
        lado = (d[0] * (p[1] - q[1]) - d[1] * (p[0] - q[0])) / math.hypot(*d)
        assert lado == pytest.approx(1.5 if tipo == "elipse" else -1.5, abs=1e-3)


@pytest.mark.parametrize("tipo", ["ajuste", "elipse"])
@pytest.mark.parametrize("por_madre", [False, True])
@pytest.mark.parametrize("conservar_cota", [False, True])
def test_soltar_desfase_desliga_la_copia_sin_borrarla(tipo, por_madre, conservar_cota):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1)
    b.agregar_restriccion("fijo", [madre])
    b.soltar_desfase(madre if por_madre else copia, conservar_cota=conservar_cota)
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    _mover_madre(b, madre)
    assert resolver(b, {k.id: 1 for k in b.cotas.values()}).ok
    assert [b.coords(p) for p in b.curvas[copia].pts] == antes
    assert max(abs(d - 1) for d in _distancias(b, madre, copia)) > 0.1
    assert len(b.cotas) == int(conservar_cota)
    assert all(k.referencia for k in b.cotas.values())


def test_separacion_de_curvas_libres_mide_la_distancia_a_la_madre():
    b = Boceto()
    madre = _madre(b, "elipse")
    copia, = b.desfase(madre, 1)
    assert b.separacion(madre, copia) == pytest.approx(1, abs=1e-3)


def test_distancia_a_elipse_busca_a_ambos_lados_del_cierre_periodico():
    b = Boceto()
    madre = _madre(b, "elipse")
    prim = b.primitivas(madre)[0]
    t = 2 * math.pi - 0.02
    q, d = evaluar_primitiva(prim, t, 1)
    n = math.hypot(*d)
    p = (q[0] + d[1] / n, q[1] - d[0] / n)
    parametro, distancia, _ = mas_cercano(prim, p)
    assert distancia == pytest.approx(1, abs=1e-6)
    assert parametro == pytest.approx(t, abs=1e-6)


@pytest.mark.parametrize("tipo", ["spline", "elipse"])
def test_api_parametro_arrastre_y_release_offset(tipo):
    sesion = api.Sesion()

    def llamar(nombre, **parametros):
        respuesta = api.llamar(sesion, nombre, parametros)
        assert respuesta["ok"], respuesta
        return respuesta["result"]

    llamar("create_sketch", plane="XY")
    llamar("create_parameter", name="separacion", expression="1 mm")
    dibujo = (llamar("draw_spline", points=[[10, 10], [20, 16], [30, 16], [40, 10]]) if tipo == "spline" else
              llamar("draw_ellipse", center_x=20, center_y=20, major_radius=10, minor_radius=6))
    madre = dibujo["entities"][0]["id"]
    copia = llamar("offset_sketch_curves", entity=madre, distance="separacion")["entities"][0]["id"]
    llamar("set_parameter", name="separacion", expression="1.5 mm")
    op = sesion.doc.operaciones[0]
    b = boceto_resuelto(sesion, op).boceto
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    c = b.curvas[madre]
    pid = c.mayor if tipo == "elipse" else c.pts[1]
    x, y = b.coords(pid)
    assert llamar("move_sketch_point", point=pid, x=x, y=y + 3)["reached"]
    b = boceto_resuelto(sesion, op).boceto
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    llamar("release_offset", entity=copia)
    b = boceto_resuelto(sesion, op).boceto
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    x, y = b.coords(pid)
    llamar("move_sketch_point", point=pid, x=x, y=y + 3)
    b = boceto_resuelto(sesion, op).boceto
    assert [b.coords(p) for p in b.curvas[copia].pts] == antes


@pytest.mark.parametrize("puntos, cantidad", [([(0, 0), (20, 10), (40, -5), (60, 5)], 48),
                                              ([(i * 30, 15 * (-1) ** i) for i in range(12)], None)])
def test_desfase_de_spline_queda_dentro_de_la_tolerancia_de_fusion(puntos, cantidad):
    """B-710: Fusion aproxima la curva desfasada exacta hasta 0,01 mm (resfit); la spline larga ya no entra con 48
    puntos fijos (0,22 mm) y se parte donde hace falta, con cada punto atado a su t de la madre (B-231)."""
    import numpy as np
    from scipy.spatial import cKDTree
    from omnicad.restricciones.boceto import dominio
    from omnicad.restricciones.boceto_desfase import _normales
    b = Boceto()
    madre = b.agregar_spline(puntos)
    copia, = b.desfase(madre, 3)
    pts = b.curvas[copia].pts
    assert len(pts) == cantidad if cantidad else len(pts) > 48
    restriccion, = (r for r in b.restricciones.values() if r.tipo == "desfase")
    assert set(restriccion.datos["parametros"]) == {str(p) for p in pts}

    def densos(cid, n):
        prim = b.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        return _normales(prim, np.linspace(t0, t1, n))[0]
    error = np.abs(cKDTree(densos(madre, 200000)).query(densos(copia, 3000))[0] - 3).max()
    assert error < 0.01



def test_cambiar_la_cota_de_la_spline_larga_sigue_exacto_y_rapido():
    """P-184: los puntos atados a su t van en un término vectorizado; cambiar la cota de la spline larga (108 puntos)
    tardaba ~12 s. Dos cambios seguidos (el segundo sobre la copia ya movida) y con la madre deformada: cada punto de
    la copia, a la distancia de la cota y en su t de la madre (B-231)."""
    import time
    b = Boceto()
    madre = b.agregar_spline([(i * 30, 15 * (-1) ** i) for i in range(12)])
    copia, = b.desfase(madre, 3)
    cota = next(k for k, c in b.cotas.items() if c.tipo == "desfase")
    ts = next(r for r in b.restricciones.values() if r.tipo == "desfase").datos["parametros"]

    def exacto(d):
        prim = b.primitivas(madre)[0]
        for p in b.curvas[copia].pts:
            t, dist, _q = mas_cercano(prim, b.coords(p))
            assert abs(dist - d) < 1e-6 and abs(t - ts[str(p)]) < 1e-6
    t = time.perf_counter()
    for d in (4.0, 5.0):
        assert resolver(b, {cota: d}).ok
        exacto(d)
    assert time.perf_counter() - t < 15       # antes ~21 s los dos; hoy ~3 s (holgado para una máquina lenta)
    b.agregar_restriccion("fijo", [madre])
    b.puntos[b.curvas[madre].pts[5]].y += 4
    assert resolver(b, {cota: 5.0}).ok
    exacto(5.0)


def _spline_larga_ya_modificada():
    """Desfase de la spline larga con la cota ya cambiada (copia rehecha por B-711) y la madre deformada."""
    from omnicad.restricciones import solver as S
    b = Boceto()
    madre = b.agregar_spline([(i * 30, 15 * (-1) ** i) for i in range(12)])
    b.desfase(madre, 3)
    cota = next(k for k, c in b.cotas.items() if c.tipo == "desfase")
    assert resolver(b, {cota: 4.0}).ok
    b.puntos[b.curvas[madre].pts[5]].y += 4
    v = {cota: 5.0}
    return S._Sistema(b, v, S._grupos(b)[0], fusionar=True)


def test_jacobiano_del_desfase_de_spline_por_filas_da_lo_mismo(monkeypatch):
    """P-185: el término de los puntos atados dice qué incógnita es de cada fila; el coloreo junta las columnas de la
    copia (224 puntos: de ~450 evaluaciones por jacobiano a ~30) y el jacobiano da lo mismo, bit a bit."""
    import numpy as np
    from omnicad.restricciones import solver as S
    sis = _spline_larga_ya_modificada()
    atados = [f for f in sis.terminos if hasattr(f, "propias")]
    assert atados
    J, colores = S._jacobiano(sis, sis.x0), len(sis._coloreo[1])
    for f in atados:
        monkeypatch.delattr(f, "propias")
    assert np.array_equal(J, S._jacobiano(sis, sis.x0)) and colores * 5 < len(sis._coloreo[1])


def test_jacobiano_del_desfase_si_las_filas_fallan_lee_todo(monkeypatch):
    import numpy as np
    from omnicad.restricciones import solver as S
    sis = _spline_larga_ya_modificada()
    f = next(f for f in sis.terminos if hasattr(f, "propias"))
    J = S._jacobiano(sis, sis.x0)
    monkeypatch.setattr(f, "propias", [None] * len(f.propias), raising=False)      # filas rotas: camino normal
    assert np.array_equal(J, S._jacobiano(sis, sis.x0))


def test_energia_de_la_quintica_es_la_de_tramo_por_tramo():
    """P-185: la matriz de energía copia la del tramo uniforme del medio (antes, 0,34 s con 224 puntos)."""
    import numpy as np
    from omnicad.restricciones.boceto_geometria import _GAUSS_W, _GAUSS_X, _PESOS_ENERGIA, _base_derivada, _energia_quintica
    for m in (1, 3, 40):
        nudos, H2 = _energia_quintica(m)
        p, n = 5, len(nudos) - 6
        H = np.zeros((n, n))
        for s in range(5 * m):
            a0, a1 = nudos[p + s], nudos[p + s + 1]
            for x, w in zip(_GAUSS_X, _GAUSS_W, strict=True):
                u, jac = 0.5 * (a0 + a1 + (a1 - a0) * x), 0.5 * (a1 - a0) * w
                for orden in (1, 2, 3):
                    b = np.asarray(_base_derivada(nudos, p, u, p + s, orden))
                    H[s:s + p + 1, s:s + p + 1] += _PESOS_ENERGIA[orden] * jac * np.outer(b, b)
        assert np.abs(H2.toarray() - 2 * H).max() <= 1e-12 * np.abs(H).max()


def test_cambiar_la_cota_rehace_la_copia_dentro_de_la_tolerancia():
    """B-711: los puntos de la copia son los de la distancia con que se creó; al cambiar la cota, entre ellos se
    alejaba de la curva desfasada exacta (3→5 mm: 0,031 mm). Fusion la rehace tras resolver: la copia toma los puntos
    de la nueva distancia, atados a su t, y queda a 0,01 mm; las puntas conservan su id."""
    import numpy as np
    from scipy.spatial import cKDTree
    from omnicad.restricciones.boceto import dominio
    from omnicad.restricciones.boceto_desfase import _normales
    b = Boceto()
    madre = b.agregar_spline([(i * 30, 15 * (-1) ** i) for i in range(12)])
    copia, = b.desfase(madre, 3)
    cota = next(k for k, c in b.cotas.items() if c.tipo == "desfase")
    ts = next(r for r in b.restricciones.values() if r.tipo == "desfase").datos["parametros"]
    viejos = list(b.curvas[copia].pts)

    def densos(cid, n):
        prim = b.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        return _normales(prim, np.linspace(t0, t1, n))[0]
    for d in (4.0, 5.0, 1.0):
        assert resolver(b, {cota: d}).ok
        assert np.abs(cKDTree(densos(madre, 200000)).query(densos(copia, 3000))[0] - d).max() < 0.01
        pts = b.curvas[copia].pts
        assert (pts[0], pts[-1]) == (viejos[0], viejos[-1]) and set(ts) == {str(p) for p in pts}
        assert [ts[str(p)] for p in pts] == sorted(ts.values()) and set(pts) <= set(b.puntos)
    assert len(b.puntos) == len(b.curvas[madre].pts) + len(pts)    # los que sobraban se borraron
    medio = pts[len(pts) // 2]
    b.agregar_linea(medio, (0.0, 200.0))                             # otra cosa usa un punto del medio: no se rehace
    assert resolver(b, {cota: 4.0}).ok and b.curvas[copia].pts == pts


def test_derivada_de_la_quintica_es_la_de_diferencias_finitas():
    """P-185b: la derivada de los polos de la quíntica respecto de cada punto (abierta, cerrada y de 2 puntos) es la de
    reinterpolar con diferencias centradas (paso 1e-3: con 1e-7 el ruido de la interpolación ya es de ~1e-4)."""
    import numpy as np
    from omnicad.restricciones.boceto_geometria import interpolar_spline, sensibilidad_spline
    for cerrada, pts in ((False, [(i * 30, 15 * (-1) ** i) for i in range(12)]),
                         (True, [(0, 0), (40, 5), (50, 40), (10, 45), (-5, 20)]), (False, [(0, 0), (10, 0)])):
        polos, _nudos, _p, dP = sensibilidad_spline(pts, cerrada)
        assert np.allclose(polos, interpolar_spline(pts, 5, cerrada)[0], atol=1e-12)
        for k in range(len(pts)):
            for c in (0, 1):
                mas, menos = [list(v) for v in pts], [list(v) for v in pts]
                mas[k][c] += 1e-3
                menos[k][c] -= 1e-3
                fd = (np.array(interpolar_spline(mas, 5, cerrada)[0]) - np.array(interpolar_spline(menos, 5, cerrada)[0]))
                assert np.abs(fd / 2e-3 - dP[k, c]).max() < 1e-5


def _cambiar_cota_dos_veces(monkeypatch, sensible, falla=False):
    """La spline larga con la cota cambiada dos veces (la segunda sobre la copia ya rehecha): (madre, copia, puntos)."""
    import numpy as np
    from omnicad.restricciones import solver as S
    monkeypatch.setattr(S, "SENSIBILIDAD_SPLINES", sensible)
    if falla:
        monkeypatch.setattr(S, "sensibilidad_spline", lambda *a: 1 / 0)
    b = Boceto()
    madre = b.agregar_spline([(i * 30, 15 * (-1) ** i) for i in range(12)])
    copia, = b.desfase(madre, 3)
    cota = next(k for k, c in b.cotas.items() if c.tipo == "desfase")
    for d in (4.0, 5.0):
        assert resolver(b, {cota: d}).ok
    return [np.array([b.coords(p) for p in b.curvas[c].pts]) for c in (madre, copia)]


def test_jacobiano_con_la_derivada_de_la_madre_da_la_misma_copia(monkeypatch):
    """P-185b: el jacobiano mueve los polos de la madre con su derivada en vez de reinterpolarla en cada columna (de
    ~1 s a ~0,1 s por cambio): la madre y la copia quedan donde quedaban (a ~1e-4 mm; la madre se mueve menos). Si la
    derivada falla, se reinterpola (el camino normal) y da lo mismo que sin la vía rápida."""
    import numpy as np
    lento = _cambiar_cota_dos_veces(monkeypatch, False)
    rapido = _cambiar_cota_dos_veces(monkeypatch, True)
    fallado = _cambiar_cota_dos_veces(monkeypatch, True, falla=True)
    for a, b, c in zip(lento, rapido, fallado, strict=True):
        assert a.shape == b.shape and np.abs(a - b).max() < 1e-3
        assert np.array_equal(a, c)


def test_libres_con_qr_es_lo_de_la_svd():
    """P-185b: `_libres` con QR con pivoteo (6 ms contra 150 ms en la spline larga) marca las mismas incógnitas que la
    SVD; si el QR no confirma el rango, cae a la SVD."""
    import numpy as np
    from omnicad.restricciones import solver as S
    sis = _spline_larga_ya_modificada()
    J = S._jacobiano(sis, sis.x0)
    rango = int(np.linalg.matrix_rank(J, tol=1e-6))
    _, _, vt = np.linalg.svd(J, full_matrices=False)
    svd = 1 - np.linalg.norm(vt[:rango].T, axis=1) ** 2 > 1e-12
    qr = S._libres_qr(J, rango, 1e-6)
    assert qr is not None and svd.any() and np.array_equal(qr, svd)
    assert S._libres_qr(J, rango - 1, 1e-6) is None          # rango dudoso: la SVD
