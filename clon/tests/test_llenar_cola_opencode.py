# -*- coding: utf-8 -*-
"""scripts/llenar_cola_opencode.py: llena la reserva sin repetir tareas ni tocar lo que está en ahora.md."""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _modulo(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIA_COLA", str(tmp_path / "cola"))
    monkeypatch.setenv("LLENAR_BRIEFS", str(tmp_path / "briefs"))
    spec = importlib.util.spec_from_file_location("llenar", RAIZ / "scripts/llenar_cola_opencode.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for c in m.CARPETAS:
        (m.COLA / c).mkdir(parents=True, exist_ok=True)
    return m


def test_no_repite_lo_que_ya_existe_por_nombre_o_por_id(tmp_path, monkeypatch):
    m = _modulo(tmp_path, monkeypatch)
    (m.COLA / "hechos" / "96_FIX-B-697.tarea").write_text("WT=x\n")
    (m.COLA / "corriendo" / "PREP-TEST-k1.tarea").write_text("WT=x\n")
    ya = m.existentes()
    assert {"FIX-B-697", "PREP-TEST-k1", "B-697"} <= ya


def test_llena_hasta_el_tope_y_no_pisa_ahora(tmp_path, monkeypatch):
    m = _modulo(tmp_path, monkeypatch)
    monkeypatch.setattr(m, "candidatas", lambda: iter([("PREP-TEST-a", "x"), ("FIX-B-1", "y"), ("FIX-B-2", "z")]))
    monkeypatch.setattr(m, "existentes", lambda: {"FIX-B-1"})
    monkeypatch.setattr("sys.argv", ["x", "--tope", "2", "--seco"])
    assert m.main() is None                      # --seco: no crea worktrees ni archivos
    assert not list((m.COLA / "reserva").glob("*.tarea"))


def test_filas_abiertas_solo_boceto_abiertas_y_fuera_de_ahora():
    spec = importlib.util.spec_from_file_location("llenar2", RAIZ / "scripts/llenar_cola_opencode.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ids = {i for i, _ in m.filas_abiertas()}
    ahora = (m.SEGUIMIENTO / "ahora.md").read_text(encoding="utf-8")
    assert not any(i in ahora for i in ids)
    assert all(i.startswith("B-") for i in ids)
