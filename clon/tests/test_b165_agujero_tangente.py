"""B-165: un agujero tangente a las paredes. Si deja un cuerpo pellizcado (material de espesor cero, aristas
compartidas por más de dos caras) el paso da un error claro; si parte el cuerpo en piezas que solo se tocan en una
línea, cada pieza es un cuerpo válido y sale un aviso. Nunca borra el cuerpo ni lo deja no manifold en silencio."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _agujero(caja, diametro, cara=">Z"):
    s = api.Sesion()
    assert api.llamar(s, "create_box", dict(zip(("length", "width", "height"), caja, strict=True)))["ok"]
    return s, api.llamar(s, "create_hole", {"face": cara, "diameter": diametro, "depth": 60})


def _formas(s):
    return [c.forma for c in s.doc.estado_final.cuerpos.values()]


def _quitado(radio, h, alto):
    """Volumen que un cilindro de `radio` quita de una franja |y| ≤ h (círculo cortado por dos rectas)."""
    return 2 * (h * math.sqrt(radio**2 - h**2) + radio**2 * math.asin(h / radio)) * alto


def test_agujero_que_pellizca_un_cuerpo_da_error_claro():
    s, r = _agujero((80, 60, 40), 60, "Cuerpo1/F5")           # el caso del cazador: tangente a las paredes y = ±30
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED"
    assert "espesor cero" in r["mensaje"]
    assert len(s.doc.operaciones) == 1                       # el documento no cambió


def test_agujero_tangente_que_parte_la_caja_deja_las_cuatro_esquinas():
    s, r = _agujero((60, 40, 20), 60)                        # antes borraba la caja entera
    assert r["ok"], r
    formas = _formas(s)
    assert all(geo.es_valida(f) and geo._aristas_defectuosas(f) == (0, 0) for f in formas)
    assert any("aristas compartidas" in a for a in r.get("avisos") or [])
    # El reintento que gana pasa la herramienta a B-spline: 1,2 mm³ de 3841 (0,03 %).
    assert sum(map(geo.volumen_exacto, formas)) == pytest.approx(60 * 40 * 20 - _quitado(30, 20, 20), rel=1e-3)


@pytest.mark.parametrize("caja, cara, quitado", [((60, 40, 20), ">Z", _quitado(29.95, 20, 20)),
                                                  ((80, 60, 40), "Cuerpo1/F5", math.pi * 29.95**2 * 40)])
def test_agujero_apenas_mas_chico_sigue_andando(caja, cara, quitado):
    s, r = _agujero(caja, 59.9, cara)
    assert r["ok"] and not r.get("avisos"), r
    formas = _formas(s)
    assert all(geo.es_valida(f) and geo._aristas_defectuosas(f) == (0, 0) for f in formas)
    assert sum(map(geo.volumen_exacto, formas)) == pytest.approx(math.prod(caja) - quitado, abs=1e-3)
