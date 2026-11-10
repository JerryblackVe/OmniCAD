"""`scripts/turno.py`: la fila respeta el orden de llegada (P-131)."""
import importlib.util
import threading
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "turno.py"
ESPEC = importlib.util.spec_from_file_location("turno", SCRIPT)
turno = importlib.util.module_from_spec(ESPEC)
ESPEC.loader.exec_module(turno)


def test_la_fila_respeta_el_orden_de_llegada_y_limpia_numeros_muertos(tmp_path, monkeypatch):
    monkeypatch.setattr(turno.tempfile, "tempdir", str(tmp_path))     # candados aislados de la PC
    muerto = tmp_path / "omnicad_turno_fila_00000000000000000001_1.lock"   # número de un proceso que ya murió
    muerto.write_text("")
    dormir = time.sleep
    # B consulta 50 veces más seguido que A: sin fila, B le gana el lugar aunque A llegó antes.
    monkeypatch.setattr(turno.time, "sleep", lambda s: dormir(0.5 if threading.current_thread().name == "A" else 0.01))
    ocupado = open(tmp_path / "omnicad_turno_0.lock", "a+")
    assert turno._tomar(ocupado)
    orden = []

    def esperar():
        candado = turno._esperar_lugar(1)
        orden.append(threading.current_thread().name)
        turno._soltar(candado)
        candado.close()

    a = threading.Thread(target=esperar, name="A")
    a.start()
    limite = time.monotonic() + 3
    while muerto.exists() and time.monotonic() < limite:
        dormir(0.02)
    dormir(0.1)
    b = threading.Thread(target=esperar, name="B")
    b.start()
    dormir(0.2)
    turno._soltar(ocupado)
    ocupado.close()
    a.join(10)
    b.join(10)
    assert orden == ["A", "B"]
    assert not muerto.exists()
    assert not list(tmp_path.glob("omnicad_turno_fila_*"))
