"""B-272: los archivos que lanzan la app entera corren en su propio lote de suite_pc.py."""
import importlib.util
from pathlib import Path

ESPEC = importlib.util.spec_from_file_location(
    "suite_pc", Path(__file__).resolve().parents[2] / "scripts" / "suite_pc.py")
suite_pc = importlib.util.module_from_spec(ESPEC)
ESPEC.loader.exec_module(suite_pc)


def test_armar_lotes_deja_los_solos_aparte_y_cada_archivo_una_vez():
    archivos = [f"tests/test_{c}.py" for c in "abcde"] + ["tests/test_motor.py", "tests/test_z.py"]
    lotes = suite_pc.armar_lotes(archivos, 3)
    assert ["tests/test_motor.py"] in lotes
    assert sorted(a for lote in lotes for a in lote) == sorted(archivos)
    assert all(len(lote) <= 3 for lote in lotes)
