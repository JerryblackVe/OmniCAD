"""scripts/tiempos.py: junta los JUnit XML del cierre y arma el ranking de tests y archivos lentos (paquete A de
docs/plan_velocidad.md)."""
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "tiempos.py"
repartir = runpy.run_path(str(SCRIPT))["repartir"]


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


@pytest.mark.parametrize("procesos", [1, 3, 4])
def test_tandas_por_tiempo_respetan_archivos_enteros_y_carga_por_proceso(procesos):
    archivos = [f"tests/test_{i}.py" for i in range(procesos + 1)]
    # La media da menos de 600 s, pero el último archivo tardaría 958 s en un trabajador.
    grupos = repartir(archivos, dict.fromkeys(archivos, 479), procesos)
    assert grupos == [archivos[:procesos], archivos[procesos:]]


@pytest.mark.parametrize("procesos, cantidad", [(1, 368), (4, 368), (4, 4 * 368)])
def test_tandas_de_archivos_chicos_incluyen_costo_fijo_por_proceso(procesos, cantidad):
    archivos = [f"tests/test_{i}.py" for i in range(cantidad)]
    grupos = repartir(archivos, dict.fromkeys(archivos, 0.5), procesos)
    assert [archivo for grupo in grupos for archivo in grupo] == archivos
    for grupo in grupos:
        carga = ((len(grupo) + procesos - 1) // procesos) * (0.5 + 3)
        assert carga <= 700
    if cantidad == 368 * procesos:
        assert len(grupos) > 1
    else:
        assert len(grupos) == 1


def test_sin_dato_cuenta_treinta_segundos_y_lista_vacia_no_crea_tanda():
    archivos = [f"tests/test_{i}.py" for i in range(21)]
    assert repartir(archivos, {}, procesos=1) == repartir(archivos, dict.fromkeys(archivos, 30), procesos=1)
    assert repartir(archivos, {}, procesos=1) == [archivos[:18], archivos[18:]]
    assert repartir([], {}) == []


@pytest.mark.parametrize("segundos", [-1, float("nan"), float("inf")])
def test_reparto_rechaza_tiempos_invalidos(segundos):
    with pytest.raises(ValueError, match="Tiempo inválido"):
        repartir(["tests/test_uno.py"], {"tests/test_uno.py": segundos})


@pytest.mark.parametrize("procesos", [0, -1])
def test_reparto_rechaza_cantidad_de_procesos_no_positiva(procesos):
    with pytest.raises(ValueError, match="procesos debe ser positiva"):
        repartir([], {}, procesos)


@pytest.mark.parametrize("segundos", [598, 950])
def test_archivo_mayor_de_600_con_costo_fijo_va_solo_y_avisa(capsys, segundos):
    assert repartir(["pesado", "otro"], {"pesado": segundos}) == [["pesado"], ["otro"]]
    assert f"Aviso: pesado tarda {segundos + 3:.1f} s; va solo" in capsys.readouterr().out


def test_cli_escribe_tandas_mas_lentas_primero_sin_modificar_el_json(tmp_path):
    lista = tmp_path / "lista.txt"
    lista.write_text("sin_dato\nrapido\nlento\nmediano\n", encoding="utf-8")
    mediciones = tmp_path / "tiempos.json"
    original = json.dumps({"archivos": {"rapido": 20, "lento": 590, "mediano": 540}})
    mediciones.write_text(original, encoding="utf-8")
    salida = tmp_path / "tandas"
    r = subprocess.run([sys.executable, str(SCRIPT), str(lista), "--tandas", str(salida),
                        "--mediciones", str(mediciones), "--procesos", "1"],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stderr
    assert "2 tandas, 1 procesos" in r.stdout
    assert [(p.name, p.read_text(encoding="utf-8")) for p in sorted(salida.iterdir())] == [
        ("parte_00", "lento\n"), ("parte_01", "mediano\nsin_dato\nrapido\n")]
    assert mediciones.read_text(encoding="utf-8") == original
