"""H-84: «Cadena tangente» de la Extrusión delgada: elegir una curva abierta elige las que siguen por tangencia."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_activo
from omnicad.restricciones.auto_candidatos import cadena_tangente_de
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def llamar(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def escena():
    """Línea, arco tangente y línea tangente (una cadena) + una línea en esquina (no tangente) + otra suelta."""
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY")
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)
    llamar(s, "draw_arc", start_x=20, start_y=0, center_x=20, center_y=10, sweep_angle=90)
    llamar(s, "draw_line", start_x=30, start_y=10, end_x=30, end_y=30)
    llamar(s, "draw_line", start_x=30, start_y=30, end_x=50, end_y=30)      # esquina de 90°: no sigue por tangencia
    llamar(s, "draw_line", start_x=100, start_y=0, end_x=120, end_y=0)      # suelta
    sop, br = boceto_activo(s, None)
    ids = sorted(br.boceto.curvas)
    return s, sop, br.boceto, ids


def test_la_cadena_sigue_por_tangencia_y_corta_en_la_esquina(escena):
    s, sop, b, (a, arco, c, esquina, suelta) = escena
    assert sorted(cadena_tangente_de(b, arco)) == [a, arco, c]
    assert cadena_tangente_de(b, a)[0] == a and sorted(cadena_tangente_de(b, c)) == [a, arco, c]
    assert cadena_tangente_de(b, esquina) == [esquina] and cadena_tangente_de(b, suelta) == [suelta]


@pytest.mark.parametrize("cadena", [True, False])
def test_la_herramienta_extrude_suma_la_cadena_solo_si_se_pide(escena, cadena):
    s, sop, b, (a, arco, c, esquina, suelta) = escena
    llamar(s, "extrude", sketch=sop.id, open_curves=[arco], thin=True, wall_thickness=1, distance=5, tangent_chain=cadena)
    paso = s.doc.operaciones[-1]
    assert sorted(x["curva"] for x in paso.p["curvas"]) == (sorted([a, arco, c]) if cadena else [arco])


def test_el_panel_elige_y_quita_la_cadena_con_un_clic(escena, tmp_path):
    s, sop, b, (a, arco, c, esquina, suelta) = escena
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    try:
        panel = v.ejecutar_comando(CATALOGO["extruir"]())
        panel.set_valor("tipo", "delgada")
        ref = lambda i: {"tipo": "curva_boceto", "boceto": sop.id, "curva": i}  # noqa: E731
        panel._activar(next(x for x in panel.campos if x.clave == "perfiles"))
        panel._elegida(hit_desde_ref(ref(arco), panel.ctx.estado))               # sin la casilla: solo la curva tocada
        assert [h["ref"]["curva"] for h in panel.valores["perfiles"]] == [arco]
        panel._elegida(hit_desde_ref(ref(arco), panel.ctx.estado))               # clic de nuevo: se quita
        assert not panel.valores["perfiles"]
        panel.set_valor("cadena_tangente", True)
        panel._elegida(hit_desde_ref(ref(arco), panel.ctx.estado))
        assert sorted(h["ref"]["curva"] for h in panel.valores["perfiles"]) == sorted([a, arco, c])
        panel._elegida(hit_desde_ref(ref(c), panel.ctx.estado))                  # otra de la cadena: la quita entera
        assert not panel.valores["perfiles"]
        panel._elegida(hit_desde_ref(ref(esquina), panel.ctx.estado))           # fuera de la cadena: sola
        assert [h["ref"]["curva"] for h in panel.valores["perfiles"]] == [esquina]
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
