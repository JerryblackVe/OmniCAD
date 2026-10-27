"""Lectura entre procesos, herramientas MCP/CLI, marcador y informe de sesión."""
import json

import pytest

from omnicad import api, registro_uso as ru
from omnicad.cli import main as cli
from omnicad.registro_uso import almacen


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    ru.ultimo = None
    yield
    ru.configurar(False)
    ru.ultimo = None


def sesion_sintetica(tmp_path):
    r = ru.Registro({"proyecto": "C:/privado/pieza.omnicad", "version": "0.1.4", "so": "Windows"},
                    destino=tmp_path / "registro", tope_archivo=420)
    r.emitir("comando_abierto", {"comando": "cilindro"})
    r.emitir("comando_aceptado", {"comando": "cilindro", "duracion_s": 2.5, "cambios": 1})
    r.emitir("op_ejecutada", {"paso": "op1", "tipo_op": "primitiva", "duracion_ms": 2600,
                              "exito": True, "antes": {"cuerpos": 0, "volumen": 0},
                              "despues": {"cuerpos": 1, "volumen": 6000}})
    r.emitir("error", {"origen": "api", "comando": "empalme", "excepcion": "ValueError",
                       "mensaje": "SECRETO C:/privado"})
    r.emitir("marca", {"label": "prueba_ia", "nota": "SECRETO"})
    r.cerrar()
    return r.id


def test_almacen_lee_partes_y_tail(tmp_path):
    sesion = sesion_sintetica(tmp_path)
    assert almacen.ultima_sesion() == sesion
    assert almacen.activa(sesion)
    assert len(almacen.rutas(sesion)) > 1                     # el tope chico obligó a rotar
    todos = almacen.eventos(sesion)
    assert todos[0]["tipo"] == "sesion_inicio" and todos[-1]["seq"] == 6
    assert [e["tipo"] for e in almacen.eventos(sesion, desde=3, tipos=["error"])] == ["error"]
    ultimo = almacen.rutas(sesion)[-1]
    lector = almacen.Lector(sesion).al_final()
    nuevo = {"t": 10, "ts": "2026-10-26T12:00:10.000Z", "tipo": "marca", "datos": {"label": "nueva"}, "seq": 7}
    with open(ultimo, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(nuevo) + "\n")
    assert [e["seq"] for e in lector.nuevos()] == [7]
    with open(ultimo, "a", encoding="utf-8", newline="\n") as f:
        f.write('{"seq": 8, "tipo": "ma')
    assert lector.nuevos() == []
    with open(ultimo, "a", encoding="utf-8", newline="\n") as f:
        f.write('rca", "t": 11, "datos": {}}\n')
    assert [e["seq"] for e in lector.nuevos()] == [8]


def test_herramientas_lectura_resumen_marca_e_informe(tmp_path):
    sesion = sesion_sintetica(tmp_path)
    s = api.Sesion()
    r = api.llamar(s, "get_usage_log", {"session": sesion, "since": 3, "kinds": ["error", "marca"], "limit": 1})
    assert r["ok"] and r["result"]["count"] == 1 and r["result"]["last_seq"] == 6
    r = api.llamar(s, "get_usage_summary", {"session": sesion})
    assert r["ok"] and r["result"]["comandos"]["cilindro"]["aceptados"] == 1
    assert r["result"]["hallazgos_por_severidad"]["alta"] >= 1
    r = api.llamar(s, "build_usage_report", {"session": sesion})
    assert r["ok"], r
    texto = open(r["result"]["path"], encoding="utf-8").read()
    assert "Informe de sesión" in texto and "Línea de tiempo" in texto and "| B-? |" in texto
    assert "SECRETO" not in texto and "C:/privado" not in texto
    assert "prueba_ia" in texto


def test_marca_local_y_hooks_en_vivo():
    s = api.Sesion()
    ru.configurar(True)
    r = api.llamar(s, "mark_usage_event", {"label": "extrusión lenta"})
    assert r["ok"] and r["result"]["label"] == "extrusi_n_lenta"
    ru.activo.cola.join()
    es = [json.loads(l) for p in ru.carpeta().glob("sesion_*.jsonl") for l in p.read_text(encoding="utf-8").splitlines()]
    assert any(e["tipo"] == "marca" and e["datos"]["label"] == "extrusi_n_lenta" for e in es)
    ru.configurar(False)
    assert not api.llamar(s, "mark_usage_event", {"label": "x"})["ok"]
    s.registrar_marca = lambda label: 77
    assert api.llamar(s, "mark_usage_event", {"label": "desde_ia"})["result"]["seq"] == 77
    s.configurar_registro = lambda enabled: {"enabled": enabled, "session": "viva"}
    assert api.llamar(s, "set_usage_logging", {"enabled": True})["result"]["session"] == "viva"


def test_cli_resumen_y_errores(tmp_path, capsys):
    sesion = sesion_sintetica(tmp_path)
    assert cli(["registro", "--json"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["ok"] and datos["session"] == sesion and datos["errores"] == 1
    assert cli(["registro", "--sesion", "../../otro"]) == 2
    assert cli(["registro", "--since", "1"]) == 2
    salida = capsys.readouterr()
    assert "sesión" in salida.err.lower() or "sesión" in salida.out.lower()


def test_cli_seguir_json_reproduce_eventos(tmp_path, monkeypatch, capsys):
    from omnicad.cli import cmd_registro
    sesion = sesion_sintetica(tmp_path)
    monkeypatch.setattr(cmd_registro.time, "sleep", lambda _s: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert cli(["registro", "--seguir", "--json", "--sesion", sesion, "--since", "0"]) == 130
    lineas = [json.loads(l) for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert [e["tipo"] for e in lineas][0] == "sesion_inicio"
    assert lineas[-1]["seq"] == 6
