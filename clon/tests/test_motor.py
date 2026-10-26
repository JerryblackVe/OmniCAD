# -*- coding: utf-8 -*-
"""Aislamiento de motores, preferencias y caché por documento."""
import importlib.util
import zipfile

import pytest
from PySide6.QtCore import QSettings

from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import motor
from omnicad.timeline import documento
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, Operacion
from omnicad.ui.preferencias import Preferencias


requiere_omnikernel = pytest.mark.skipif(importlib.util.find_spec("omnikernel") is None,
                                       reason="módulo Rust omnikernel sin compilar")


@pytest.fixture(autouse=True)
def preferencias_aisladas(monkeypatch):
    monkeypatch.setattr(motor, "_preferencias", None)


@requiere_omnikernel
def test_motor_se_guarda_en_ini_y_variable_tiene_prioridad(tmp_path, monkeypatch):
    monkeypatch.delenv("OMNICAD_MOTOR", raising=False)
    ruta = str(tmp_path / "ajustes.ini")
    p = Preferencias(QSettings(ruta, QSettings.IniFormat))
    p["geometria/motor"] = "omnikernel"
    p.q.sync()
    otra = Preferencias(QSettings(ruta, QSettings.IniFormat))
    assert otra["geometria/motor"] == "omnikernel"
    assert motor.motor_activo() == "omnikernel"
    monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
    assert motor.motor_activo() == "opencascade"


@requiere_omnikernel
def test_recalculo_fija_un_motor_y_cambiarlo_rehace_desde_cero(monkeypatch):
    observados = []

    class Sonda(Operacion):
        TIPO = "sonda_motor"

        def ejecutar(self, estado, ctx):
            observados.append(motor.motor_activo())
            estado.nuevo_cuerpo(self.id, geo.caja(10, 20, 30))
            monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
            observados.append(motor.motor_activo())
            estado.nuevo_cuerpo(self.id, geo.cilindro(10, 20))

    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    d = Documento()
    d.agregar(Sonda(d.nuevo_id()))
    assert observados == ["omnikernel", "omnikernel"]
    assert all(r.estado == "ok" for r in d.resultados)
    assert d.motor == "omnikernel"
    anteriores = [c.forma for c in d.estado_final.cuerpos.values()]
    d._cache[0] = object()  # ninguna entrada del motor anterior puede pasar al recálculo nuevo
    d.recalcular(1)
    assert observados == ["omnikernel", "omnikernel", "opencascade", "opencascade"]
    assert d.motor == "opencascade" and d._cache == {}
    assert all(r.estado == "ok" for r in d.resultados)
    assert all(c.forma is not f for c in d.estado_final.cuerpos.values() for f in anteriores)


@requiere_omnikernel
def test_formas_de_otro_motor_se_rechazan(monkeypatch):
    import omnikernel
    monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
    occ = geo.caja(10, 20, 30)
    omni = omnikernel.primitiva("caja", [10, 20, 30])
    for elegido, forma in (("omnikernel", occ), ("opencascade", omni)):
        monkeypatch.setenv("OMNICAD_MOTOR", elegido)
        with pytest.raises(geo.ErrorGeometria) as e:
            geo.volumen(forma)
        assert e.value.error_kind == "MOTOR_INCOMPATIBLE"


@requiere_omnikernel
def test_faltante_es_error_tipado_sin_respaldo(monkeypatch):
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    with pytest.raises(geo.ErrorGeometria) as e:
        geo.longitud(geo.caja(1, 2, 3))
    assert e.value.error_kind == "MOTOR_SIN_SOPORTE"
    assert str(e.value) == ("OmniKernel todavía no hace geometria.longitud. "
                            "Podés elegir OpenCascade en Preferencias.")


@requiere_omnikernel
def test_cache_nativa_reabre_y_opencascade_no_la_reutiliza(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", 0)
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), tipo="caja", ancho=10, largo=20, alto=30))
    ruta = proyecto.guardar(d, tmp_path / "caja.omnicad")
    with zipfile.ZipFile(ruta) as z:
        assert "cache/omnikernel/0.v1" in z.namelist()
        assert "cache/cuerpos.brep" not in z.namelist()
    llamadas = []
    original = OpPrimitiva.ejecutar

    def contar(self, estado, ctx):
        llamadas.append(motor.motor_activo())
        return original(self, estado, ctx)

    monkeypatch.setattr(OpPrimitiva, "ejecutar", contar)
    nativo = proyecto.abrir(ruta)
    assert llamadas == []
    assert nativo.motor == "omnikernel" and nativo.resultados[0].estado == "ok"
    monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
    occ = proyecto.abrir(ruta)
    assert llamadas == ["opencascade"]
    assert occ.resultados[0].estado == "ok"


