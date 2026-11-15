# -*- coding: utf-8 -*-
"""B-509: las sesiones del servidor MCP y del CLI autoguardan como la ventana (misma carpeta e intervalo): un agente
que se cae no pierde lo que no guardó. Las sesiones que la ventana arma sobre su documento no autoguardan."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

from omnicad import api
from omnicad.api import sesion as modulo_sesion
from omnicad.cli import main
from omnicad.io_archivos import proyecto

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(proyecto, "carpeta_autoguardado", lambda: tmp_path)
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "preferencias.ini"))     # intervalo por defecto: 1 min
    return tmp_path


def _parametro(sesion, nombre):
    r = api.llamar(sesion, "create_parameter", {"name": nombre, "expression": "1 mm"})
    assert r["ok"], r
    proyecto.esperar_autoguardado()


def _recuperado(copia):
    s = api.Sesion()
    assert api.llamar(s, "recover_document", {"path": str(copia)})["ok"]
    return [p["name"] for p in api.llamar(s, "get_parameters", {"user_only": True})["result"]["parameters"]]


def test_la_sesion_autoguarda_al_primer_cambio_con_tope_y_se_recupera(carpeta, tmp_path, monkeypatch):
    s = api.Sesion(autoguardado=True)
    _parametro(s, "a")
    (copia,) = proyecto.autoguardados_pendientes()
    assert _recuperado(copia) == ["a"]                         # se recupera lo que no se guardó

    marca = copia.stat().st_mtime_ns
    _parametro(s, "b")                                         # dentro del minuto: no se reescribe
    assert copia.stat().st_mtime_ns == marca and _recuperado(copia) == ["a"]
    monkeypatch.setattr(modulo_sesion, "_intervalo_autoguardado", lambda: 0)
    _parametro(s, "c")                                         # pasó el intervalo: copia nueva
    assert _recuperado(copia) == ["a", "b", "c"]

    assert api.llamar(s, "save_document", {"path": str(tmp_path / "pieza.omnicad")})["ok"]
    assert not proyecto.autoguardados_pendientes() and not proyecto.ruta_autoguardado(s.doc).exists()


def test_sin_pedirlo_no_autoguarda_ni_falla_la_llamada_si_no_puede(carpeta, monkeypatch):
    _parametro(api.Sesion(), "a")                              # la de la ventana o una vista previa
    assert not proyecto.autoguardados_pendientes()

    def roto(*_a, **_k):
        raise OSError("disco lleno")
    monkeypatch.setattr(proyecto, "autoguardar_en_hilo", roto)
    _parametro(api.Sesion(autoguardado=True), "b")             # la herramienta salió bien igual


def test_el_servidor_mcp_deja_la_copia_si_el_agente_no_guardo(tmp_path):
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters
    parametros = StdioServerParameters(command=sys.executable, cwd=str(RAIZ),
                                       args=["-m", "omnicad.servidor_mcp", "--modo", "sin_ventana"],
                                       env={"PYTHONPATH": str(RAIZ), "LOCALAPPDATA": str(tmp_path)})

    async def caso():
        async with Client(parametros) as c:
            r = await c.call_tool("create_parameter", {"name": "a", "expression": "1 mm"})
            return json.loads(r.content[0].text)
    assert asyncio.run(asyncio.wait_for(caso(), 90))["ok"]
    (copia,) = (tmp_path / "OmniCAD" / "autoguardado").glob("sin_titulo_*.autoguardado.omnicad")
    assert _recuperado(copia) == ["a"]


def test_batch_del_cli_borra_su_copia_al_guardar_y_al_detenerse(carpeta, tmp_path, capsys):
    pieza = tmp_path / "pieza.omnicad"
    assert main(["new", str(pieza)]) == 0
    pasos = tmp_path / "p.jsonl"
    for falla, codigo in ((False, 0), (True, 1)):
        lineas = [{"tool": "create_parameter", "args": {"name": f"p{int(falla)}", "expression": "1 mm"}}]
        if falla:
            lineas.append({"tool": "set_parameter", "args": {"name": "no_existe", "expression": "2"}})
        pasos.write_text("\n".join(json.dumps(x) for x in lineas), encoding="utf-8")
        assert main(["batch", str(pasos), "--doc", str(pieza)]) == codigo
        assert not pieza.with_name("pieza.autoguardado.omnicad").exists()
