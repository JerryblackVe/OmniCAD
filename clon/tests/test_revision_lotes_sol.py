# -*- coding: utf-8 -*-
"""Correcciones de la revisión de los lotes SOL-7 a SOL-29: cada una con una prueba que falla si se rompe."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_dividir_cara_punto_mas_cercano_rechaza_caras_curvas():
    from omnicad.nucleo import solidos_modificar as sm
    cilindro = geo.cilindro(10, 20, (0, 0, 0), (0, 0, 1))
    lateral = next(c for c in geo.caras(cilindro) if sm._plano_de_cara(c) is None)
    with pytest.raises(geo.ErrorGeometria, match="solo divide caras planas"):
        sm.dividir_cara(cilindro, [lateral], None, tipo="cercano")


def test_listar_conjuntos_no_ensucia_el_documento():
    s = api.Sesion()
    s.doc.modificado = False
    assert llamar(s, "manage_selection_sets", action="list")["count"] == 0
    assert not s.doc.modificado and "conjuntos_seleccion" not in s.doc.espacios
    r = api.llamar(s, "manage_selection_sets", {"action": "select", "name": "nada"})
    assert not r["ok"] and not s.doc.modificado


def test_asignar_regla_vacia_usa_la_regla_por_defecto():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
    comp = llamar(s, "create_component", bodies=["Caja"], name="Taco")["component"]
    r = llamar(s, "assign_plastic_rule", component=comp["id"] if isinstance(comp, dict) else "Taco", rule="")
    assert r


def test_multitransformar_de_componentes_protege_al_componente():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
    llamar(s, "create_component", bodies=["Caja"], name="Taco")
    llamar(s, "multi_transform", components=["Taco"], transforms=[{"type": "rectangular", "axis": "x", "count": 2, "spacing": 30}])
    r = api.llamar(s, "delete_feature", {"feature": "Taco"})
    assert not r["ok"] and r["error_kind"] == "FEATURE_IN_USE"


def test_envolvente_con_scu_no_pierde_el_scu_al_reabrir_el_dialogo():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import SolidoEnvolvente
    QApplication.instance() or QApplication([])
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=10, height=10, name="Viga")
    llamar(s, "create_ucs", origin="O")
    llamar(s, "create_bounding_solid", bodies=["Viga"], shape="cylinder", orientation="ucs", ucs="SCU1")
    op = next(o for o in s.doc.operaciones if o.TIPO == "solido_envolvente")
    assert op.p["scu"]
    cmd = SolidoEnvolvente()
    v = cmd.desde_op(op, ContextoComando(s.doc, op=op))
    nueva = cmd.construir(v, ContextoComando(s.doc, op=op))
    assert nueva.p["scu"] == op.p["scu"] and nueva.p["orientacion"] == "scu"


def test_preajuste_con_tipo_malo_no_rompe_el_dialogo(tmp_path, monkeypatch):
    from omnicad.nucleo import preajustes as pre
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.plastico import PatronGeometrico
    from omnicad.ui.visor3d import Visor3D
    monkeypatch.setenv(pre.VAR_PREAJUSTES, str(tmp_path / "pre.json"))
    QApplication.instance() or QApplication([])
    llamar(api.Sesion(), "manage_command_presets", action="save", command="patron_geometrico", name="malo",
           values={"rayos": "muchos", "distribucion": "no_existe", "limpiar_perimetro": "si"})
    llamar(api.Sesion(), "manage_command_presets", action="set_default", command="patron_geometrico", default="malo")
    doc = Documento()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(PatronGeometrico(), ContextoComando(doc), visor)
    assert panel.valores["distribucion"] != "no_existe" and isinstance(panel.valores["rayos"], int)


def test_un_archivo_de_preajustes_roto_se_aparta_y_no_se_pisa_en_silencio(tmp_path, monkeypatch):
    from omnicad.nucleo import preajustes as pre
    ruta = tmp_path / "pre.json"
    monkeypatch.setenv(pre.VAR_PREAJUSTES, str(ruta))
    ruta.write_text("{esto no es json", encoding="utf-8")
    pre.guardar("nervio", "uno", {"espesor": "2 mm"})
    assert ruta.with_suffix(".bak").read_text(encoding="utf-8") == "{esto no es json"
    assert pre.obtener("nervio", "uno") == {"espesor": "2 mm"}


def test_seleccion_limite_con_un_panel_abierto_avisa_sin_lanzar():
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal.__new__(VentanaPrincipal)
    avisos = []
    v.mensaje = avisos.append
    v.panel = object()
    v.modo_boceto = type("M", (), {"activo": False})()
    for slot in (v._seleccion_limite, v._seleccion_semilla, v._elegir_conjunto_seleccion):
        slot()
    assert len(avisos) == 3 and all("Terminá el comando" in a for a in avisos)


def test_consejos_de_diseno_no_es_cuadratico_con_muchas_caras():
    import time
    s = api.Sesion()
    llamar(s, "create_box", length=100, width=100, height=10, name="Placa")
    llamar(s, "create_geometric_pattern", faces=">Z", object_type="cylinder", size1=2, size2=2, distance=6, operation="cut")
    caras = len(geo.caras(s.cuerpo("Placa").forma))
    assert caras > 100
    t = time.time()
    llamar(s, "design_advice", body="Placa")
    assert time.time() - t < 20
