"""B-855: el conteo que no llega NO rechaza una operación válida (principio de Gerardo, 24/11).

Gemelos de B-853 (Engrosar). Primera vuelta: el desfase de superficie, el «¿agregó cruces?» del
empalme/chaflán y la solevación (`_plegada`, el chequeo de condiciones y el de `_loft_liso`)
pasaron a rechazar con «no se pudo comprobar» cuando el análisis no llegaba en su plazo. Regresión
medida 24/11: la zona de una rosca tarda 19,5 s con n=0 y el desfase de su cara plana sale en
0,13 s → una operación VÁLIDA fallaba solo porque la compuerta no llegó a contar (test_b306 rojo).
Segunda vuelta: no llegó → no se rechaza (como antes de B-855) y, donde hay lista de avisos, queda
el aviso de 1 renglón de siempre, igual frío y caliente; se rechaza solo si el conteo SÍ llegó y
cruza más.

El VACIADO revisa solo las caras nuevas por malla y BVH (B-855, medido 24/11): la tina lisa tarda ~1,1 s
en esa revisión y sigue rechazando cruces. Si la malla falla, queda el BOP anterior; si éste no llega,
no rechaza y deja un aviso de un renglón."""
import time
from unittest.mock import patch

import pytest

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo, revision
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import superficies as sf
from test_b173_solevacion_plegada import _secciones
from test_b_633_repro import _pieza
from test_solevacion_lisa import ALTO, _circulo, _ranura


def _sin_llegar():
    """El análisis de verdad con un plazo que no alcanza: «no llegó a contar», como frío en una pieza densa."""
    real = revision._autointersecciones_seguras

    def espia(forma, limite, plazo):
        return real(forma, limite, 0.001)

    return patch.object(revision, "_autointersecciones_seguras", espia)


def _alambre_circulo(centro, normal, radio):
    mk = BRepBuilderAPI_MakeWire()
    mk.Add(BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*centro), gp_Dir(*normal)), radio)).Edge())
    assert mk.IsDone()
    return mk.Wire()


def test_desfase_sin_analisis_no_rechaza_la_pieza_valida():
    """Frío: el desfase de la tina lisa NO se rechaza porque el conteo no llegó; queda el aviso de siempre."""
    lamina = sc.solevar([_circulo(30, 0), _ranura(ALTO)], solido=False)
    avisos = []
    with _sin_llegar():
        desfasada = sf.desfasar_superficie(lamina, 0.1, avisos=avisos)
    assert geo.es_valida(desfasada)
    assert avisos and "No se revisaron" in avisos[0]


def test_empalme_sin_analisis_no_rechaza_la_pieza_valida():
    """Frío: el empalme de la tina NO se rechaza porque el conteo no llegó; queda el aviso de siempre."""
    tina = sc.solevar([_circulo(30, 0), _ranura(ALTO)])
    e_abajo = max((e for e in geo._aristas_unicas(tina) if geo.caja_envolvente(e)[1][2] < 1e-6),
                  key=geo.longitud)
    avisos = []
    with _sin_llegar():
        empalmada = sm.empalme(tina, [{"aristas": [e_abajo], "tipo": "constante", "radio": 2.0}], avisos=avisos)
    assert geo.es_valida(empalmada)
    assert avisos and "No se revisaron" in avisos[0]


def test_comparar_con_entrada_sin_analisis_no_rechaza():
    """Si el resultado contó un cruce pero la entrada no llegó, no se la trata como si tuviera cero."""
    entrada = geo.caja(10, 10, 10)
    resultado = geo.compuesto([entrada, geo.caja(10, 10, 10, origen=(5, 5, 5))])
    aviso = {"mensaje": "No se revisaron las autointersecciones: plazo agotado."}
    avisos = []
    with patch.object(revision, "_autointersecciones_seguras",
                      side_effect=[(1, [], True), (None, [aviso], False)]):
        assert not sm._cruza_mas_que(entrada, resultado, avisos)
    assert avisos == [aviso["mensaje"]]


def test_vaciado_de_la_tina_revisa_rapido_y_sin_cruces():
    """La compuerta ya no espera el BOP de todo el sólido: revisa la pared nueva por malla en menos de 5 s."""
    forma = sc.solevar([_circulo(30, 0), _ranura(ALTO)])
    cara = max((c for c in geo.caras(forma) if geo.caja_envolvente(c)[0][2] > 80), key=geo.area)
    duraciones, resultados = [], []
    real = sm._cruces_pared_malla

    def medir(*args):
        inicio = time.perf_counter()
        try:
            salida = real(*args)
            resultados.append(salida)
            return salida
        finally:
            duraciones.append(time.perf_counter() - inicio)

    with patch.object(sm, "_cruces_pared_malla", side_effect=medir) as revisar:
        hueco = sm.vaciado(forma, [cara], espesor_interior=1.0)
    assert revisar.call_count == 1
    assert resultados == [0], "la vía rápida no terminó: se usó el BOP de respaldo"
    assert duraciones[0] < 5.0, f"la revisión de la pared tardó {duraciones[0]:.3f} s"
    assert geo.es_valida(hueco) and 0 < geo.volumen_exacto(hueco) < geo.volumen_exacto(forma)


