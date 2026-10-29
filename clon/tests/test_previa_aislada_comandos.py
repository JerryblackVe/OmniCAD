"""Fase E: la previa de empalme, chaflán, booleanas y patrones también sale en un proceso aparte sobre cuerpos grandes.

La malla del hijo es solo visual: lo aceptado sale del kernel en el padre (mismo contrato que P-51, Vaciado).
"""
import math
import runpy
import time
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import geometria as geo
from omnicad.nucleo.render_cpu import es_malla
from omnicad.timeline.calculo_aislado import leer_previa_visual, previa_visual
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_solido import OpPatron
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import TIPOS_PESADOS, _ids_cuerpo
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

BANCO = Path(__file__).resolve().parents[2] / "scripts/medir_previa_comandos.py"
COMANDOS = ("empalme", "chaflan", "cortar", "unir", "intersecar", "vaciar", "patron_rectangular", "patron_circular")


@pytest.fixture(scope="module")
def banco():
    return runpy.run_path(str(BANCO))


@pytest.fixture(scope="module")
def receta_placa(banco):
    return banco["_modelo"]("placa200")[0]


def abrir(tmp_path, doc):
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    app.processEvents()
    return v


def cerrar(v):
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QApplication.processEvents()


@pytest.fixture
def ventana_placa(tmp_path, receta_placa):
    v = abrir(tmp_path, Documento.desde_dict(receta_placa))
    yield v
    cerrar(v)


@pytest.fixture
def ventana_chica(tmp_path):
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="100", largo="60", alto="20"))
    v = abrir(tmp_path, d)
    yield v
    cerrar(v)


def test_los_ids_de_cuerpo_se_leen_de_cada_forma_de_parametro():
    p = {"aristas": [{"ref": {"tipo": "arista", "cuerpo": "op1.c1"}}, {"tipo": "arista", "cuerpo": "op1.c2"}],
         "cuerpos": ["op3.c1"], "objetivo": "op4.c1", "caras": [{"cuerpo": "op5.c1", "indice": 3}],
         "conjuntos": [{"aristas": [{"ref": {"cuerpo": "op6.c1"}}]}], "radio": "op9.c9", "x": "0"}
    assert _ids_cuerpo(p) == {"op1.c1", "op1.c2", "op3.c1", "op4.c1", "op5.c1", "op6.c1"}
    assert _ids_cuerpo({"objetivo": ["op2.c1", {"cuerpo": "op2.c2"}]}) == {"op2.c1", "op2.c2"}
    assert _ids_cuerpo({}) == set()


@pytest.mark.parametrize("caso", COMANDOS)
def test_solo_los_cuerpos_de_muchas_caras_van_a_un_proceso_aparte(caso, banco, ventana_placa, ventana_chica):
    grande = banco["_preparar"](ventana_placa, caso, "placa200")[0]
    op = grande.comando.construir(grande.valores, grande.ctx)
    assert op.TIPO in TIPOS_PESADOS and grande._previa_pesada(op)
    grande.cancelar()
    chico = banco["_preparar"](ventana_chica, caso, "chico")[0]
    op = chico.comando.construir(chico.valores, chico.ctx)
    assert not chico._previa_pesada(op)       # 6 caras: la previa del proceso sigue siendo más rápida
    chico.cancelar()


def test_una_primitiva_nueva_nunca_va_a_un_proceso_aparte(ventana_placa):
    p = ventana_placa.ejecutar_comando(CATALOGO["caja"]())
    op = p.comando.construir(p.valores, p.ctx)           # operacion «nuevo»: no nombra ningún cuerpo
    assert not p._previa_pesada(op)
    p.cancelar()


def documento_con_patron(n=3, separacion="150 mm"):
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="10"))
    cid = next(iter(d.estado_final.cuerpos))
    op = OpPatron(d.nuevo_id(), forma_patron="rectangular", cuerpos=[cid], dir1={"tipo": "eje", "id": "X"},
                  n1=n, d1=separacion, distribucion="espaciado")
    return d, cid, op