@requiere_omnikernel
def test_funciones_sin_occ_son_comunes_a_los_dos_motores(monkeypatch):
    from omnicad.nucleo import perfiles
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    with pytest.raises(geo.ErrorGeometria) as e:
        geo.exigir_longitud(0, "La distancia")       # validación pura: no es MOTOR_SIN_SOPORTE
    assert getattr(e.value, "error_kind", None) is None
    assert perfiles.buscar_por_firma([], {1}) is None


@requiere_omnikernel
def test_tarea_aislada_con_omnikernel_no_tapa_el_faltante(monkeypatch):
    from omnicad.nucleo import aislado
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    with pytest.raises(geo.ErrorGeometria) as e:
        aislado.correr("autointersecciones", geo.caja(1, 2, 3), 5, limite=10)
    assert e.value.error_kind == "MOTOR_SIN_SOPORTE"


@requiere_omnikernel
def test_herramienta_set_geometry_engine_cambia_y_recalcula(monkeypatch):
    from omnicad import api
    from omnicad.api.sesion import Sesion
    monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
    s = Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 20, "height": 30})["ok"]
    r = api.llamar(s, "set_geometry_engine", {})
    assert r["ok"] and r["result"]["engine"] == "opencascade"
    r = api.llamar(s, "set_geometry_engine", {"engine": "omnikernel"})
    assert r["ok"] and r["result"]["engine"] == "omnikernel" and r["result"]["failed_steps"] == []
    assert s.doc.motor == "omnikernel"
    props = api.llamar(s, "get_physical_properties", {})["result"]["total"]
    assert abs(props["volume"] - 6000) < 1e-6
    assert not api.llamar(s, "set_geometry_engine", {"engine": "otro"})["ok"]


@pytest.mark.lento
@requiere_omnikernel
def test_prueba_humo_arranca_con_omnikernel_y_ocp_bloqueado():
    """La app abre con OmniKernel y sin OpenCascade y recorre la prueba de humo hasta el primer paso que el guion da
    por hecho con OpenCascade (hoy, la placa con agujero: MOTOR_SIN_SOPORTE). Lo que no puede pasar es un import de
    OCP o un error de import: eso querría decir que algo de la app todavía depende de OpenCascade."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    entorno = dict(os.environ, OMNICAD_MOTOR="omnikernel", OMNICAD_BLOQUEAR_OCP="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(raiz / "OmniCAD.py"), "--prueba-humo"], cwd=raiz, env=entorno,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    salida = p.stdout + p.stderr
    assert "OK    La ventana principal se muestra" in salida, salida[-3000:]
    assert salida.count("OK    ") >= 50, salida[-3000:]       # el visor, el ratón, los bocetos y el boceto 3D
    for prohibido in ("Import prohibido por OMNICAD_BLOQUEAR_OCP", "ModuleNotFoundError", "ImportError"):
        assert prohibido not in salida, salida[-3000:]


def test_metodos_de_clase_con_occ_no_corren_con_omnikernel(monkeypatch):
    plano = geo.Plano("XY")
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    assert list(plano.a_3d(1, 2)) == [1, 2, 0]               # numpy puro: común a los dos
    with pytest.raises(geo.ErrorGeometria) as e:
        plano.ax2()
    assert e.value.error_kind == "MOTOR_SIN_SOPORTE"
    monkeypatch.setenv("OMNICAD_MOTOR", "opencascade")
    assert plano.ax2(1, 2).Location().X() == 1.0


def test_preferencia_omnikernel_sin_modulo_usa_opencascade(monkeypatch):
    monkeypatch.delenv("OMNICAD_MOTOR", raising=False)
    monkeypatch.setattr(motor, "_preferencias", {"geometria/motor": "omnikernel"})
    monkeypatch.setattr(motor, "version_omnikernel", lambda: None)
    assert motor.motor_activo() == "opencascade"


def test_faltante_en_funcion_interna_nombra_la_operacion_publica(monkeypatch):
    from omnicad.nucleo import engranajes
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    with pytest.raises(geo.ErrorGeometria) as e:
        engranajes.engranaje(2.5, 30)           # el perfil usa `_linea`, interna y sin versión nativa
    assert e.value.error_kind == "MOTOR_SIN_SOPORTE"
    assert "engranajes.engranaje." in str(e.value) and "_linea" not in str(e.value)
