"""FL-0: banco pesado de ventana real; ejecutar con xcb, xvfb y turno.py."""
import importlib.util
import json
import math
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.lento, pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen" or not os.environ.get("DISPLAY"),
    reason="El banco de fluidez necesita DISPLAY y QT_QPA_PLATFORM=xcb (xvfb-run -a); offscreen no tiene visor GL",
)]

RAIZ = Path(__file__).resolve().parents[2]
especificacion = importlib.util.spec_from_file_location("bench_fluidez", RAIZ / "scripts" / "bench_fluidez.py")
banco = importlib.util.module_from_spec(especificacion)
especificacion.loader.exec_module(banco)
PRESUPUESTOS = json.loads(Path(__file__).with_name("fluidez_presupuestos.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("letra", banco.ESCENARIOS)
def test_presupuesto_fluidez(letra, tmp_path):
    """Una corrida por escenario calibrado; los errores de calibración se omiten con motivo."""
    presupuestos = PRESUPUESTOS[letra]
    if motivo := presupuestos.get("motivo_omision"):
        assert all(presupuestos[m] is None for m in banco.METRICAS), presupuestos
        pytest.skip(f"{letra}: {motivo}")
    resultado = banco.correr_aislado(letra)
    (tmp_path / f"fluidez_{letra}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    if resultado.get("omitido"):
        pytest.skip(f"{letra}: {resultado['omitido']}")
    assert not resultado.get("colgado"), resultado
    assert "error" not in resultado, resultado
    for metrica in banco.METRICAS:
        valor = resultado[metrica]
        presupuesto = presupuestos[metrica]
        if presupuesto is None:
            assert valor is None, f"{letra}/{metrica}: falta calibrar el presupuesto ({valor} ms)"
        else:
            assert valor is not None and math.isfinite(valor), f"{letra}/{metrica}: medida perdida"
            assert valor <= presupuesto, f"{letra}/{metrica}: {valor} ms > {presupuesto} ms; {resultado}"


def test_mediana_conserva_errores_y_no_aplicables():
    corridas = [{"escenario": "g", "titulo": "Eliminar", "bloqueo_max_ms": v,
                 "primera_previa_ms": None, "aceptar_ms": None} for v in (40, 900, 60)]
    corridas[1]["error"] = "falló"
    corridas[1]["colgado"] = True
    resultado = banco.resumir(corridas)
    assert resultado["bloqueo_max_ms"] == 60
    assert resultado["primera_previa_ms"] is None and resultado["aceptar_ms"] is None
    assert resultado["error"] == "falló" and resultado["colgado"]
    assert resultado["detalle"]["corridas"] == corridas