def test_la_previa_visual_arma_los_cuerpos_nuevos_de_un_patron():
    d, cid, op = documento_con_patron()
    receta = d.a_dict()
    salida = previa_visual(receta, op.a_dict(), None, 0.05, 0.3)
    estado, avisos = leer_previa_visual(salida, d.estado_final)
    assert not avisos and list(estado.cuerpos)[0] == cid and len(estado.cuerpos) == 3
    original = estado.cuerpos[cid].forma
    assert es_malla(original) is False                      # el original no cambió: conserva su forma exacta
    for k, nuevo in enumerate(list(estado.cuerpos.values())[1:], start=1):
        assert es_malla(nuevo.forma) and nuevo.origen == (cid,) and nuevo.nombre
        v = nuevo.forma.vertices
        assert v[:, 0].min() == pytest.approx(150 * k, abs=1e-3) and v[:, 0].max() == pytest.approx(40 + 150 * k, abs=1e-3)
        assert nuevo.id in estado._mallas_previa and len(estado._mallas_previa[nuevo.id][0]) == len(v)
    assert d.a_dict() == receta and len(d.estado_final.cuerpos) == 1       # el documento ni se enteró


def test_un_patron_aceptado_sale_del_kernel_y_no_de_la_malla_del_hijo():
    d, cid, op = documento_con_patron()
    salida = previa_visual(d.a_dict(), op.a_dict(), None, 0.05, 0.3)
    estado, _ = leer_previa_visual(salida, d.estado_final)
    assert d.agregar(op).estado == "ok"
    for cuerpo in d.estado_final.cuerpos.values():
        assert not es_malla(cuerpo.forma) and geo.es_valida(cuerpo.forma)
    exacto = list(d.estado_final.cuerpos)
    assert exacto == list(estado.cuerpos)                    # mismos ids que la previa mostró


def esperar(p, plazo=90):
    fin = time.perf_counter() + plazo
    while p._hijo_previa is not None and time.perf_counter() < fin:
        QTest.qWait(10)
    assert p._hijo_previa is None, "El hijo no terminó"


def test_el_patron_sobre_la_placa_se_calcula_aparte_y_aceptar_da_el_solido_exacto(banco, ventana_placa, monkeypatch):
    p = banco["_preparar"](ventana_placa, "patron_rectangular", "placa200")[0]
    vistas = []
    monkeypatch.setattr(type(p.comando), "previa_vista", lambda self, ctx, v, op: vistas.append(op.TIPO))
    antes = ventana_placa.doc.a_dict()
    p._calcular_previa()
    assert p._hijo_previa is not None and p._previa_aparte and not p._previa_ok
    assert ventana_placa.doc.a_dict()["operaciones"] == antes["operaciones"]
    esperar(p)
    assert p._previa_ok, p.mensaje.text()
    estado = ventana_placa.visor._estado
    assert len(estado.cuerpos) == 3 and vistas == ["patron"]
    assert sum(es_malla(c.forma) for c in estado.cuerpos.values()) == 2          # solo las copias son malla
    assert len(ventana_placa.doc.estado_final.cuerpos) == 1
    p.aceptar()
    assert ventana_placa.panel is None
    finales = ventana_placa.doc.estado_final.cuerpos
    assert len(finales) == 3 and all(not es_malla(c.forma) and geo.es_valida(c.forma) for c in finales.values())
    volumenes = {geo.volumen_exacto(c.forma) for c in finales.values()}
    assert len(volumenes) == 1 or max(volumenes) == pytest.approx(min(volumenes), rel=1e-9)


