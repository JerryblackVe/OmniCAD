"""B-195: cinco Bézier del cruce de ZAI, sin archivos externos ni datos del Escritorio."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles


# Polos en mm de las curvas 235, 239, 243, 1803 y 1807; ningún subconjunto reproduce el fallo.
POLOS = (
    ((15.695203504146628, 14.426865418255742), (15.641798708900266, 14.090393941983574),
     (15.473562970764183, 13.922164849541273), (15.190502935432155, 13.922164849541273)),
    ((15.190502935432155, 13.922164849541273), (15.069006361677312, 13.922164849541273),
     (14.807305586166313, 14.062355759909858), (14.405420545980519, 14.342744226340809)),
    ((14.405420545980519, 14.342744226340809), (13.900719977266048, 14.361438562954548),
     (13.648369692908812, 14.174515133898508), (13.648369692908812, 13.781967293478905)),
    ((15.692459442274343, 14.474612533877734), (15.696985909794753, 14.362382004900315),
     (15.57446090039949, 13.655709895614287), (14.883489167027104, 14.038416258082574)),
    ((14.883489167027104, 14.038416258082574), (14.457820161407977, 14.274180552074087),
     (14.469226859559402, 14.430667000636749), (14.000517614203371, 14.296399041217116)),
)


def curvas():
    return [("spline", i + 1, polos, (0., 0., 0., 0., 1., 1., 1., 1.), 3, None)
            for i, polos in enumerate(POLOS)]


@pytest.mark.parametrize("detectar", [perfiles._detectar_occ, perfiles.detectar])
def test_b195_el_cruce_casi_tangente_entrega_solo_caras_validas(detectar, monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    regiones = detectar(curvas(), geo.Plano("XY"))
    assert regiones
    # No alcanza con descartar la cara mala: las otras dos juntas no llegan a esta área.
    assert sum(p.area for p in regiones) > 0.0027
    assert all(geo.es_valida(p.cara) for p in regiones), [(p.area, sorted(p.firma)) for p in regiones]
    for p in regiones:
        assert p.area > 0
        assert geo.area(p.cara) == pytest.approx(p.area, abs=1e-10)
    solido = geo.extruir([p.cara for p in regiones], (0., 0., 1.), 2.)
    assert geo.es_valida(solido)
    assert geo.volumen(solido) == pytest.approx(sum(p.area for p in regiones) * 2, abs=1e-8)


def rectangulo(i, x, y, ancho, alto, hueco=0.):
    return [("linea", i, (x, y), (x + ancho, y)),
            ("linea", i + 1, (x + ancho, y + hueco), (x + ancho, y + alto)),
            ("linea", i + 2, (x + ancho, y + alto), (x, y + alto)),
            ("linea", i + 3, (x, y + alto), (x, y))]


@pytest.mark.parametrize("plano", ["XY", "XZ", "YZ"])
def test_b195_reparar_el_cruce_conserva_los_cierres_difusos(plano, monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_RUST", "1")
    regiones = perfiles.detectar(curvas() + rectangulo(10, 40., 0., 2., 3., 5e-5), geo.Plano(plano))
    assert all(geo.es_valida(p.cara) for p in regiones)
    cierre = [p for p in regiones if p.firma == {10, 11, 12, 13}]
    assert len(cierre) == 1
    assert cierre[0].area == pytest.approx(6., abs=1e-4)
    assert sum(p.area for p in regiones if p not in cierre) > 0.0027


def test_b195_segundo_cruce_del_zai_entre_curvas_casi_paralelas():
    # Curvas originales 145 y 1598: EdgeEdge no encuentra su cruce ni con difusa cero.
    polos = (
        ((4.896256807437824, 11.558896328789348), (4.896256807437824, 11.704430376960085),
         (4.927637773484776, 11.865987192843482), (4.9903864141911125, 12.043566776439544)),
        ((5.100913427450964, 11.179732161951348), (4.830670383718289, 11.260561939101484),
         (4.904231947307084, 11.672315290286445), (4.909353321987316, 11.730176477961596)),
    )
    primitivas = [("spline", i + 1, ps, (0., 0., 0., 0., 1., 1., 1., 1.), 3, None)
                  for i, ps in enumerate(polos)]
    regiones = perfiles._detectar_occ(primitivas + rectangulo(10, 3., 10., 4., 4.), geo.Plano("XY"))
    assert regiones
    assert all(geo.es_valida(p.cara) for p in regiones)
    assert sum(p.area for p in regiones) == pytest.approx(16., abs=1e-8)


def test_b195_si_el_cruce_no_se_puede_partir_no_entrega_caras_invalidas(monkeypatch):
    """La región irreparable no se ofrece (como Fusion), sin hacer fallar el boceto entero: un boceto de ajuste a malla
    con curvas superpuestas a propósito (test_boceto_fase8_malla) tiene que seguir recalculando."""
    monkeypatch.setattr(perfiles, "_partir_cruces", lambda caras, aristas: aristas)
    salida = perfiles._detectar_occ(curvas(), geo.Plano("XY"))
    assert all(geo.es_valida(p.cara) for p in salida)
