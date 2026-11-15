"""P-156: holgura de impresión 3D única (Preferencias), usada por la Rosca y el Agujero roscado."""
import pytest

from omnicad import api
from omnicad.nucleo import solidos_crear as sc
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos import crear


@pytest.fixture
def prefs(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "prefs.ini"))


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _volumen(s):
    return _ok(s, "get_scene_info")["bodies"][0]["volume"]


def test_p156_la_preferencia_acepta_mm_por_lado_y_rechaza_lo_demas(prefs):
    s = api.Sesion()
    assert _ok(s, "get_preferences", keys=["impresion/holgura_mm"])["preferences"][0]["value"] == 0.2
    assert _ok(s, "set_preference", key="impresion/holgura_mm", value=0.35)["value"] == 0.35
    for malo in (-0.1, 2, True, "0.2"):
        assert not api.llamar(s, "set_preference", {"key": "impresion/holgura_mm", "value": malo})["ok"], malo


@pytest.mark.parametrize("pieza", ["tornillo", "agujero"])
def test_p156_print_clearance_general_usa_la_preferencia(prefs, pieza):
    """El agujero agranda y el tornillo achica con el valor de Preferencias, igual que con el número."""
    volumenes = {}
    for holgura in (0, "general", 0.3):
        s = api.Sesion()
        _ok(s, "set_preference", key="impresion/holgura_mm", value=0.3)
        if pieza == "tornillo":
            _ok(s, "create_cylinder", radius=5, height=12)
            _ok(s, "create_thread", faces="%CYLINDER", thread="M10", thread_class="", print_clearance=holgura)
        else:
            _ok(s, "create_box", length=30, width=30, height=12)
            _ok(s, "create_hole", face=">Z", hole_tap="modeled", thread="M10", thread_class="", through_all=True,
                print_clearance=holgura)
        volumenes[holgura] = _volumen(s)
        if holgura == "general":
            assert [op.p["holgura_3d"] for op in s.doc.operaciones if "holgura_3d" in op.p] == ["0.3 mm"]
    assert volumenes["general"] == pytest.approx(volumenes[0.3], rel=1e-6)
    assert volumenes["general"] < volumenes[0] - 1          # quita material en los dos casos
    # El Ø del taladro del agujero: M10 sin clase 8,376 mm + 2 × 0,3
    assert sc.diametro_taladro_rosca("M10", "", 0.3) == pytest.approx(8.376 + 0.6, abs=1e-3)


def test_p156_la_linea_del_panel_lleva_el_valor_y_la_casilla_decide():
    s = api.Sesion()
    ctx = ContextoComando(s.doc)
    campo = crear._campo_holgura(ctx, lambda v: True)
    assert campo.etiqueta == "Holgura de impresión: 0,2 mm por lado"
    assert crear._holgura_3d({"impresion": True}, ctx) == "0.2 mm"
    assert crear._holgura_3d({"impresion": False}, ctx) == "0 mm"


def test_p156_al_editar_conserva_la_holgura_del_paso():
    s = api.Sesion()
    _ok(s, "create_cylinder", radius=5, height=12)
    _ok(s, "create_thread", faces="%CYLINDER", thread="M10", print_clearance=0.35, modeled=False)
    op = s.doc.operaciones[-1]
    ctx = ContextoComando(s.doc, op=op)
    assert crear.Rosca().desde_op(op, ctx)["impresion"] is True
    assert crear._campo_holgura(ctx, lambda v: True).etiqueta == "Holgura de impresión: 0,35 mm por lado"
    assert crear._holgura_3d({"impresion": True}, ctx) == "0.35"     # la expresión del paso, tal cual
