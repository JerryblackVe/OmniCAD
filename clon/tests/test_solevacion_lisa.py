"""B-845: solevaciones entre perfiles lisos, con una pared continua que admite desfases."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeWire
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Elips, gp_Pnt

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import solidos_crear_solevacion as sl
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import superficies as sf

ALTO = 85.34
VOLUMEN_TINA_ANTERIOR = 420763.8117431697


def _alambre(aristas):
    mk = BRepBuilderAPI_MakeWire()
    for arista in aristas:
        mk.Add(arista)
    assert mk.IsDone()
    return mk.Wire()


def _circulo(radio, z):
    eje = gp_Ax2(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1))
    return _alambre([BRepBuilderAPI_MakeEdge(gp_Circ(eje, radio)).Edge()])


def _elipse(z):
    eje = gp_Ax2(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1))
    return _alambre([BRepBuilderAPI_MakeEdge(gp_Elips(eje, 35, 20)).Edge()])


def _ranura(z):
    """Contorno de draw_slot center_to_center, en sentido horario para cubrir también la orientación inversa."""
    p = [gp_Pnt(-55, 25, z), gp_Pnt(55, 25, z), gp_Pnt(55, -25, z), gp_Pnt(-55, -25, z)]
    return _alambre([
        BRepBuilderAPI_MakeEdge(p[0], p[1]).Edge(),
        BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p[1], gp_Pnt(80, 0, z), p[2]).Value()).Edge(),
        BRepBuilderAPI_MakeEdge(p[2], p[3]).Edge(),
        BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p[3], gp_Pnt(-80, 0, z), p[0]).Value()).Edge(),
    ])


def _redondeado(z):
    """Rectángulo 80 × 40 con cuatro empalmes R8."""
    p = [(-32, -20, z), (32, -20, z), (40, -12, z), (40, 12, z),
         (32, 20, z), (-32, 20, z), (-40, 12, z), (-40, -12, z)]
    medios = [(37.656854, -17.656854), (37.656854, 17.656854),
              (-37.656854, 17.656854), (-37.656854, -17.656854)]
    aristas = []
    for i in range(4):
        j = 2 * i
        a, b, c = p[j], p[(j + 1) % 8], p[(j + 2) % 8]
        aristas += [BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge(),
                    BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*b), gp_Pnt(*medios[i], z), gp_Pnt(*c)).Value()).Edge()]
    return _alambre(aristas)


def _rectangulo(z):
    mk = BRepBuilderAPI_MakePolygon()
    for p in [(-40, -20, z), (40, -20, z), (40, 20, z), (-40, 20, z)]:
        mk.Add(gp_Pnt(*p))
    mk.Close()
    return mk.Wire()


def _tapa(forma):
    z = geo.caja_envolvente(forma)[1][2]
    return next(c for c in geo.caras(forma) if geo.plano_de_cara(c) is not None
                and abs(geo.centro_masa(c, superficie=True)[2] - z) < 1e-3)


def _comprobar_vaciado(forma, espesor=1.0):
    hueco = sm.vaciado(forma, [_tapa(forma)], espesor_interior=espesor)
    assert geo.es_valida(hueco)
    assert len(geo.solidos(hueco)) == 1
    assert 0 < geo.volumen_exacto(hueco) < geo.volumen_exacto(forma)
    return hueco


@pytest.fixture(scope="module")
def tina():
    return sc.solevar([_circulo(30, 0), _ranura(ALTO)])


def test_tina_tiene_una_cara_lateral_y_conserva_el_perfil(tina):
    assert geo.es_valida(tina)
    assert len(geo.caras(tina)) == 3                    # dos tapas y UNA pared lateral
    assert geo.volumen_exacto(tina) == pytest.approx(VOLUMEN_TINA_ANTERIOR, rel=0.005)
    tapa = _tapa(tina)
    assert geo.area(tapa) == pytest.approx(110 * 50 + 25**2 * 3.141592653589793, rel=0.005)
    minimo, maximo = geo.caja_envolvente(tapa)
    assert minimo == pytest.approx([-80, -25, ALTO], rel=0.005, abs=1e-3)
    assert maximo == pytest.approx([80, 25, ALTO], rel=0.005, abs=1e-3)


@pytest.mark.parametrize("espesor", [0.5, 1.0, 2.0])
def test_tina_se_vacia(tina, espesor):
    _comprobar_vaciado(tina, espesor)


def test_la_tapa_de_la_tina_se_desfasa(tina):
    desplazada = sm.desfasar_caras(tina, [_tapa(tina)], 0.1, tangente=False)
    assert geo.es_valida(desplazada) and len(geo.solidos(desplazada)) == 1
    assert geo.volumen_exacto(desplazada) > geo.volumen_exacto(tina)


def test_ranura_a_circulo_tambien_es_lisa_y_vaciable():
    forma = sc.solevar([_ranura(0), _circulo(30, ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 3
    assert geo.volumen_exacto(forma) == pytest.approx(VOLUMEN_TINA_ANTERIOR, rel=0.005)
    _comprobar_vaciado(forma)


def test_rectangulo_redondeado_a_circulo_no_se_deforma_y_se_vacia():
    forma = sc.solevar([_redondeado(0), _circulo(30, ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 4
    assert geo.volumen_exacto(forma) == pytest.approx(254527.427438, rel=0.005)
    _comprobar_vaciado(forma)


def test_circulo_a_elipse_no_cambia():
    forma = sc.solevar([_circulo(30, 0), _elipse(ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 3
    assert geo.volumen_exacto(forma) == pytest.approx(216717.010151, rel=1e-8)
    _comprobar_vaciado(forma)


def test_tres_secciones_sin_variante_que_reproduzca_queda_como_antes():
    """La lisa de 3 secciones difiere +2,97 % del camino anterior: la guarda la rechaza y queda el loft
    de siempre (con sus pliegues; arreglarlo exige una variante que reproduzca el volumen)."""
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO), _circulo(25, 2 * ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 7
    assert geo.volumen_exacto(forma) == pytest.approx(949304.751664, rel=1e-6)


def test_reglada_tambien_usa_la_pared_lisa():
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO)], reglada=True)
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 3
    assert geo.volumen_exacto(forma) == pytest.approx(VOLUMEN_TINA_ANTERIOR, rel=0.005)
    _comprobar_vaciado(forma)


def test_cerrada_sin_variante_que_reproduzca_queda_como_antes():
    """La cerrada lisa perdía un 22 % del volumen (torcida): la guarda la rechaza."""
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO), _circulo(30, 2 * ALTO)], cerrada=True)
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    assert len(geo.caras(forma)) == 5
    assert geo.volumen_exacto(forma) == pytest.approx(795382.409253, rel=1e-6)


@pytest.mark.parametrize("extremo,esperado", [("condicion_inicio", 342214.179504),
                                              ("condicion_fin", 510135.737459)])
def test_condiciones_sin_variante_que_reproduzca_quedan_como_antes(extremo, esperado):
    """B-243: la seta con condición no puede cambiar de volumen (la lisa daba −1,5 % y +4,1 %)."""
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO)],
                       **{extremo: {"tipo": "direccion", "angulo": 0, "peso": 1}})
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 7
    assert geo.volumen_exacto(forma) == pytest.approx(esperado, rel=1e-6)


def test_rectangulo_con_esquinas_vivas_sigue_el_camino_anterior():
    forma = sc.solevar([_rectangulo(0), _circulo(30, ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 7
    assert geo.volumen_exacto(forma) == pytest.approx(259541.025785, rel=1e-8)


def test_si_la_conversion_falla_devuelve_el_loft_anterior(monkeypatch):
    monkeypatch.setattr(sl, "_una_arista_lisa", lambda _w: None)
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO)])
    assert geo.es_valida(forma) and len(geo.caras(forma)) == 7
    assert geo.volumen_exacto(forma) == pytest.approx(VOLUMEN_TINA_ANTERIOR, rel=1e-8)


def test_superficie_lisa_se_desfasa():
    lamina = sc.solevar([_circulo(30, 0), _ranura(ALTO)], solido=False)
    assert geo.es_valida(lamina) and len(geo.caras(lamina)) == 1
    desfasada = sf.desfasar_superficie(lamina, 0.1)
    assert geo.es_valida(desfasada) and geo.area(desfasada) > 0


def test_superficie_lisa_engrosa_1_mm_la_rechaza_la_compuerta():
    """B-846 (medido 24/11, con la compuerta honesta de B-853): engrosar 1 mm esta lámina daba «válido y exacto»
    solo porque el análisis (21 s) no llegaba al tope de 5 s y aprobaba en silencio; ahora cuenta 1 autointersección
    de CARA que crea el offset aproximado del kernel (la lámina sola tiene 0). Decide B-846 si hay que aceptarlo."""
    lamina = sc.solevar([_circulo(30, 0), _ranura(ALTO)], solido=False)
    # 2 mm (B-846) no sale: el kernel deja la cara desfasada a 1,75 mm y `_desfase_imposible` lo rechaza
    # (antes la previa colgaba 300 s con el lateral de 5 caras); con 1 mm queda a 1,00 mm exacto.
    with pytest.raises(geo.ErrorGeometria, match="probá menos espesor"):
        sf.engrosar_superficie(lamina, 1.0)
