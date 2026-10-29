"""Los datos reanudables van aparte y las tablas se reproducen sin medir otra vez."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest


@pytest.fixture
def banco(tmp_path, monkeypatch):
    raiz = Path(__file__).resolve().parents[2]
    espacio = runpy.run_path(str(raiz / "scripts/medir_previa_comandos.py"))["main"].__globals__
    monkeypatch.setitem(espacio, "RAIZ", tmp_path)
    (tmp_path / "docs/auditorias").mkdir(parents=True)
    corrida = {
        "valida": True, "previa_ok": True, "mensaje": "", "fps": 60, "previas_s": 2,
        "retraso_ms": {"n": 1, "p50": 2, "p95": 3}, "cuadros_33": 0, "cuadros_100": 0,
        "hijo_primera": 0, "hijo_arrastre": 0,
        "primera": {k: {"p50": 4} for k in ("previa", "kernel", "modelo")},
        "etapas": {k: {"n": 2} for k in ("previa", "teselado")},
        "muestras_ms": {k: [1, 3] for k in ("previa", "kernel", "modelo", "teselado_por_modelo", "dibujo")},
    }
    datos = {
        "fecha": "2026-10-28", "commit": "base", "version": 2, "catalogo": {},
        "modelos": {"chico": {"pasos": 1, "cuerpos": 1, "caras": 6}},
        "casos": {"empalme": {"chico": [deepcopy(corrida), deepcopy(corrida)]}},
    }
    ruta = tmp_path / "docs/auditorias/previa-comandos-2026-10-28.md"
    espacio["_guardar"](ruta, datos)
    return espacio, datos, ruta, tmp_path / "evidencias/previa_comandos_2026-10-28.json"


def ejecutar(banco, monkeypatch, *opciones):
    monkeypatch.setattr("sys.argv", ["medir_previa_comandos.py", "--fecha", "2026-10-28", *opciones])
    banco[0]["main"]()


def test_guardar_y_resumir_reproducen_tablas_sin_json_embebido(banco, monkeypatch, capsys):
    _, datos, ruta, ruta_datos = banco
    original, crudo = ruta.read_bytes(), ruta_datos.read_bytes()
    assert json.loads(crudo) == datos
    assert b"DATOS_PREVIA" not in original and len(original) < 100_000
    assert "evidencias/previa_comandos_2026-10-28.json" in original.decode("utf-8")
    ejecutar(banco, monkeypatch, "--resumir")
    assert capsys.readouterr().out.rstrip() == original.decode("utf-8").rstrip()
    assert "| empalme | chico (1/1/6) | 2 | 2.0/3.0/3.0 |" in original.decode("utf-8")
    assert ruta.read_bytes() == original and ruta_datos.read_bytes() == crudo
    ejecutar(banco, monkeypatch, "--comprobar")
    assert "JSON separado y tablas del informe OK" in capsys.readouterr().out


def test_comprobar_rechaza_una_tabla_que_no_sale_del_json(banco, monkeypatch):
    ruta = banco[2]
    original = ruta.read_bytes()
    cambiado = original.replace(b"2.0/3.0/3.0", b"9.0/9.9/9.0")
    assert cambiado != original
    ruta.write_bytes(cambiado)
    with pytest.raises(AssertionError, match="tabla del informe no coincide"):
        ejecutar(banco, monkeypatch, "--comprobar")


def test_informe_asincrono_no_inventa_un_kernel_de_cero(banco):
    espacio, datos, *_ = banco
    for corrida in datos["casos"]["empalme"]["chico"]:
        corrida["primera"].pop("kernel")
        corrida["etapas"].pop("teselado")
        corrida["muestras_ms"]["kernel"] = []
    texto = espacio["_informe"](datos)
    assert "kernel del hijo no está instrumentado (—)" in texto
    assert "| empalme | chico | 4.0–4.0 | — | 4.0–4.0 |" in texto


@pytest.mark.parametrize("opciones", [("--resumir",), ("--comprobar",), ()])
def test_json_faltante_avisa_sin_pisar_el_informe(banco, monkeypatch, capsys, opciones):
    ruta, ruta_datos = banco[2:]
    original = ruta.read_bytes()
    ruta_datos.unlink()
    with pytest.raises(SystemExit) as error:
        ejecutar(banco, monkeypatch, *opciones)
    assert error.value.code == 2
    assert "Faltan los datos:" in capsys.readouterr().err
    assert ruta.read_bytes() == original and not ruta_datos.exists()


def test_modo_normal_reanuda_el_json_y_guarda_la_corrida_nueva(banco, monkeypatch):
    espacio, datos, ruta, ruta_datos = banco
    entradas = []
    monkeypatch.setattr(espacio["subprocess"], "check_output", lambda *a, **k: "base\n")
    monkeypatch.setitem(espacio, "_modelo", lambda nombre: ({}, datos["modelos"][nombre]))
    monkeypatch.setitem(espacio, "QApplication", SimpleNamespace(instance=lambda: object()))
    monkeypatch.setattr(espacio["_Relojes"], "instalar", lambda *a: None)

    def medir(*args):
        entradas.append(args)
        return deepcopy(datos["casos"]["empalme"]["chico"][0])

    monkeypatch.setitem(espacio, "_corrida", medir)
    ruta.write_bytes(b"El modo normal no lee los datos desde este Markdown.\n")
    ejecutar(banco, monkeypatch, "--modelo", "chico", "--comandos", "empalme")
    assert len(entradas) == 1
    guardados = json.loads(ruta_datos.read_bytes())
    assert guardados["casos"]["empalme"]["chico"][:2] == datos["casos"]["empalme"]["chico"]
    assert len(guardados["casos"]["empalme"]["chico"]) == 3
    assert ruta.read_text(encoding="utf-8") == espacio["_informe"](guardados)