def test_compuerta_del_vaciado_rechaza_un_cruce_real():
    """Dos cajas superpuestas tienen cruces comprobados por BOP y por la malla: no pasan como una pared válida."""
    entrada = geo.caja(10, 10, 10)
    resultado = geo.compuesto([geo.caja(10, 10, 10), geo.caja(10, 10, 10, origen=(5, 5, 5))])
    assert revision._autointersecciones_seguras(resultado, 1, 5.0)[0] > 0
    assert sm._cruces_pared_malla(entrada, resultado) > 0
    with pytest.raises(geo.ErrorGeometria, match="el espesor no cabe"):
        sm._exigir_pared_sin_cruces(entrada, resultado)


def test_compuerta_del_vaciado_rechaza_un_solape_coplanar():
    """El rayo no ve dos láminas en el mismo plano: la forma analítica pasa también por el BOP exacto."""
    entrada = geo.caja(20, 20, 20)
    resultado = geo.compuesto([geo.caja(10, 10, 10), geo.caja(10, 10, 10)])
    assert revision._autointersecciones_seguras(resultado, 1, 5.0)[0] > 0
    with pytest.raises(geo.ErrorGeometria, match="el espesor no cabe"):
        sm._exigir_pared_sin_cruces(entrada, resultado)


def test_vaciado_sin_malla_ni_analisis_no_rechaza_y_avisa():
    """Respaldo agotado: se conserva la pieza válida y el aviso entra en una sola línea de panel."""
    s, cid = _pieza(superficie=False)
    forma = s.cuerpo(cid).forma
    cara = max((c for c in geo.caras(forma) if geo.caja_envolvente(c)[0][2] > 80), key=geo.area)
    avisos = []
    with patch.object(sm, "_cruces_pared_malla", side_effect=RuntimeError("sin malla")), _sin_llegar():
        hueco = sm.vaciado(forma, [cara], espesor_interior=1.0, avisos=avisos)
    assert geo.es_valida(hueco) and 0 < geo.volumen_exacto(hueco) < geo.volumen_exacto(forma)
    assert avisos == ["Vaciado: no se revisaron los cruces."]
    assert len(avisos[0]) <= 45 and "\n" not in avisos[0]


def test_solevacion_con_condiciones_sin_analisis_no_rechaza():
    """Frío: la seta de B-243 NO se rechaza porque el conteo no llegó (el paso avisa en `ops_solido`)."""
    with _sin_llegar():
        seta = sc.solevar([_circulo(30, 0), _ranura(ALTO)],
                          condicion_inicio={"tipo": "direccion", "angulo": 0, "peso": 1})
    assert geo.es_valida(seta) and geo.volumen_exacto(seta) > 0


def test_solevacion_plegada_sin_analisis_no_rechaza():
    """Frío: el antebrazo de B-173/B-419 NO se rechaza porque el conteo no llegó: queda la versión de siempre."""
    s = _secciones()
    with _sin_llegar():
        r = api.llamar(s, "create_surface_loft",
                       {"profiles": [{"sketch": b, "profile": 0}
                                      for b in ("Bc_ant_n", "Bc_ant_m", "Bc_ant_p")]})
    assert r["ok"], r
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1 and geo.es_valida(cuerpos[0].forma)


def test_solevacion_lisa_sin_analisis_no_se_rechaza():
    """Frío: el codo de B-618 no se rechaza porque el conteo no llegó: como antes, queda el loft de siempre."""
    c1 = _alambre_circulo((0, 0, 0), (0, 0, 1), 10)
    c2 = _alambre_circulo((5, 0, 30), (0, 1, 0), 10)
    with _sin_llegar():
        codo = sc.solevar([c1, c2])
    assert geo.es_valida(codo) and geo.volumen_exacto(codo) > 0


def test_caliente_el_veredicto_sale_de_un_analisis_que_llego():
    """Caliente (como B-853): el veredicto del desfase sale de un conteo que terminó, no de un plazo agotado."""
    real = revision._autointersecciones_seguras
    completos = []

    def espia(forma, limite, plazo):
        cantidad, problemas, completo = real(forma, limite, plazo)
        completos.append(completo)
        return cantidad, problemas, completo

    lamina = sc.solevar([_circulo(30, 0), _ranura(ALTO)], solido=False)
    with patch.object(revision, "_autointersecciones_seguras", side_effect=espia):
        desfasada = sf.desfasar_superficie(lamina, 0.1)
    assert geo.es_valida(desfasada)
    assert completos and any(completos), "el análisis del desfase no llegó a terminar"
