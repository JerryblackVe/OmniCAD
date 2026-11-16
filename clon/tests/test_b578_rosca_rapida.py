# -*- coding: utf-8 -*-
"""B-578: cambiar una cota de una pieza con un agujero M10 modelado tardaba 1,67 s (Fusion 0,04, con la rosca
cosmética). La herramienta del agujero roscado se arma una vez en el origen y se traslada; las integrales de volumen se
recuerdan por forma; `_adentro` no arma el clasificador (44 ms con la rosca) si el punto cae fuera de la caja."""
import pytest

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.ui.comandos.crear import Agujero, Rosca


def _llamar(sesion, herramienta, **argumentos):
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"], resultado


def _placa_roscada():
    """Placa con empalmes (un cuerpo ya modificado) y un agujero M10 modelado, con su espesor como parámetro."""
    s = api.Sesion()
    _llamar(s, "create_parameter", name="espesor", expression="20 mm")
    _llamar(s, "create_sketch", plane="XY", name="B1")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=60, y2=40)
    _llamar(s, "extrude", sketch="B1", distance="espesor", profile=0)
    _llamar(s, "fillet", edges="|Z", radius=5)
    _llamar(s, "create_hole", face=">Z", points=[[30, 20]], thread="M10", hole_tap="modeled", depth=12)
    return s


def _volumen(s):
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    assert geo.es_valida(cuerpo.forma)
    return geo.volumen_exacto(cuerpo.forma, 1e-6)


def test_b578_cambiar_la_cota_reusa_la_rosca_y_da_lo_mismo_que_sin_atajo(monkeypatch):
    monkeypatch.setattr(aislado, "EN_HIJO", True)                      # recalcula acá, como el trabajador
    s = _placa_roscada()
    antes = sc._rosca_en_origen.cache_info().hits
    _llamar(s, "set_parameter", name="espesor", expression="26 mm")
    assert sc._rosca_en_origen.cache_info().hits > antes                  # la rosca no se volvió a armar
    rapido = _volumen(s)

    def falla(*a):
        raise RuntimeError("caché rota")
    monkeypatch.setattr(sc, "_rosca_en_origen", falla)                    # vía rápida rota: el camino de siempre
    geo._INTEGRALES.clear()
    _llamar(s, "set_parameter", name="espesor", expression="25 mm")
    _llamar(s, "set_parameter", name="espesor", expression="26 mm")
    assert _volumen(s) == pytest.approx(rapido, rel=1e-9)


def test_b578_la_rosca_trasladada_es_la_misma_que_armada_en_su_lugar():
    punto, direccion = (12.5, -3.0, 7.0), (0.0, 0.6, -0.8)
    opciones = dict(diametro=10.0, profundidad=12.0, roscado="M10", clase="6H")
    movida = sc.herramienta_agujero(punto, direccion, **opciones)
    en_su_lugar = sc._herramienta_agujero(punto, direccion, **_todas(opciones))       # sin caché
    comun = geo.booleano(movida, en_su_lugar, "intersecar")
    assert geo.volumen_exacto(comun, 1e-6) == pytest.approx(geo.volumen_exacto(en_su_lugar, 1e-6), rel=1e-6)


def _todas(opciones):
    """Las opciones de `herramienta_agujero` con sus valores por defecto, para llamar a la versión sin caché."""
    import inspect
    firma = inspect.signature(sc.herramienta_agujero).parameters
    return {k: opciones.get(k, p.default) for k, p in firma.items() if k not in ("punto", "direccion")}


def test_b578_la_integral_recordada_se_rehace_si_la_forma_cambia_de_hijos():
    caja = geo.caja(10, 10, 10)
    assert geo.volumen_exacto(caja) == pytest.approx(1000)
    geo._INTEGRALES[(caja, geo.BRepGProp.VolumeProperties_s, None)] = (caja.NbChildren() + 1, -1.0)   # vieja
    assert geo.volumen_exacto(caja) == pytest.approx(1000)


def test_b578_adentro_sigue_viendo_lo_contenido_y_saltea_lo_lejano():
    grande, chica = geo.caja(20, 20, 20), geo.caja(2, 2, 2, origen=(9, 9, 9))
    assert geo._adentro(grande, chica, 1e-6) and geo.se_tocan(grande, chica)
    assert not geo._adentro(grande, geo.caja(2, 2, 2, origen=(50, 0, 0)), 1e-6)


def test_b578_la_rosca_sale_cosmetica_por_defecto_como_en_fusion():
    """Fusion: «Select Modeled to show the thread as fully modeled» (Thread, paso 8): sin marcarla, es cosmética."""
    from omnicad.ui.comando import ContextoComando
    ctx = ContextoComando(api.Sesion().doc)

    def defecto(comando, clave):
        return next(c.defecto for c in comando.campos(ctx) if c.clave == clave)
    assert defecto(Rosca(), "modelada") is False
    assert defecto(Agujero(), "rosca_modelada") is False
