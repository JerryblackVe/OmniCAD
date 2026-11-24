"""B-853: el veredicto de autointersecciones del Engrosar no puede depender del estado térmico del trabajador.

La banda de `engrosar_banda` del loft rectángulo → círculo (B-633) analiza en 6–10 s: con el plazo de 5 s de la
compuerta el análisis nunca llegaba, ni frío ni caliente, y el «ok» salía de un plazo agotado cuyo aviso se perdía
(en el árbol sin la copia de B-850 llegaba a contar 190 y el MISMO Engrosar fallaba). La costura está sana: con la
geometría limpia el conteo es 0 (medido 24/11, plazo 60 s)."""
from unittest.mock import patch

from omnicad import api
from omnicad.nucleo import aislado, revision

from test_b_633_repro import _pieza


def _engrosar(s, cid):
    return api.llamar(s, "thicken", {"faces": cid, "thickness": 2})


def test_frio_sin_analisis_no_aprueba_en_silencio():
    """Frío: si el análisis no llega, el Engrosar no da por bueno lo que no revisó (antes aprobaba en silencio)."""
    def agotado(*args, **kwargs):
        raise aislado.TiempoAgotado("plazo agotado")

    s, cid = _pieza(superficie=True)
    with patch.object(aislado, "correr", side_effect=agotado), patch.object(revision, "_AGOTADAS", {}):
        r = _engrosar(s, cid)
    assert not r["ok"] and "comprobar" in r["mensaje"], r


def test_caliente_el_veredicto_sale_de_un_analisis_que_llego():
    """Caliente, como en la fila: un loft sólido revisado antes calienta el trabajador y el MISMO Engrosar tiene que
    dar «ok» por un conteo que terminó, no por un plazo agotado. La compuerta le da al análisis el plazo de una
    vista previa (≥ 30 s: la banda necesita 6–10 s)."""
    real = revision._autointersecciones_seguras
    plazos, completos = [], []

    def espia(forma, limite, plazo):
        plazos.append(plazo)
        cantidad, problemas, completo = real(forma, limite, plazo)
        completos.append(completo)
        return cantidad, problemas, completo

    _pieza(superficie=False)                    # calienta el trabajador, como en la fila
    s, cid = _pieza(superficie=True)
    with patch.object(revision, "_autointersecciones_seguras", side_effect=espia):
        r = _engrosar(s, cid)
    assert r["ok"], r.get("mensaje", r)
    assert completos and any(completos), "el análisis del engrosado no llegó a terminar"
    assert max(plazos) >= 30.0, plazos
