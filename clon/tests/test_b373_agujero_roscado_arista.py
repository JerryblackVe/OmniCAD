"""B-373: un agujero con rosca modelada no queda con una arista de más de dos caras: se prueba otro margen del surco."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _agujero(rosca):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 14})["ok"]
    r = api.llamar(s, "create_hole", {"face": ">Z", "depth": 10, "hole_tap": "modeled", "thread": rosca})
    return s, r


def test_acme_de_media_pulgada_a_10_mm_queda_sin_pellizcos_ni_error():
    """El caso de la fila: con el primer margen el corte sumaba una arista no manifold (en Linux)."""
    s, r = _agujero("1/2-10 ACME")
    assert r["ok"], r
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and geo._aristas_defectuosas(forma)[1] == 0
    assert 20000 < geo.volumen(forma) < 22400


def test_si_el_primer_margen_deja_un_pellizco_se_deshace_y_se_prueba_otro(monkeypatch):
    s0, r0 = _agujero("M6")
    assert r0["ok"]
    volumen = geo.volumen(next(iter(s0.doc.estado_final.cuerpos.values())).forma)
    llamadas, real = [], sc.agujero_sin_pellizco

    def primera_vez_mal(antes, despues):
        llamadas.append(len(despues))
        return len(llamadas) > 1 and real(antes, despues)
    monkeypatch.setattr(sc, "agujero_sin_pellizco", primera_vez_mal)
    s, r = _agujero("M6")
    assert r["ok"], r
    assert len(llamadas) == 3     # el primer corte se deshizo (1), el segundo valió (2) y la guarda final lo confirma (3)
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1 and len(s.doc.operaciones) == 2             # sin cuerpos ni pasos de más
    assert geo.volumen(cuerpos[0].forma) == pytest.approx(volumen, rel=2e-3)


def test_si_ningun_margen_sale_limpio_el_error_sigue_siendo_el_de_la_guarda(monkeypatch):
    monkeypatch.setattr(sc, "agujero_sin_pellizco", lambda antes, despues: False)
    s, r = _agujero("M6")
    assert not r["ok"] and "espesor cero" in r["mensaje"], r
    assert len(s.doc.estado_final.cuerpos) == 1
