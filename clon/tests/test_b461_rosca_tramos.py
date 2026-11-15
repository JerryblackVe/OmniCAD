"""B-461: la rosca modelada exterior a derechas sin torneado se arma sin booleana helicoidal (`_rosca_directa`); las
demás cortan el surco partido en tramos (`_en_tramos`). Las dos dan la misma geometría que el recorte de siempre sobre
un cuerpo ya modificado, y si la vía rápida falla cae sola al recorte de siempre."""
import pytest
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _cuerpo(modificacion):
    sesion = api.Sesion()
    pasos = [("create_cylinder", {"radius": 5, "height": 30})]
    if modificacion == "chaflanado":
        pasos.append(("chamfer", {"edges": ">Z", "distance": 1}))
    else:
        pasos.append(("create_box", {"length": 24, "width": 18, "height": 3, "x": 2, "z": -3, "operation": "join"}))
    for herramienta, argumentos in pasos:
        resultado = api.llamar(sesion, herramienta, argumentos)
        assert resultado["ok"], resultado
    (cuerpo,) = sesion.doc.estado_final.cuerpos.values()
    return cuerpo.forma


def _roscar(forma, clase=""):
    sc._surco_en_origen.cache_clear()
    return sc.rosca(forma, None, designacion="M10x1.5", clase=clase)


@pytest.mark.parametrize("modificacion", ["chaflanado", "unido_a_base"])
def test_b461_tramos_da_lo_mismo_que_el_recorte_normal(monkeypatch, modificacion):
    forma = _cuerpo(modificacion)
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)
    usados, original = [], sc._en_tramos
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: usados.append(1) or original(*a))
    rapida = _roscar(forma)
    assert usados, "M10×30 (20 vueltas) tiene que ir por la vía rápida"
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: None)
    normal = _roscar(forma)
    assert geo.es_valida(rapida)
    assert geo.volumen_exacto(rapida, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-6)
    assert len(geo.caras(rapida)) == len(geo.caras(normal))     # las caras partidas se vuelven a juntar


def test_b461_si_la_via_rapida_sale_mal_cae_al_recorte_normal(monkeypatch):
    forma = _cuerpo("chaflanado")
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: None)
    normal = _roscar(forma)
    monkeypatch.setattr(sc, "_en_tramos", lambda *a: geo.cilindro(1, 1))     # volumen equivocado: se descarta
    rota = _roscar(forma)
    assert geo.es_valida(rota)
    assert geo.volumen_exacto(rota, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-9)


def _adentro(forma, puntos):
    return [BRepClass3d_SolidClassifier(forma, gp_Pnt(*q), 1e-7).State() for q in puntos]


def _misma_fase(a, b, puntos):
    """Puntos entre fondo y cresta: con la fase corrida difieren ~70 %; uno pegado a un flanco puede caer distinto (los
    flancos difieren ~1e-5 mm entre la varilla y el barrido)."""
    distintos = sum(x != y for x, y in zip(_adentro(a, puntos), _adentro(b, puntos), strict=True))
    assert distintos <= len(puntos) // 50, f"{distintos} de {len(puntos)} puntos de prueba distintos"


@pytest.mark.parametrize("modificacion, clase", [("chaflanado", ""), ("unido_a_base", "6g")])   # 6g: tornea la cresta
def test_b461_la_rosca_directa_da_lo_mismo_que_el_corte(monkeypatch, modificacion, clase):
    forma = _cuerpo(modificacion)
    salidas, original = [], sc._rosca_directa
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: salidas.append(original(*a)) or salidas[-1])
    directa = _roscar(forma, clase)
    assert salidas and salidas[0] is not None, "M10 exterior a derechas va sin booleana helicoidal"
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)
    normal = _roscar(forma, clase)
    assert geo.es_valida(directa)
    assert len(geo.solidos(directa)) == 1
    assert geo.volumen_exacto(directa, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=2e-5)
    # la misma fase (B-79: tornillo y tuerca encajan): puntos entre fondo y cresta, dentro o fuera en las dos
    puntos = [(4.6 * c, 4.6 * s, z / 4) for z in range(2, 116, 3) for c, s in ((1, 0), (0, 1), (-1, 0), (0, -1))]
    _misma_fase(directa, normal, puntos)


def test_b461_si_la_rosca_directa_sale_mal_cae_al_corte(monkeypatch):
    forma = _cuerpo("unido_a_base")
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)
    normal = _roscar(forma)
    monkeypatch.undo()
    monkeypatch.setattr(sc, "_varilla_roscada", lambda *a: geo.cilindro(5, 30))     # válida, sin surco: se descarta
    rota = _roscar(forma)
    assert geo.es_valida(rota)
    assert geo.volumen_exacto(rota, 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-9)
    monkeypatch.setattr(sc, "_varilla_roscada", lambda *a: 1 / 0)                  # error del kernel: tampoco se ve
    assert geo.volumen_exacto(_roscar(forma), 1e-6) == pytest.approx(geo.volumen_exacto(normal, 1e-6), rel=1e-9)


def test_b461_la_rosca_directa_conserva_la_fase_con_el_eje_al_reves(monkeypatch):
    forma = geo.cilindro(4, 15, base=(3, 2, 1), eje=(-1, 0, 0))     # eje −X: `_fase_rosca` da media vuelta
    # con 6g: sin clase el corte de siempre falla a 0° y su respaldo de 229° corre la fase (B-499)
    sc._surco_en_origen.cache_clear()
    directa = sc.rosca(forma, None, designacion="M8x1.25", clase="6g")
    assert len(geo.caras(directa)) > 30, "tiene que salir por la rosca directa (el corte de siempre da 18 caras)"
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)
    sc._surco_en_origen.cache_clear()
    normal = sc.rosca(forma, None, designacion="M8x1.25", clase="6g")
    puntos = [(3 - x / 4, 2 + 3.7 * c, 1 + 3.7 * s) for x in range(2, 58, 3) for c, s in ((1, 0), (0, 1), (-1, 0), (0, -1))]
    _misma_fase(directa, normal, puntos)


def test_b461_la_previa_marca_crestas_y_no_el_fondo():
    """`caras_sobre_cilindro`: en el tornillo directo, la cresta sin el fondo; en un agujero, sus crestas de adentro."""
    eje = geo.cilindro(5, 20)
    cara = sc._caras_cilindricas(eje)[0]
    radios = {round(sc._radio_cilindro(c), 3) for c in sc.caras_sobre_cilindro(sc.rosca(eje, cara, designacion="M10", clase="6g"), cara)}
    assert radios == {4.925}
    pieza = geo.booleano(geo.cilindro(15, 12), geo.cilindro(4.25, 12), "cortar")
    agujero = next(c for c in sc._caras_cilindricas(pieza) if abs(sc._radio_cilindro(c) - 4.25) < 1e-6)
    assert sc.caras_sobre_cilindro(sc.rosca(pieza, agujero, designacion="M10", clase=""), agujero)
