# -*- coding: utf-8 -*-
"""B-160: un STEP ajeno dañado no puede cerrar el proceso que lo abre."""
from pathlib import Path
import sys

import pytest

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import intercambio
from omnicad.nucleo import motor


ROTO = Path(__file__).parent / "corpus_caza" / "b160_step_roto.step"


@pytest.mark.parametrize("lector", [intercambio.leer_step_estructura, intercambio.leer_step])
def test_b160_step_roto_da_error_sin_matar_el_proceso(lector):
    with pytest.raises(geo.ErrorGeometria, match="El archivo STEP está dañado"):
        lector(ROTO)
    assert geo.es_valida(geo.caja(1, 2, 3))


def test_b160_open_document_roto_conserva_el_documento():
    sesion = api.Sesion()
    anterior = sesion.doc
    respuesta = api.llamar(sesion, "open_document", {"path": str(ROTO.resolve())})
    assert respuesta["ok"] is False
    assert "El archivo STEP está dañado" in respuesta["mensaje"]
    assert sesion.doc is anterior
    assert geo.es_valida(geo.caja(1, 2, 3))


@pytest.mark.parametrize("lector,formato", [(intercambio.leer_step, "STEP"),
                                           (intercambio.leer_step_estructura, "STEP"),
                                           (intercambio.leer_iges, "IGES")])
@pytest.mark.parametrize("modo", ["caida", "plazo"])
def test_b160_hijo_caido_o_colgado_da_error_claro(monkeypatch, lector, formato, modo):
    codigo = ("import os; os._exit(-1073741819) if os.name == 'nt' else os.kill(os.getpid(), 11)"
              if modo == "caida" else "import time; time.sleep(60)")
    monkeypatch.setattr(aislado, "_comando", lambda *args: [sys.executable, "-c", codigo])
    monkeypatch.setattr(aislado, "TOPE_ENSAYO_LECTURA", 10 if modo == "caida" else 0.2)
    with pytest.raises(geo.ErrorGeometria, match=f"El archivo {formato} está dañado") as fallo:
        lector(ROTO)
    assert isinstance(fallo.value.__cause__, aislado.TareaAislada)
    assert ("error nativo" if modo == "caida" else "se cortó") in str(fallo.value)
    assert geo.es_valida(geo.caja(1, 2, 3))


@pytest.mark.parametrize("formato", ["STEP", "STEP_ESTRUCTURA", "IGES"])
def test_b160_archivos_validos_y_lectura_dentro_del_hijo(tmp_path, monkeypatch, formato):
    ruta = tmp_path / ("caja.igs" if formato == "IGES" else "caja.step")
    escritor = intercambio.escribir_iges if formato == "IGES" else intercambio.escribir_step
    escritor(geo.caja(1, 2, 3), ruta)
    lector = {"STEP": intercambio.leer_step, "STEP_ESTRUCTURA": intercambio.leer_step_estructura,
              "IGES": intercambio.leer_iges}[formato]
    lector(ruta)     # el ensayo y la lectura real terminan; los siguientes ensayos reusan el trabajador
    trabajador = aislado._trabajador
    resultado = lector(ruta)
    assert aislado._trabajador is trabajador
    forma = resultado["cuerpos"][0]["forma"] if formato == "STEP_ESTRUCTURA" else resultado
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(6)

    def no_recursar(*args, **kwargs):
        pytest.fail("Una lectura dentro del hijo no debe pedir otro ensayo")

    monkeypatch.setattr(aislado, "EN_HIJO", True)
    monkeypatch.setattr(aislado, "correr_json", no_recursar)
    lector(ruta)


def test_b160_tarea_json_por_correr_con_omnikernel(tmp_path):
    """Sin formas, _correr sigue aislando OCC aunque el padre tenga elegido OmniKernel."""
    ruta = tmp_path / "caja.step"
    intercambio.escribir_step(geo.caja(1, 2, 3), ruta)
    with motor.fijar_motor("omnikernel"), aislado._ocupado:
        assert aislado.correr_json("ensayar_lectura", {"ruta": str(ruta), "formato": "STEP"}, 60) == {"ok": True}
        with pytest.raises(aislado.TareaAislada, match="error nativo"):
            aislado.correr_json("ensayar_lectura", {"ruta": str(ROTO), "formato": "STEP_ESTRUCTURA"}, 60)
    assert aislado._trabajador is None
