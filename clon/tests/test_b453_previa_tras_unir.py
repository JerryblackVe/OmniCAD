"""B-453 y B-458: la previa rápida de Extruir sobre un cuerpo ya modificado por un paso anterior (la secuencia de Gerardo:
caja, Extruir la cara lateral con «Unir», Extruir la cara de arriba). Si la previa rápida no puede, cae a la normal sin
mostrar su error interno, y el asa sale sobre la cara."""
import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], r
    return r["result"]


VARIANTES = {"en el origen": {}, "lejos del origen": {"x": 300, "y": 200, "z": 100},
             "movida": {"mover": [120, -80, 40]}, "girada": {"girar": [0, 0, 30]},
             "de un boceto": {"boceto": True}}      # el cuerpo de Gerardo: Boceto1 → Extruir 62,2 mm → Extruir la cara de arriba


def _documento_de_gerardo(variante):
    s = api.Sesion()
    opciones = dict(VARIANTES[variante])
    if opciones.pop("boceto", False):
        _llamar(s, "create_sketch", plane="XY")
        _llamar(s, "draw_rectangle", x1=0, y1=0, x2=73, y2=65.46)
        _llamar(s, "extrude", sketch="Boceto1", distance=62.2, operation="new_body")
        return s.doc
    mover, girar = opciones.pop("mover", None), opciones.pop("girar", None)
    _llamar(s, "create_box", length=100, width=100, height=50, **opciones)
    if mover or girar:
        _llamar(s, "move_body", body="Cuerpo1", translate=mover, rotate=girar, pivot="origin")
    _llamar(s, "create_sketch", plane="<Y")
    _llamar(s, "draw_rectangle", x1=-50, y1=0, x2=50, y2=50)
    _llamar(s, "extrude", sketch="Boceto1", distance=70, operation="join")
    return s.doc


@pytest.mark.parametrize("variante", list(VARIANTES))
def test_extruir_la_cara_de_arriba_tras_unir_tiene_previa_sin_el_error_interno(tmp_path, variante):
    app = QApplication.instance() or QApplication([])
    doc = _documento_de_gerardo(variante)
    cid = next(iter(doc.estado_final.cuerpos))
    forma = doc.estado_final.cuerpos[cid].forma
    arriba = max((c for c in refs.subformas(forma, "cara")), key=lambda c: refs.firma(c)["centro"][2])
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        p._elegida(hit_desde_ref(refs.referencia(cid, arriba, forma), p.ctx.estado))
        p.set_valor("distancia", "5 mm")
        for valor in (5, 22, 54):                              # arrastrando la flecha, como en el video de Gerardo
            g = p.manipuladores
            if not g.arrastrando:
                flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
                a, b = flecha.puntos(g)
                puntos, visibles = g.pantalla([(a + b) / 2])
                assert visibles[0] and g.empezar_arrastre(QPointF(*puntos[0]))
            g.escribir({"distancia": float(valor)})
            p._t_previa.stop()
            p._calcular_previa()
            QTest.qWait(300)                                   # la exacta del proceso aparte, si la hay
            texto = p.mensaje.text()
            assert "La previa solo admite" not in texto and "⚠" not in texto, texto
            assert p._previa_ok, texto
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_si_la_previa_rapida_no_puede_cae_a_la_normal_sin_su_error_interno(tmp_path, monkeypatch):
    """B-458: la previa con prisma es un atajo. Si su plantilla falla (aquí con el mismo error de Gerardo), al arrastrar
    la flecha no sale en rojo: va la previa normal y la forma exacta se ve."""
    from omnicad.nucleo import geometria as geo, render_cpu as rc

    def imposible(*a, **k):
        raise geo.ErrorGeometria("La previa solo admite un perfil plano extruido 1 mm desde su plano.")

    monkeypatch.setattr(rc, "prisma_unidad", imposible)
    app = QApplication.instance() or QApplication([])
    doc = _documento_de_gerardo("en el origen")
    cid = next(iter(doc.estado_final.cuerpos))
    forma = doc.estado_final.cuerpos[cid].forma
    arriba = max((c for c in refs.subformas(forma, "cara")), key=lambda c: refs.firma(c)["centro"][2])
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        p._elegida(hit_desde_ref(refs.referencia(cid, arriba, forma), p.ctx.estado))
        p.set_valor("distancia", "5 mm")
        g = p.manipuladores
        flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
        a, b = flecha.puntos(g)
        puntos, visibles = g.pantalla([(a + b) / 2])
        assert visibles[0] and g.empezar_arrastre(QPointF(*puntos[0]))
        g.escribir({"distancia": 22.0})
        p._t_previa.stop()
        p._calcular_previa()
        QTest.qWait(500)                                       # la exacta, en la ventana o en el proceso aparte
        assert "La previa solo admite" not in p.mensaje.text() and "⚠" not in p.mensaje.text(), p.mensaje.text()
        assert p._previa_ok
        assert p.ultima_op is not None and p._prisma_previa is None      # sin plantilla barata: la previa es la normal
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_extruir_la_cara_de_arriba_de_una_extrusion_hecha_con_el_panel(tmp_path):
    """El camino de Gerardo: Boceto1 → Extruir 62,2 mm con el panel y Aceptar → Extruir la cara de arriba arrastrando."""
    from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
    from omnicad.timeline.operaciones import OpExtrusion
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY")
    _llamar(s, "draw_rectangle", x1=20, y1=10, x2=93, y2=75.46)
    doc = s.doc
    sop, br = boceto_activo(s, s.paso("Boceto1").id)
    ref = OpExtrusion.referencia_perfil(seleccionar_perfiles(br, sop, 0)[0])
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": sop.id, **ref}, p.ctx.estado))
        p.set_valor("distancia", "62.2 mm")
        p._t_previa.stop()
        p._calcular_previa()
        QTest.qWait(300)
        p.aceptar()
        QTest.qWait(500)
        assert v.panel is None and len(v.doc.estado_final.cuerpos) == 1
        cid = next(iter(v.doc.estado_final.cuerpos))
        forma = v.doc.estado_final.cuerpos[cid].forma
        arriba = max(refs.subformas(forma, "cara"), key=lambda c: refs.firma(c)["centro"][2])
        p = v.ejecutar_comando(Extruir())
        p._elegida(hit_desde_ref(refs.referencia(cid, arriba, forma), p.ctx.estado))
        p.set_valor("distancia", "5 mm")
        g = p.manipuladores
        flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
        a, b = flecha.puntos(g)
        puntos, visibles = g.pantalla([(a + b) / 2])
        assert visibles[0] and g.empezar_arrastre(QPointF(*puntos[0]))
        for valor in (22.0, 54.08):
            g.escribir({"distancia": valor})
            p._t_previa.stop()
            p._calcular_previa()
            QTest.qWait(300)
            assert "La previa solo admite" not in p.mensaje.text() and "⚠" not in p.mensaje.text(), p.mensaje.text()
            assert p._previa_ok
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
