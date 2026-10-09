# -*- coding: utf-8 -*-
"""Herramientas de desarrollo (grupo "dev"): `run_checks`, `app_screenshot` y la CLI `omnicad dev`."""
import json
import struct
from pathlib import Path

import pytest

from omnicad import api
from omnicad.api import herramientas_dev as hd
from omnicad.cli import main
from omnicad.ejemplo import crear_documento_ejemplo

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
ARCHIVO_RAPIDO = "tests/test_parametros.py"   # chico y sin Qt: pytest termina en pocos segundos


@pytest.fixture(autouse=True)
def sin_marca_de_anidado(monkeypatch):
    """Si esta suite la lanzó `omnicad dev check`, el proceso trae la marca de run_checks: se saca para que los tests
    de run_checks prueben la herramienta (los reales corren un archivo chico fijo, nunca la suite entera)."""
    monkeypatch.delenv(hd.VAR_ANIDADO, raising=False)


def resultado_ok(r):
    assert r["ok"], r
    return r["result"]


def promedio_gris(ruta):
    """Brillo medio (0 a 255) de la parte de arriba de un PNG: la barra y la cinta, que cambian con el tema."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    img = QImage(str(ruta))
    assert not img.isNull(), ruta
    c = img.copy(0, 0, img.width(), 80).scaled(1, 1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).pixelColor(0, 0)
    return (c.red() + c.green() + c.blue()) / 3


def sin_pantalla(r):
    """True si la captura no pudo abrir la ventana (no hay escritorio u OpenGL): el test se salta."""
    return not r["ok"] and "No hay pantalla u OpenGL" in r["mensaje"]


def simular_pasos(monkeypatch, pytest_codigo=0):
    """Reemplaza los subprocesos de ruff, pytest y la prueba de humo por salidas fijas (argv[2] dice el paso)."""
    def simulado(argv, timeout):
        if argv[2] == "ruff":
            return 0, "All checks passed!\n"
        if argv[2] == "pytest":
            if pytest_codigo == 0:
                return 0, "5 passed in 0.20s\n"
            return 1, "FAILED tests/test_z.py::test_roto - AssertionError\n1 failed, 4 passed in 0.30s\n"
        return 0, "OK    carga\nResultado: TODO OK (1/1)\n"
    monkeypatch.setattr(hd, "_correr", simulado)


def test_grupo_dev_registrado():
    herramientas = {h["nombre"]: h for h in api.catalogo("dev")}
    assert set(herramientas) == {"run_checks", "app_screenshot"}
    assert not any(h["modifica"] for h in herramientas.values())


# ---------------------------------------------------------------- parseo puro (sin subprocesos)
def test_parseo_de_pytest_con_fallas():
    texto = ("..F.\n"
             "=========== short test summary info ===========\n"
             "FAILED tests/test_a.py::test_x - AssertionError: 1 != 2\n"
             "FAILED tests/test_b.py::test_y - KeyError: 'ancho'\n"
             "2 failed, 40 passed in 3.10s\n")
    assert hd.parsear_pytest(texto, 1) == {
        "ok": False, "summary": "2 failed, 40 passed in 3.10s",
        "failed": ["FAILED tests/test_a.py::test_x - AssertionError: 1 != 2",
                   "FAILED tests/test_b.py::test_y - KeyError: 'ancho'"]}


def test_parseo_de_pytest_verde_y_lista_recortada():
    assert hd.parsear_pytest("972 passed in 74.11s\n", 0) == {
        "ok": True, "summary": "972 passed in 74.11s", "failed": []}
    muchas = "".join(f"FAILED tests/t.py::t{i}\n" for i in range(30))
    assert len(hd.parsear_pytest(muchas + "30 failed\n", 1)["failed"]) == hd.TOPE_LINEAS


def test_parseo_de_humo_y_de_ruff():
    assert hd.parsear_humo("OK    carga ejemplo\nFALLA  cinta\nResultado: 1 FALLA de 2\n", 1) == {
        "ok": False, "summary": "Resultado: 1 FALLA de 2", "failures": ["FALLA  cinta"]}
    assert hd.parsear_humo("OK a\nOK b\nResultado: TODO OK (2/2)\n", 0) == {
        "ok": True, "summary": "Resultado: TODO OK (2/2)", "failures": []}
    # sin líneas FALLA pero con código de error: se devuelven las líneas que no son OK (p. ej. un traceback)
    assert hd.parsear_humo("OK a\nTraceback (most recent call last):\nValueError: x\n", 1)["failures"] == [
        "Traceback (most recent call last):", "ValueError: x"]
    assert hd.parsear_ruff("All checks passed!\n", 0) == {"ok": True, "summary": "All checks passed!"}
    assert hd.parsear_ruff("Found 2 errors.\n", 1) == {"ok": False, "summary": "Found 2 errors."}


def test_run_checks_marca_timeout_y_sigue_con_los_demas_pasos(monkeypatch):
    def simulado(argv, timeout):
        if argv[2] == "ruff":
            return None, ""                       # ruff pasó el tiempo máximo
        return 0, "5 passed in 0.20s\n"
    monkeypatch.setattr(hd, "_correr", simulado)
    r = resultado_ok(api.llamar(api.Sesion(), "run_checks", {"include_smoke": False}))
    assert r["ruff"]["ok"] is False and "timeout" in r["ruff"]["summary"]
    assert r["pytest"]["ok"] and r["pytest"]["summary"] == "5 passed in 0.20s"
    assert r["smoke"] is None and r["ok"] is False


def test_run_checks_no_se_anida(monkeypatch):
    """Dentro de una verificación lanzada por run_checks, run_checks se niega en vez de correr otra suite entera."""
    def no_deberia_correr(argv, timeout):
        raise AssertionError(f"lanzó un subproceso anidado: {argv}")
    monkeypatch.setattr(hd, "_correr", no_deberia_correr)
    monkeypatch.setenv(hd.VAR_ANIDADO, "1")
    r = api.llamar(api.Sesion(), "run_checks", {"include_smoke": False})
    assert not r["ok"] and r["error_kind"] == "NESTED_CHECKS", r


def test_run_checks_marca_sus_subprocesos(monkeypatch):
    """El subproceso real lleva la marca: si la suite hija llamara a run_checks, se negaría."""
    monkeypatch.delenv(hd.VAR_ANIDADO, raising=False)
    codigo, salida = hd._correr([hd.sys.executable, "-c", f"import os; print(os.environ.get('{hd.VAR_ANIDADO}'))"], 60)
    assert codigo == 0 and salida.strip() == "1"


def test_run_checks_todo_verde_y_con_humo(monkeypatch):
    simular_pasos(monkeypatch)
    r = resultado_ok(api.llamar(api.Sesion(), "run_checks", {}))
    assert r["ok"] is True and r["smoke"]["ok"] is True
    assert r["smoke"]["summary"] == "Resultado: TODO OK (1/1)"


# ---------------------------------------------------------------- pytest y ruff reales (un archivo chico)
def test_run_checks_real_corre_un_archivo_sin_humo():
    r = resultado_ok(api.llamar(api.Sesion(), "run_checks",
                                {"include_smoke": False, "pytest_args": ARCHIVO_RAPIDO}))
    assert r["smoke"] is None
    assert r["pytest"]["ok"] and "passed" in r["pytest"]["summary"], r["pytest"]
    assert r["ok"] == (r["ruff"]["ok"] and r["pytest"]["ok"])


def test_run_checks_real_reporta_una_ruta_inexistente():
    r = resultado_ok(api.llamar(api.Sesion(), "run_checks",
                                {"include_smoke": False, "pytest_args": "tests/no_existe_nunca.py"}))
    assert r["pytest"]["ok"] is False and r["ok"] is False


# ---------------------------------------------------------------- captura de la ventana real
def test_app_screenshot_validaciones():
    casos = [({"example": True, "project": "x.omnicad"}, "INVALID_ARGUMENTS"),
             ({"width": 100}, "INVALID_ARGUMENTS"),
             ({"project": "no_existe_nunca.omnicad"}, "FILE_NOT_FOUND"),
             ({"theme": "no_existe_nunca"}, "INVALID_ARGUMENTS")]
    for args, kind in casos:
        r = api.llamar(api.Sesion(), "app_screenshot", args)
        assert r["ok"] is False and r["error_kind"] == kind, (args, r)


def test_app_screenshot_ejemplo_png_del_tamano_pedido(tmp_path):
    destino = tmp_path / "ejemplo.png"
    r = api.llamar(api.Sesion(), "app_screenshot",
                   {"example": True, "width": 800, "height": 500, "path": str(destino)})
    if sin_pantalla(r):
        pytest.skip(f"sin pantalla u OpenGL: {r['mensaje']}")
    img = resultado_ok(r)
    assert img["image"].png[:8] == FIRMA_PNG
    assert struct.unpack(">II", img["image"].png[16:24]) == (800, 500)
    assert (img["image"].ancho, img["image"].alto) == (800, 500)
    assert Path(img["path"]) == destino.resolve() and destino.is_file()


def test_app_screenshot_con_tema_cambia_los_colores_de_la_ventana(tmp_path):
    colores = {}
    for tema in ("oscuro_moderno", "claro_moderno"):
        r = api.llamar(api.Sesion(), "app_screenshot", {"example": True, "width": 480, "height": 300, "theme": tema,
                                                        "path": str(tmp_path / f"{tema}.png")})
        if sin_pantalla(r):
            pytest.skip(f"sin pantalla u OpenGL: {r['mensaje']}")
        img = resultado_ok(r)
        assert (img["image"].ancho, img["image"].alto) == (480, 300)
        colores[tema] = promedio_gris(tmp_path / f"{tema}.png")
    assert colores["claro_moderno"] > colores["oscuro_moderno"] + 60, colores     # claro frente a oscuro


def test_app_screenshot_sin_path_no_devuelve_ruta(tmp_path):
    r = api.llamar(api.Sesion(), "app_screenshot", {"width": 320, "height": 240})
    if sin_pantalla(r):
        pytest.skip(f"sin pantalla u OpenGL: {r['mensaje']}")
    img = resultado_ok(r)
    assert img["path"] is None
    assert (img["image"].ancho, img["image"].alto) == (320, 240)


def test_app_screenshot_abre_un_proyecto_guardado(tmp_path):
    ruta = tmp_path / "ejemplo.omnicad"
    guardar = api.Sesion(crear_documento_ejemplo())
    resultado_ok(api.llamar(guardar, "save_document", {"path": str(ruta)}))
    r = api.llamar(api.Sesion(), "app_screenshot", {"project": str(ruta), "width": 480, "height": 300})
    if sin_pantalla(r):
        pytest.skip(f"sin pantalla u OpenGL: {r['mensaje']}")
    img = resultado_ok(r)
    assert (img["image"].ancho, img["image"].alto) == (480, 300)


# ---------------------------------------------------------------- CLI `omnicad dev`
def test_cli_dev_uso_incorrecto(tmp_path):
    assert main(["dev"]) == 2
    assert main(["dev", "screenshot", str(tmp_path / "x.jpg")]) == 2
    assert main(["dev", "screenshot", str(tmp_path / "x.png"), "--size", "grande"]) == 2
    assert main(["dev", "screenshot", str(tmp_path / "x.png"), "--example",
                 "--project", str(tmp_path / "y.omnicad")]) == 2
    assert main(["dev", "screenshot", str(tmp_path / "x.png"), "--project", str(tmp_path / "y.omnicad")]) == 2
    assert main(["dev", "screenshot", str(tmp_path / "x.png"), "--theme", "no_existe_nunca"]) == 1


def test_cli_dev_check_resume_y_sale_0(capsys, monkeypatch):
    simular_pasos(monkeypatch)
    assert main(["dev", "check"]) == 0
    salida = capsys.readouterr().out
    assert "All checks passed!" in salida and "5 passed" in salida and "TODO OK" in salida
    assert "OK: " in salida


def test_cli_dev_check_con_falla_sale_1(capsys, monkeypatch):
    simular_pasos(monkeypatch, pytest_codigo=1)
    assert main(["dev", "check", "--no-smoke"]) == 1
    salida = capsys.readouterr().out
    assert "FALLA" in salida and "FAILED tests/test_z.py::test_roto" in salida


def test_cli_dev_check_json_es_el_dict_de_la_api(capsys, monkeypatch):
    simular_pasos(monkeypatch)
    assert main(["dev", "check", "--json", "--no-smoke"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["ok"] is True and datos["result"]["smoke"] is None


def test_cli_dev_check_json_con_falla_sale_1(capsys, monkeypatch):
    simular_pasos(monkeypatch, pytest_codigo=1)
    assert main(["dev", "check", "--json", "--no-smoke"]) == 1
    datos = json.loads(capsys.readouterr().out)
    assert datos["ok"] is True and datos["result"]["ok"] is False


def test_cli_dev_screenshot_real(tmp_path, capsys):
    destino = tmp_path / "cli.png"
    codigo = main(["dev", "screenshot", str(destino), "--example", "--size", "480x300"])
    salida = capsys.readouterr()
    if codigo == 1 and "No hay pantalla u OpenGL" in salida.err + salida.out:
        pytest.skip("sin pantalla u OpenGL")
    assert codigo == 0 and destino.is_file()
    assert "480x300" in salida.out
