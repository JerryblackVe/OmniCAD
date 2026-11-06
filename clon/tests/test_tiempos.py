"""scripts/tiempos.py: junta los JUnit XML del cierre y arma el ranking de tests y archivos lentos (paquete A de
docs/plan_velocidad.md)."""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "tiempos.py"


def _xml(carpeta, nombre, casos, envolver=False):
    """Escribe un JUnit mínimo; casos = [(classname, name, time)]."""
    cuerpo = "".join(f'<testcase classname="{c}" name="{n}" time="{t}" />' for c, n, t in casos)
    suite = f'<testsuite name="{nombre}" tests="{len(casos)}">{cuerpo}</testsuite>'
    (carpeta / f"{nombre}.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        + (f"<testsuites>{suite}</testsuites>" if envolver else suite), encoding="utf-8")


def _correr(carpeta, salida):
    return subprocess.run([sys.executable, str(SCRIPT), str(carpeta), "--salida", str(salida)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})   # la consola de Windows no es UTF-8


def test_segundos_por_test_y_por_archivo_y_orden_impreso(tmp_path):
    _xml(tmp_path, "t1", [("tests.test_uno", "test_a", "1.50"), ("tests.test_uno.TestClase", "test_b", "0.25")])
    _xml(tmp_path, "t2", [("tests.test_dos", "test_c", "2.00")], envolver=True)      # envuelto en testsuites
    salida = tmp_path / "sub" / "tiempos.json"
    r = _correr(tmp_path, salida)
    assert r.returncode == 0, r.stderr
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["tests"] == {"tests/test_uno.py::test_a": 1.5, "tests/test_uno.py::TestClase::test_b": 0.25,
                              "tests/test_dos.py::test_c": 2.0}
    assert datos["archivos"] == {"tests/test_uno.py": 1.75, "tests/test_dos.py": 2.0}
    assert datos["total"] == 3.75
    assert datos["fuentes"] == ["t1.xml", "t2.xml"]
    assert [l.split()[-1] for l in r.stdout.splitlines() if "::" in l] == [
        "tests/test_dos.py::test_c", "tests/test_uno.py::test_a", "tests/test_uno.py::TestClase::test_b"]
    assert [l.split()[-1] for l in r.stdout.splitlines() if l.strip().endswith(".py")] == [
        "tests/test_dos.py", "tests/test_uno.py"]


def test_carpeta_sin_xml_falla(tmp_path):
    r = _correr(tmp_path, tmp_path / "tiempos.json")
    assert r.returncode != 0
    assert "no hay ningún *.xml" in r.stderr
    assert not (tmp_path / "tiempos.json").exists()
