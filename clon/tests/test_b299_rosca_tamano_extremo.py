"""B-299: los tamaños extremos de Rosca fallan con una explicación útil (qué probar) en vez de un mensaje del kernel."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _cilindro(diametro=10, alto=10):
    sesion = api.Sesion()
    resultado = api.llamar(sesion, "create_cylinder", {"diameter": diametro, "height": alto})
    assert resultado["ok"], resultado
    return sesion


def test_tamano_extremo_dice_que_probar_y_no_cambia_el_documento():
    sesion = _cilindro()
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": "ANSI M0.3x0.08", "modeled": True})
    assert not resultado["ok"] and resultado["error_kind"] == "OPERATION_FAILED", resultado
    assert "otro tamaño" in resultado["mensaje"] and "cosmética" in resultado["mensaje"], resultado
    assert sesion.doc.a_dict() == antes


@pytest.mark.parametrize("diametro, alto, designacion, texto", [
    (0.3, 25, "ANSI M0.3x0.08", "312.5 vueltas"),
    (10, 1, "M10", "paso de la rosca (1.5 mm) supera el largo roscado (1 mm)"),
])
def test_extremos_se_rechazan_antes_de_armar_el_perfil(monkeypatch, diametro, alto, designacion, texto):
    sesion = _cilindro(diametro, alto)
    llamadas = []

    def perfil_prohibido(*_args):
        llamadas.append(True)
        raise AssertionError("No debe empezar a modelar una rosca extrema.")

    monkeypatch.setattr(sc, "_perfil_clase", perfil_prohibido)
    resultado = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": designacion, "modeled": True})
    assert not resultado["ok"] and texto in resultado["mensaje"], resultado
    assert not llamadas


def test_m10_normal_conserva_el_volumen_modelado():
    sesion = _cilindro()
    resultado = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": "M10", "modeled": True})
    assert resultado["ok"], resultado
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    # Volumen medido por la API antes del arreglo, con la clase automática 6g.
    assert geo.volumen_exacto(forma, 1e-6) == pytest.approx(639.1261063312793, abs=1e-3)


def test_una_cara_mucho_mas_gruesa_se_sigue_torneando():
    """B-247: M10 sobre Ø30 andaba antes de B-299 (se tornea a la cresta); el arreglo no la rechaza."""
    sesion = _cilindro(30, 12)
    resultado = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": "M10", "modeled": True})
    assert resultado["ok"], resultado


def test_la_cosmetica_admite_el_tamano_extremo_y_muchas_vueltas():
    sesion = _cilindro(alto=30)
    resultado = api.llamar(sesion, "create_thread", {"faces": "%CYLINDER", "thread": "ANSI M0.3x0.08", "modeled": False})
    assert resultado["ok"], resultado
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(math.pi * 25 * 30)
