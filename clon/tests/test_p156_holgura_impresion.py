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
            _ok(s, "create_thread", faces="%CYLINDER", thread="M10", thread_class="", print_clearance=holgura,
                other_part="metal", modeled=True)
        else:
            _ok(s, "create_box", length=30, width=30, height=12)
            _ok(s, "create_hole", face=">Z", hole_tap="modeled", thread="M10", thread_class="", through_all=True,
                print_clearance=holgura, other_part="metal")
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
    assert campo[0].etiqueta == "Holgura de impresión: 0,2 mm por lado"
    assert crear._holgura_3d({"impresion": True}, ctx) == "0.2 mm"
    assert crear._holgura_3d({"impresion": False}, ctx) == "0 mm"


def test_p156_al_editar_conserva_la_holgura_del_paso():
    s = api.Sesion()
    _ok(s, "create_cylinder", radius=5, height=12)
    _ok(s, "create_thread", faces="%CYLINDER", thread="M10", print_clearance=0.35, modeled=False)
    op = s.doc.operaciones[-1]
    ctx = ContextoComando(s.doc, op=op)
    assert crear.Rosca().desde_op(op, ctx)["impresion"] is True
    assert crear._campo_holgura(ctx, lambda v: True)[0].etiqueta == "Holgura de impresión: 0,35 mm por lado"
    assert crear._holgura_3d({"impresion": True}, ctx) == "0.35"     # la expresión del paso, tal cual


def test_p156_con_la_otra_pieza_impresa_cada_una_se_lleva_la_mitad(prefs):
    s = api.Sesion()
    _ok(s, "set_preference", key="impresion/holgura_mm", value=0.3)
    _ok(s, "create_cylinder", radius=5, height=12)
    _ok(s, "create_thread", faces="%CYLINDER", thread="M10", print_clearance="general", modeled=False)
    op = s.doc.operaciones[-1]
    assert (op.p["holgura_3d"], op.p["otra_pieza"]) == ("0.15 mm", "impresa")
    ctx = ContextoComando(s.doc, op=op)       # al editar, la línea muestra el valor general, no la mitad
    assert crear._campo_holgura(ctx, lambda v: True)[0].etiqueta == "Holgura de impresión: 0,3 mm por lado"
    assert crear._holgura_3d({"impresion": True, "otra_pieza": "metalica"}, ctx) == "0.3 mm"


def test_p156_el_molde_deja_holgura_y_la_herramienta_no_cambia(prefs):
    """Combinar › Cortar con «Dejar holgura»: el hueco de un cubo de 10 crece 0,2 por lado; la herramienta queda igual."""
    vols = {}
    for holgura in (0, 0.2):
        s = api.Sesion()
        _ok(s, "create_box", length=30, width=30, height=30, name="Molde")
        _ok(s, "create_box", length=10, width=10, height=10, z=10, name="Pieza")
        _ok(s, "boolean_operation", target="Molde", tools=["Pieza"], operation="cut", keep_tools=True,
            print_clearance=holgura)
        vols[holgura] = {c["name"]: c["volume"] for c in _ok(s, "get_scene_info")["bodies"]}
    assert vols[0.2]["Pieza"] == pytest.approx(1000, rel=1e-6)
    hueco = 27000 - vols[0.2]["Molde"]          # cubo agrandado 0,2 con aristas y esquinas redondeadas
    assert hueco == pytest.approx(1000 + 6 * 100 * 0.2 + 12 * 10 * 3.14159 * 0.04 / 4 + 4 / 3 * 3.14159 * 0.008, rel=1e-3)


def test_p156_usar_este_valor_guarda_la_holgura_del_agujero():
    from types import SimpleNamespace
    mensajes, prefs = [], {}
    panel = SimpleNamespace(valores={"holgura_inicial": "0.1 mm", "paso": "0.05 mm", "cantidad": 5, "elegido": "0.2"},
                            ctx=SimpleNamespace(ventana=SimpleNamespace(prefs=prefs), evaluar=lambda t: float(t.split()[0])),
                            _mostrar=lambda texto, tipo=None: mensajes.append((texto, tipo)))
    placa = crear.PlacaHolguras()
    assert list(placa._agujeros(panel.valores, panel.ctx)) == ["0.1", "0.15", "0.2", "0.25", "0.3"]
    placa.usar(panel)
    assert prefs == {"impresion/holgura_mm": 0.2} and "0,2 mm por lado" in mensajes[0][0]


