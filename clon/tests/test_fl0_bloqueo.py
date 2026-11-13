"""FL-0: el evento `bloqueo_ui` baja a 100 ms, lleva CPU y diálogo, y la suspensión de la PC no cuenta."""
from types import SimpleNamespace

import pytest

from omnicad import registro_uso as ru
from omnicad.registro_uso.detector import analizar
from omnicad.ui import bench, registro_uso
from omnicad.ui.registro_uso import RegistroVentana
from tests.test_registro_uso_mas import aislado, eventos  # noqa: F401  (fixture autouse: carpeta de registro propia)


def _latido(monkeypatch, ahora, ultimo, cpu_antes, cpu_ahora, t_accion=None):
    doble = SimpleNamespace(
        _ultima_accion="Rosca", _ultimo=ultimo, _pausado=False, _cpu_ultimo=cpu_antes,
        _capturar_error=lambda: None, _comando=lambda: "rosca",
        ventana=SimpleNamespace(panel=None), _rss=2**20, _muestra=ahora)
    if t_accion is not None:
        doble._t_accion = t_accion
    monkeypatch.setattr(registro_uso, "time", SimpleNamespace(perf_counter=lambda: ahora, process_time=lambda: cpu_ahora))
    monkeypatch.setattr(bench, "memoria_mb", lambda: (1, 0))
    monkeypatch.setattr(ru, "toca_podar", lambda: False)
    ru.configurar(True)
    try:
        RegistroVentana._latido(doble)
        ru.activo.cola.join()
        return [e["datos"] for e in eventos(ru.carpeta()) if e["tipo"] == "bloqueo_ui"]
    finally:
        ru.configurar(False)


def test_un_bloqueo_de_150_ms_ya_se_anota_con_su_cpu(monkeypatch):
    # 0,05 s es el período del latido: 0,2 s entre ticks = 150 ms de demora
    [b] = _latido(monkeypatch, ahora=1.2, ultimo=1.0, cpu_antes=0.0, cpu_ahora=0.14)
    assert b["duracion_ms"] == pytest.approx(150) and b["cpu_ms"] == 140
    assert "suspension_probable" not in b and "dialogo" not in b


def test_menos_de_100_ms_no_se_anota(monkeypatch):
    assert _latido(monkeypatch, ahora=1.12, ultimo=1.0, cpu_antes=0.0, cpu_ahora=0.0) == []


def test_mucho_rato_sin_gastar_cpu_se_marca_como_suspension_probable(monkeypatch):
    [b] = _latido(monkeypatch, ahora=601.0, ultimo=1.0, cpu_antes=0.0, cpu_ahora=0.2)
    assert b["duracion_ms"] > 590000 and b["suspension_probable"] is True


def test_mucho_rato_gastando_cpu_sigue_siendo_un_congelamiento(monkeypatch):
    [b] = _latido(monkeypatch, ahora=61.0, ultimo=1.0, cpu_antes=0.0, cpu_ahora=55.0)
    assert "suspension_probable" not in b


def test_el_detector_no_cuenta_la_suspension_pero_si_el_congelamiento_real():
    def ev(seq, datos):
        return {"t": seq * 10.0, "ts": f"2026-11-13T10:00:{seq:02d}+00:00", "seq": seq, "tipo": "bloqueo_ui", "datos": datos}
    real = ev(1, {"duracion_ms": 3000, "comando": "rosca", "accion": "rosca"})
    dormida = ev(10, {"duracion_ms": 554000, "comando": "abrir", "accion": "abrir", "suspension_probable": True})
    reglas = [h["regla"] for h in analizar([real, dormida])]
    assert reglas.count("bloqueo_ui") == 1


def test_una_accion_vieja_no_se_le_atribuye_al_bloqueo(monkeypatch):
    # Tocó «Rosca» en t=1; el bloqueo de 4 s empezó en t=5 (hace 4 s): no es culpa de Rosca.
    [b] = _latido(monkeypatch, ahora=9.05, ultimo=5.0, cpu_antes=0.0, cpu_ahora=3.9, t_accion=1.0)
    assert b["accion"] == "" and b["despues_de"] == "Rosca" and b["hace_s"] == 4


def test_una_accion_reciente_si_se_le_atribuye(monkeypatch):
    [b] = _latido(monkeypatch, ahora=1.7, ultimo=1.0, cpu_antes=0.0, cpu_ahora=0.6, t_accion=1.0)
    assert b["accion"] == "Rosca" and "despues_de" not in b
