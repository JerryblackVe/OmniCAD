# -*- coding: utf-8 -*-
"""Informes de error por sesión (pendiente 20): cada error no capturado queda en un archivo de
informes/ sin pisar el anterior, con fecha, versión, traza y los últimos pasos del timeline."""
import sys
import threading
import time
from pathlib import Path

import pytest

from omnicad import VERSION, informes_error
from omnicad import api


@pytest.fixture()
def sesion_limpia(tmp_path, monkeypatch):
    """Instala el capturador con una carpeta temporal y lo DESINSTALA al salir (el excepthook de pytest
    y el faulthandler global vuelven a como estaban)."""
    antes_principal, antes_hilos = sys.excepthook, threading.excepthook
    informes_error._E = informes_error._Estado()          # ninguna sesión abierta
    informes_error.instalar(carpeta=tmp_path)
    yield tmp_path
    sys.excepthook, threading.excepthook = antes_principal, antes_hilos
    informes_error._E = informes_error._Estado()
    informes_error.faulthandler.disable()


def _disparar(excepthook, tipo=ValueError, mensaje="algo se rompió"):
    try:
        raise tipo(mensaje)
    except tipo as e:
        excepthook(tipo, e, e.__traceback__)


def test_un_error_queda_escrito_con_fecha_version_y_traza(capsys, sesion_limpia):
    informes_error.poner_contexto(lambda: ["op1 Caja 30 mm", "op2 Empalme 3 mm"])
    _disparar(sys.excepthook)
    capsys.readouterr()                       # el gancho también imprime la traza: no importa acá
    informes = informes_error.listar(sesion_limpia)
    assert len(informes) == 1
    texto = informes_error.leer(informes[0]["name"], sesion_limpia)
    assert f"OmniCAD {VERSION}" in texto                       # versión
    assert "ValueError: algo se rompió" in texto                # traza
    assert time.strftime("%Y-%m-%d") in texto                    # fecha
    assert "op1 Caja 30 mm" in texto and "op2 Empalme 3 mm" in texto   # últimos pasos del timeline


def test_la_sesion_no_se_pisa_y_los_errores_se_acumulan(sesion_limpia):
    primera = informes_error._E.archivo
    _disparar(sys.excepthook, IndexError, "uno")
    _disparar(sys.excepthook, TypeError, "dos")
    assert [r["name"] for r in informes_error.listar(sesion_limpia)] == [primera.name]
    texto = primera.read_text(encoding="utf-8")
    assert "IndexError: uno" in texto and "TypeError: dos" in texto


def test_el_gancho_principal_avisa_con_la_ruta_del_informe(sesion_limpia):
    avisados = []
    informes_error.instalar(avisar=avisados.append, carpeta=sesion_limpia)
    _disparar(sys.excepthook, TypeError, "plop")
    assert avisados and avisados[0] == informes_error._E.archivo
    assert "TypeError: plop" in avisados[0].read_text(encoding="utf-8")


def test_el_gancho_de_hilos_registra_el_error_del_hilo(sesion_limpia):
    from types import SimpleNamespace
    try:
        raise RuntimeError("en un hilo")
    except RuntimeError as e:
        args = SimpleNamespace(exc_type=RuntimeError, exc_value=e, exc_traceback=e.__traceback__,
                               thread=None, name="hilo de prueba")
        threading.excepthook(args)
    texto = informes_error._E.archivo.read_text(encoding="utf-8")
    assert "RuntimeError: en un hilo" in texto and "Error en el hilo" in texto


def test_podar_conserva_los_ultimos_20(sesion_limpia):
    import os
    for i in range(25):
        archivo = sesion_limpia / f"sesion-vieja-{i:02}.txt"
        archivo.write_text(f"informe {i}", encoding="utf-8")
        mtime = archivo.stat().st_mtime - (30 - i) * 60      # cuanto más chico i, más viejo
        os.utime(archivo, (mtime, mtime))
    assert informes_error.podar(sesion_limpia) == 5                                  # 25 viejos − 20
    nombres = [r["name"] for r in informes_error.listar(sesion_limpia)]
    assert len(nombres) == 21                                  # 20 viejos + el de esta sesión
    assert "sesion-vieja-00.txt" not in nombres and "sesion-vieja-04.txt" not in nombres
    assert "sesion-vieja-05.txt" in nombres and "sesion-vieja-24.txt" in nombres
    assert informes_error._E.archivo.name in nombres           # el de la sesión abierta nunca se borra


def test_leer_rechaza_rutas_que_escapan_de_la_carpeta(sesion_limpia):
    with pytest.raises(FileNotFoundError):
        informes_error.leer("../otra/cosa.txt", sesion_limpia)


def test_ultimo_error_y_el_issue_no_lleva_rutas_de_la_casa(sesion_limpia):
    informes_error._E.contexto = lambda: []
    _disparar(sys.excepthook, ValueError, "cosas")
    nombre = informes_error.listar(sesion_limpia)[0]["name"]
    tipo, mensaje = informes_error.ultimo_error(informes_error.leer(nombre, sesion_limpia))
    assert (tipo, mensaje) == ("ValueError", "cosas")
    cuerpo = informes_error.resumen_issue(nombre, sesion_limpia)
    assert str(Path.home()) not in cuerpo                     # sin rutas del usuario
    url = informes_error.url_issue(nombre, sesion_limpia)
    assert url.startswith("https://github.com/JerryblackVe/OmniCAD/issues/new?title=Error%3A")
    assert str(Path.home()) not in url


def test_url_issue_sin_informes_igual_trae_version_y_sistema(tmp_path, monkeypatch):
    from urllib.parse import unquote
    monkeypatch.setattr(informes_error, "carpeta_informes", lambda: tmp_path)
    url = informes_error.url_issue()
    assert f"OmniCAD {VERSION}" in unquote(url)                 # el cuerpo lleva versión y sistema


# ---------------------------------------------------------------- herramientas de la API (grupo dev)
def test_api_lista_y_lee_los_informes(tmp_path, monkeypatch):
    (tmp_path / "sesion-20260101-000000-1.txt").write_text("=== OmniCAD ===\n--- Error ---\n"
                                                           "ValueError: de prueba", encoding="utf-8")
    monkeypatch.setattr(informes_error, "carpeta_informes", lambda: tmp_path)
    r = api.llamar(api.Sesion(), "list_error_reports", {})
    assert r["ok"] and [x["name"] for x in r["result"]["reports"]] == ["sesion-20260101-000000-1.txt"]
    r = api.llamar(api.Sesion(), "read_error_report", {"name": "sesion-20260101-000000-1.txt"})
    assert r["ok"] and "ValueError: de prueba" in r["result"]["text"]
    r = api.llamar(api.Sesion(), "read_error_report", {"name": "no-existe.txt"})
    assert not r["ok"] and r["error_kind"] == "FILE_NOT_FOUND"
    r = api.llamar(api.Sesion(), "read_error_report", {})      # vacío = el más reciente
    assert r["ok"] and r["result"]["name"] == "sesion-20260101-000000-1.txt"