def test_p156_dejar_holgura_escondida_no_cambia_el_corte():
    """Con «Conservar herramientas» desmarcada, «Dejar holgura» se esconde y no cuenta aunque haya quedado marcada."""
    from omnicad.ui.comandos.modificar import Combinar
    s = api.Sesion()
    _ok(s, "create_box", length=30, width=30, height=30, name="Molde")
    _ok(s, "create_box", length=10, width=10, height=10, z=10, name="Pieza")
    ctx = ContextoComando(s.doc)
    cuerpos = list(s.doc.estado_final.cuerpos)
    v = {"objetivo": [{"ref": {"tipo": "cuerpo", "cuerpo": cuerpos[0]}}],
         "herramientas": [{"ref": {"tipo": "cuerpo", "cuerpo": cuerpos[1]}}],
         "operacion": "cortar", "dejar_holgura": True, "otra_pieza": "metalica"}
    assert Combinar().construir({**v, "mantener": False}, ctx).p["holgura"] == "0 mm"
    assert Combinar().construir({**v, "mantener": True}, ctx).p["holgura"] == "0.2 mm"


def _perno_en_cilindro(s):
    _ok(s, "create_cylinder", height=20, diameter=40, name="Cuerpo1")
    _ok(s, "create_cylinder", height=20, diameter=10, name="Cuerpo2")


def test_b609_perno_coaxial_con_holgura_impresa(prefs):
    """B-609: perno Ø10 coaxial en un cilindro Ø40, Cortar con 0,15 por lado e «Impresa»: esta pieza se lleva la mitad
    (0,075 por lado), así que el agujero queda Ø10,15; los dos cuerpos válidos y el perno intacto."""
    from omnicad.nucleo import geometria as geo
    s = api.Sesion()
    _ok(s, "set_preference", key="impresion/holgura_mm", value=0.15)
    _perno_en_cilindro(s)
    _ok(s, "boolean_operation", target="Cuerpo1", tools=["Cuerpo2"], operation="cut", keep_tools=True,
        print_clearance="general", other_part="printed")
    cuerpos = {c.nombre: c.forma for c in s.doc.estado_final.cuerpos.values()}
    assert all(geo.es_valida(f) for f in cuerpos.values())
    assert geo.volumen(cuerpos["Cuerpo2"]) == pytest.approx(3.14159265 * 25 * 20, rel=1e-6)
    hueco = 3.14159265 * 400 * 20 - geo.volumen(cuerpos["Cuerpo1"])
    assert hueco == pytest.approx(3.14159265 * 5.075 ** 2 * 20, rel=1e-6)


def test_b609_herramienta_de_varios_solidos_y_mensaje_de_un_renglon(prefs, monkeypatch):
    """Una herramienta de dos pernos sueltos (un cuerpo «unido») se desfasa sólido por sólido; si el kernel no puede,
    el mensaje es de 1 renglón con el número de la casilla y coma."""
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import solidos_modificar as sm
    s = api.Sesion()
    _ok(s, "create_box", length=60, width=20, height=10, x=20, name="Molde")
    _ok(s, "create_cylinder", height=10, diameter=10, name="Pernos")
    _ok(s, "create_cylinder", height=10, diameter=10, x=40, operation="join", target="Pernos")
    _ok(s, "boolean_operation", target="Molde", tools=["Pernos"], operation="cut", keep_tools=True, print_clearance=0.1)
    molde = next(c.forma for c in s.doc.estado_final.cuerpos.values() if c.nombre == "Molde")
    assert geo.es_valida(molde)
    assert 12000 - geo.volumen(molde) == pytest.approx(2 * 3.14159265 * 5.1 ** 2 * 10, rel=1e-6)

    def falla(*_):
        raise geo.ErrorGeometria("detalle del kernel")
    monkeypatch.setattr(sm, "_desfase_cuerpo", falla)
    s = api.Sesion()
    _ok(s, "set_preference", key="impresion/holgura_mm", value=0.15)
    _perno_en_cilindro(s)
    r = api.llamar(s, "boolean_operation", {"target": "Cuerpo1", "tools": ["Cuerpo2"], "operation": "cut",
                                            "keep_tools": True, "print_clearance": "general"})
    assert not r["ok"] and r["mensaje"].endswith(": ⚠ No pude dejar 0,15 mm de holgura en esta pieza"), r