# ------------------------------------------------------------- asas que no se recalculan al mover el valor
@pytest.mark.parametrize("caso", ("empalme", "chaflan"))
def test_el_asa_de_arista_se_reusa_y_sigue_a_la_punta_del_valor(caso, banco, ventana_placa):
    p = banco["_preparar"](ventana_placa, caso, "placa200")[0]
    clave = banco["CASOS"][caso][1]
    g = p.manipuladores
    g.actualizar()
    construidas = []
    original = p.comando.manipuladores
    p.comando.manipuladores = lambda ctx, v: (construidas.append(1), original(ctx, v))[1]
    g.actualizar()
    construidas.clear()
    asa = next(m for m in g.manips if isinstance(m, mp.Flecha))
    colas = []
    for texto in ("1 mm", "2.5 mm", "4 mm"):
        p.set_valor(clave, texto)
        p._t_previa.stop()
        assert next(m for m in g.manips if isinstance(m, mp.Flecha)) is asa       # misma asa, sin reconstruir
        colas.append(asa.puntos(g)[0])
    assert not construidas
    # Contra una asa reconstruida desde cero con el mismo valor: dibuja exactamente lo mismo.
    nueva = next(m for m in p.comando.manipuladores(p.ctx, p.valores) if isinstance(m, mp.Flecha))
    for a, b in zip(asa.dibujar(g, None), nueva.dibujar(g, None), strict=True):
        assert a[0] == b[0] and np.allclose(a[1], b[1])
    assert np.linalg.norm(colas[2] - colas[0]) > 0.5                              # y la cola sí se movió
    # Cambiar la arista elegida SÍ reconstruye.
    p.set_valor("aristas", [])
    p._t_previa.stop()
    assert not any(isinstance(m, mp.Flecha) for m in g.manips) and construidas
    p.cancelar()


# ------------------------------------------------------------- dibujos vectorizados = los de siempre
def _disco_ref(R, centro, radio, color, borde=None):
    u, v = np.asarray(R[0], float), np.asarray(R[1], float)
    lineas, n = [], 9
    for i in range(-n, n + 1):
        y = radio * i / n
        x = math.sqrt(max(radio * radio - y * y, 0.0))
        lineas += [centro - u * x + v * y, centro + u * x + v * y]
    prims = [("lineas", np.array(lineas), color, 2.0)]
    if borde is not None:
        angs = np.linspace(0, 2 * math.pi, 25)
        prims.append(("lineas", mp._segs([centro + (u * math.cos(a) + v * math.sin(a)) * radio for a in angs]), borde,
                      1.5))
    return prims


def _cono_ref(base, eje, largo, radio, color, n=20):
    eje = mp.unitario(eje)
    u, v = mp.perpendiculares(eje)
    punta = base + eje * largo
    angs = np.linspace(0, 2 * math.pi, n + 1)
    anillo = np.array([base + (u * math.cos(a) + v * math.sin(a)) * radio for a in angs])
    tris, lineas = [], []
    for i in range(n):
        tris += [punta, anillo[i], anillo[i + 1], base, anillo[i + 1], anillo[i]]
        lineas += [punta, anillo[i]]
        for k in (0.33, 0.66):
            lineas += [punta, anillo[i] + (anillo[i + 1] - anillo[i]) * k]
    return [("tris", np.array(tris), color, 1.0), ("lineas", np.array(lineas), color, 1.6),
            ("lineas", mp._segs(anillo), color, 1.6)]


def _igual(a, b):
    assert len(a) == len(b)
    for x, y in zip(a, b, strict=True):
        assert x[0] == y[0] and x[2:] == y[2:] and x[1].shape == y[1].shape and np.allclose(x[1], y[1], atol=1e-9)


@pytest.mark.parametrize("semilla", range(5))
def test_el_disco_y_el_cono_vectorizados_dan_los_mismos_puntos(semilla):
    r = np.random.default_rng(semilla)
    R = np.linalg.qr(r.normal(size=(3, 3)))[0]
    centro, eje = r.normal(size=3) * 50, r.normal(size=3)
    visor = type("V", (), {"R": R})()
    for borde in (None, (1, 0, 0)):
        _igual(mp._disco(visor, centro, 4.5, (0, 1, 0), borde), _disco_ref(R, centro, 4.5, (0, 1, 0), borde))
    _igual(mp._cono(centro, eje, 7.0, 2.0, (0, 0, 1)), _cono_ref(centro, eje, 7.0, 2.0, (0, 0, 1)))
