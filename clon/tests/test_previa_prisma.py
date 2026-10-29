"""Previa de Extruir por transformación (P-44): la malla es solo visual; el sólido aceptado sale siempre del kernel."""
from pathlib import Path
import runpy

import numpy as np
import pytest
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, render_cpu as rc
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui import visor3d as vis
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture(scope="module")
def placa():
    banco = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/medir_previa_comandos.py"))
    receta, _ = banco["_modelo"]("placa200")
    d = Documento.desde_dict(receta)
    base = d.operacion("op2")
    unidad = OpExtrusion("op2", **dict(base.p, distancia="1", direccion="un_lado"))
    e, _ = d.previsualizar(unidad, 1, en_vivo=True)
    forma = e.cuerpos["op2.c1"].forma
    partes = rc._mallas_por_cara(forma, 0.05, 0.3)
    v, n = (np.concatenate([p[i] for p in partes]) for i in (1, 2))
    return d, base, rc.PrismaVisual(v, n, np.zeros((0, 3)), [0, 0, 0], [0, 0, 1])


@pytest.mark.parametrize("caso", range(20))
def test_veinte_distancias_con_huecos_coinciden_con_el_kernel(placa, caso):
    d, base, prisma = placa
    azar = np.random.default_rng(20261029 + caso)
    d1, d2 = azar.uniform(2, 60, 2)
    d1 *= -1 if caso % 2 else 1
    modo = ("un_lado", "simetrica", "dos_lados")[caso % 3]
    medida = "total" if caso % 2 else "mitad"
    invertida = caso % 4 == 0
    op = OpExtrusion("op2", **dict(base.p, distancia=str(d1), distancia2=str(d2),
                                  direccion=modo, medida=medida, invertir=invertida))
    e, _ = d.previsualizar(op, 1, en_vivo=True)
    forma = e.cuerpos["op2.c1"].forma
    if modo == "un_lado":
        a, b = 0, d1
    elif modo == "simetrica":
        b = abs(d1) * (0.5 if medida == "total" else 1)
        a = -b
    else:
        a, b = min(0, d1, -d2), max(0, d1, -d2)
    if invertida:
        a, b = -a, -b
    v, n, _ = prisma.transformar(a, b)
    caja = np.array([v.min(0), v.max(0)])
    assert np.allclose(caja, geo.caja_envolvente(forma), atol=1e-6, rtol=0)
    tris = v.reshape(-1, 3, 3) - v.mean(0)
    volumen = np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6
    assert volumen == pytest.approx(geo.volumen_exacto(forma), rel=0.001)
    assert np.allclose(np.linalg.norm(n, axis=1), 1, atol=1e-6)
    tri = v.reshape(-1, 3, 3)
    giro = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    assert (np.einsum("ij,ij->i", giro, n.reshape(-1, 3, 3).mean(1)) > -1e-9).all()  # normal coherente con el giro
    mn, mx = prisma.caja(a, b)
    assert (v >= mn - 1e-9).all() and (v <= mx + 1e-9).all()
    assert geo.es_valida(forma)


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"name": "R", "entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [40, 30]}]})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    p = v.ejecutar_comando(Extruir())
    br = s.doc.estado_final.bocetos["op1"]
    ref = {"tipo": "perfil", "boceto": "op1", **OpExtrusion.referencia_perfil(br.perfiles[0])}
    p._elegida(hit_desde_ref(ref, p.ctx.estado))
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok, p.mensaje.text()
    yield v, p
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _arrastrar_a(p, valor):
    """Agarra la flecha de la distancia (una vez) y la lleva a `valor`: la previa va por la malla estimada."""
    g = p.manipuladores
    if not g.arrastrando:
        flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
        a, b = flecha.puntos(g)
        puntos, visibles = g.pantalla([(a + b) / 2])
        assert visibles[0] and g.empezar_arrastre(QPointF(*puntos[0]))
    g.escribir({"distancia": float(valor)})
    p._t_previa.stop()
    p._calcular_previa()


def _forma_visor(v):
    return next(iter(v.visor._estado.cuerpos.values())).forma


def test_al_arrastrar_no_ejecuta_kernel_ni_retesela(ventana, monkeypatch):
    v, p = ventana

    def prohibido(*a, **k):
        pytest.fail("El movimiento volvió a calcular un prisma del kernel")

    muestreos, original = [], vis.polilineas_boceto
    monkeypatch.setattr(vis, "polilineas_boceto", lambda br: muestreos.append(br) or original(br))
    _arrastrar_a(p, 5)     # el primer cuadro del gesto publica el estado con la malla
    assert muestreos == []     # y no remuestrea los bocetos, que no cambian durante el gesto (un slot de Qt se tragaría un fail)
    monkeypatch.setattr(v.doc, "previsualizar", prohibido)
    monkeypatch.setattr(v.visor, "_puntos_escena", prohibido)
    for valor in (20, -15, 25):
        _arrastrar_a(p, valor)
        assert p._previa_ok
        dibujado = v.visor._mallas[-1]["v"]
        assert np.ptp(dibujado, axis=0)[2] == pytest.approx(abs(valor))
        assert np.allclose([dibujado[:, 2].min(), dibujado[:, 2].max()], sorted([0, valor]), atol=1e-6)
        assert np.allclose(np.asarray(v.visor._caja_escena())[:, 2], sorted([0, valor]), atol=1e-6)
    monkeypatch.undo()
    p.manipuladores.soltar()
    p._t_previa.stop()
    p._calcular_previa()  # al soltar el asa, el camino exacto reemplaza la malla
    assert all(not rc.es_malla(c.forma) for c in v.visor._estado.cuerpos.values())


