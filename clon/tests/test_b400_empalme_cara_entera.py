"""B-400: un empalme de radio constante igual al alto de la cara vecina (caja 40 × 30 × 20, arista de arriba, 20 mm)
se rechazaba con «se come justo una cara vecina». Fusion lo hace: la cara lateral desaparece y queda un cuarto de
cilindro hasta la arista de abajo (captura `evidencias/fusion_capturas_2026-11-12/2b_tras_Medir_valor_20mm_en_la_caja.jpg`)."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm

VOLUMEN = 40 * 30 * 20 - (20 * 20 - math.pi * 20 * 20 / 4) * 40       # caja menos la esquina del cuarto de cilindro


def _arista(forma, medio):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    for e in geo._aristas_unicas(forma):
        c = BRepAdaptor_Curve(e)
        p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
        if abs(p.X() - medio[0]) + abs(p.Y() - medio[1]) + abs(p.Z() - medio[2]) < 1e-6:
            return e
    raise AssertionError(f"no hay arista con el medio en {medio}")


def test_radio_igual_al_alto_se_come_la_cara_como_fusion():
    caja = geo.caja(40, 30, 20)
    forma = sm.empalme(caja, [{"aristas": [_arista(caja, (20, 0, 20))], "tipo": "constante", "radio": 20}])
    assert geo.volumen(forma) == pytest.approx(VOLUMEN, abs=1e-3)
    assert geo.es_valida(forma)
    assert len(geo.caras(forma)) == 6                     # la cara de adelante desapareció


def test_por_la_api_como_un_agente():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    forma = s.cuerpo("Cuerpo1").forma
    from omnicad.api import selectores
    (x0, y0, _), (x1, _, z1) = geo.caja_envolvente(forma)
    arriba = _arista(forma, ((x0 + x1) / 2, y0, z1))         # la de 40 mm de arriba, sobre la cara de 20 de alto
    nombre = next(f"Cuerpo1/E{e.i}" for e in selectores.listar(forma, "arista") if e.sub.IsSame(arriba))
    r = api.llamar(s, "fillet", {"body": "Cuerpo1", "edges": [nombre], "radius": 20})
    assert r["ok"], r
    assert r["result"]["bodies_modified"][0]["volume"] == pytest.approx(VOLUMEN, abs=1e-3)


def test_mas_grande_que_la_cara_sigue_dando_error():
    caja = geo.caja(40, 30, 20)
    with pytest.raises(geo.ErrorGeometria):
        sm.empalme(caja, [{"aristas": [_arista(caja, (20, 0, 20))], "tipo": "constante", "radio": 20.5}])


def test_dos_aristas_con_vertice_comun_siguen_con_el_error_claro():
    caja = geo.caja(40, 30, 20)
    aristas = [_arista(caja, (20, 0, 20)), _arista(caja, (0, 15, 20))]
    with pytest.raises(geo.ErrorGeometria, match="se come justo"):
        sm.empalme(caja, [{"aristas": aristas, "tipo": "constante", "radio": 20}])