def test_valor_tecleado_sale_del_kernel_y_no_es_una_malla(ventana):
    v, p = ventana
    p.set_valor("distancia", "20")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok and p._prisma_previa is not None    # la plantilla queda lista para el primer arrastre
    forma = _forma_visor(v)
    assert not rc.es_malla(forma) and geo.volumen_exacto(forma) == pytest.approx(40 * 30 * 20, rel=1e-9)


def test_aceptar_un_milimetro_no_reutiliza_la_malla_de_la_plantilla(ventana):
    v, p = ventana
    _arrastrar_a(p, 1)
    assert rc.es_malla(_forma_visor(v))
    assert all(not rc.es_malla(c.forma) for c in v.doc._previa["salida"].cuerpos.values())
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    assert v.panel is None
    forma = next(iter(v.doc.estado_final.cuerpos.values())).forma
    assert not rc.es_malla(forma) and geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(1200, rel=1e-9)


def test_soltar_el_asa_reemplaza_la_malla_por_el_brep_sin_otro_cambio(ventana):
    v, p = ventana
    _arrastrar_a(p, 20)
    assert rc.es_malla(_forma_visor(v))
    p.manipuladores.soltar()
    QTest.qWait(50)
    assert all(not rc.es_malla(c.forma) for c in v.visor._estado.cuerpos.values())


def test_conicidad_usa_el_camino_exacto(ventana):
    v, p = ventana
    p.set_valor("conicidad", "3 deg")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok and p._prisma_previa is None
    assert all(not rc.es_malla(c.forma) for c in v.visor._estado.cuerpos.values())


def test_un_perfil_que_no_arranca_en_su_plano_no_se_estima():
    v = np.array([[0, 0, 0.5], [1, 0, 0.5], [0, 1, 1.5]], float)    # base a 0,5 mm del plano: no es un prisma recto
    with pytest.raises(geo.ErrorGeometria, match="plano"):
        rc.PrismaVisual(v, np.tile([0, 0, 1.0], (3, 1)), np.zeros((0, 3)), [0, 0, 0], [0, 0, 1])


def _volumen_final(v):
    return sum(geo.volumen_exacto(c.forma) for c in v.doc.estado_final.cuerpos.values())


@pytest.mark.parametrize("texto", ["", "0", "abc"])
def test_valor_tecleado_invalido_avisa_y_se_recupera(ventana, texto):
    v, p = ventana
    p.set_valor("distancia", texto)
    p._t_previa.stop()
    p._calcular_previa()
    assert not p._previa_ok and p.mensaje.text()
    p.set_valor("distancia", "20")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok and not p.mensaje.text()
    assert np.ptp(v.visor._mallas[-1]["v"], axis=0)[2] == pytest.approx(20)


@pytest.mark.parametrize("texto", ["-15", "5000", "12,5", "2 in"])
def test_valor_tecleado_extremo_o_con_unidad_dibuja_lo_pedido(ventana, texto):
    v, p = ventana
    p.set_valor("distancia", texto)
    p._t_previa.stop()
    p._calcular_previa()
    esperado = p.ctx.evaluar(texto)
    assert p._previa_ok, p.mensaje.text()
    assert np.ptp(v.visor._mallas[-1]["v"], axis=0)[2] == pytest.approx(abs(esperado))


def test_esc_en_pleno_arrastre_no_deja_pasos_ni_cuerpos_estimados(ventana):
    v, p = ventana
    pasos = len(v.doc.operaciones)
    _arrastrar_a(p, 30)
    assert rc.es_malla(_forma_visor(v))
    p.cancelar()
    assert v.panel is None and len(v.doc.operaciones) == pasos
    assert not v.visor._estado.cuerpos
    assert not any(rc.es_malla(c.forma) for c in v.doc.estado_final.cuerpos.values())


def test_aceptar_editar_deshacer_y_rehacer_dan_el_solido_del_kernel(ventana):
    v, p = ventana
    area = 40 * 30
    p.set_valor("distancia", "10")
    p._t_previa.stop()
    p._calcular_previa()
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    assert v.panel is None and _volumen_final(v) == pytest.approx(area * 10, rel=1e-9)

    v.editar_operacion(list(v.doc.operaciones)[-1].id)
    q = v.panel
    q.set_valor("distancia", "12")
    q._t_previa.stop()
    q._calcular_previa()
    _arrastrar_a(q, 25)
    assert q._prisma_previa is not None and rc.es_malla(_forma_visor(v))
    q.manipuladores.soltar()
    QTest.mouseClick(q.boton_ok, Qt.LeftButton)
    forma = next(iter(v.doc.estado_final.cuerpos.values())).forma
    assert not rc.es_malla(forma) and geo.es_valida(forma)
    assert _volumen_final(v) == pytest.approx(area * 25, rel=1e-9)
    caja = geo.caja_envolvente(forma)
    assert np.allclose(caja, [[0, 0, 0], [40, 30, 25]], atol=1e-6)

    v.doc.deshacer()
    assert _volumen_final(v) == pytest.approx(area * 10, rel=1e-9)
    v.doc.rehacer()
    assert _volumen_final(v) == pytest.approx(area * 25, rel=1e-9)
