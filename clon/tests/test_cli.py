# -*- coding: utf-8 -*-
"""CLI `omnicad`: salida, códigos de salida (0 ok, 1 herramienta falló, 2 uso), guardado y atajos."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from omnicad.cli import main
from omnicad.cli import util

RAIZ = Path(__file__).resolve().parent.parent   # D:/PROGRAMA/clon


def correr(capsys, *argv):
    """main(argv) en el mismo proceso → (código, stdout, stderr)."""
    capsys.readouterr()
    codigo = main([str(a) for a in argv])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def como_json(texto):
    return json.loads(texto.strip())


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """Proyecto de partida (parámetro `ancho` + una caja), creado con la propia CLI."""
    carpeta = tmp_path_factory.mktemp("cli_base")
    ruta = carpeta / "base.omnicad"
    assert main(["new", str(ruta)]) == 0
    assert main(["call", "create_parameter", "--doc", str(ruta), "name=ancho", "expression=60 mm"]) == 0
    assert main(["call", "create_box", "--doc", str(ruta), "--args",
                 '{"length": "ancho", "width": 30, "height": 10}']) == 0
    return ruta


@pytest.fixture
def pieza(base, tmp_path):
    destino = tmp_path / "pieza.omnicad"
    shutil.copy(base, destino)
    return destino


def subproceso(*argv, cwd=None, env=None):
    entorno = dict(os.environ, **(env or {}))
    entorno["PYTHONPATH"] = str(RAIZ) + os.pathsep + entorno.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "omnicad.cli", *map(str, argv)], capture_output=True,
                          cwd=cwd, env=entorno, timeout=120)


# ---------------------------------------------------------------- versión y arranque
def test_version_por_subproceso():
    r = subproceso("--version")
    assert r.returncode == 0
    assert r.stdout.decode("utf-8").strip() == "omnicad 0.1.0"


def test_version_y_ayuda_no_cargan_la_api():
    """--version y --help tienen que arrancar al instante: `omnicad.api` (OCP, scipy: ~2 s) no se importa."""
    codigo = ("import sys; from omnicad.cli import main; "
              "print(main(['--version']), main(['--help']), 'omnicad.api' in sys.modules)")
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, cwd=RAIZ, timeout=60)
    assert r.stdout.decode("utf-8").split()[-3:] == ["0", "0", "False"], r.stderr


def test_ayuda_en_espanol(capsys):
    codigo, out, _ = correr(capsys, "--help")
    assert codigo == 0
    assert "uso:" in out and "comandos" in out and "códigos de salida" in out
    for comando in ("tools", "describe", "call", "new", "info", "export", "render", "run", "batch"):
        assert comando in out


# ---------------------------------------------------------------- catálogo
def test_tools_json_parsea(capsys):
    codigo, out, _ = correr(capsys, "tools", "--json")
    assert codigo == 0
    lista = como_json(out)
    nombres = {h["nombre"] for h in lista}
    assert {"create_parameter", "get_scene_info", "execute_code"} <= nombres
    assert all(set(h) == {"nombre", "grupo", "modifica", "descripcion"} for h in lista)
    api = util.api()
    assert nombres == {h["nombre"] for h in api.catalogo()}      # dinámico: nada de listas fijas


def test_tools_filtra_por_grupo_y_texto_corto(capsys):
    codigo, out, _ = correr(capsys, "tools", "--group", "parametros")
    assert codigo == 0
    lineas = [x for x in out.splitlines() if x.strip() and not x.startswith("\n")]
    assert any(x.startswith("create_parameter") and " M " in x for x in lineas)
    assert not any(x.startswith("create_box") for x in lineas)
    _, solo, _ = correr(capsys, "tools", "--group", "parametros", "--json")
    assert {h["grupo"] for h in como_json(solo)} == {"parametros"}


def test_tools_grupo_inexistente_es_error_de_uso(capsys):
    codigo, _, err = correr(capsys, "tools", "--group", "no_existe")
    assert codigo == 2 and "no_existe" in err


def test_describe(capsys):
    codigo, out, _ = correr(capsys, "describe", "create_parameter")
    assert codigo == 0
    assert "name" in out and "expression" in out and "obligatorio" in out
    codigo, out, _ = correr(capsys, "describe", "create_parameter", "--json")
    h = como_json(out)
    assert h["nombre"] == "create_parameter" and "name" in h["esquema"]["properties"]
    codigo, _, err = correr(capsys, "describe", "create_paramete")
    assert codigo == 2 and "create_parameter" in err          # sugiere el nombre parecido


# ---------------------------------------------------------------- new + call + info (cadena real)
def test_cadena_por_subproceso(tmp_path):
    ruta = tmp_path / "x.omnicad"
    assert subproceso("new", ruta).returncode == 0
    r = subproceso("call", "create_parameter", "--doc", ruta, "name=largo", "expression=25 mm")
    assert r.returncode == 0, r.stderr
    r = subproceso("info", ruta, "--json")
    assert r.returncode == 0
    escena = como_json(r.stdout.decode("utf-8"))
    assert escena["ok"] and escena["result"]["name"] == "x"   # el nombre del archivo
    assert [p["name"] for p in escena["result"]["parameters"]] == ["largo"]


def test_new_no_pisa_sin_overwrite(tmp_path, capsys):
    ruta = tmp_path / "a.omnicad"
    assert correr(capsys, "new", ruta)[0] == 0
    codigo, out, _ = correr(capsys, "new", ruta, "--json")
    assert codigo == 1 and como_json(out)["error_kind"] == "FILE_EXISTS"
    assert correr(capsys, "new", ruta, "--overwrite")[0] == 0


def test_call_guarda_y_no_save_no_guarda(pieza, capsys):
    antes = pieza.read_bytes()
    codigo, out, _ = correr(capsys, "call", "create_parameter", "--doc", pieza, "--no-save",
                            "name=alto", "expression=5")
    assert codigo == 0 and "guardado" not in out
    assert pieza.read_bytes() == antes
    codigo, out, _ = correr(capsys, "call", "create_parameter", "--doc", pieza, "name=alto", "expression=5")
    assert codigo == 0 and "guardado:" in out
    _, info, _ = correr(capsys, "info", pieza, "--json")
    nombres = [p["name"] for p in como_json(info)["result"]["parameters"]]
    assert nombres == ["ancho", "alto"]


def test_call_herramienta_que_solo_lee_no_toca_el_archivo(pieza, capsys):
    antes = pieza.read_bytes()
    codigo, out, _ = correr(capsys, "call", "get_parameters", "--doc", pieza, "--json")
    assert codigo == 0 and como_json(out)["ok"]
    assert pieza.read_bytes() == antes


def test_clave_valor_mezclado_con_opciones_y_tipos(pieza, capsys):
    codigo, out, _ = correr(capsys, "call", "create_box", "length=20", "--doc", pieza, "width=10.5",
                            "--json", "height=2", "operation=new_body")
    assert codigo == 0, out
    assert como_json(out)["result"]["bodies_created"][0]["volume"] == pytest.approx(20 * 10.5 * 2)


def test_valor_se_interpreta_como_json_o_texto():
    prop_texto = {"type": "string"}
    assert util._valor("123", prop_texto) == "123"             # el esquema pide texto: se respeta
    assert util._valor("123", {"type": ["number", "string"]}) == 123
    assert util._valor("[1, 2]", {"type": "array"}) == [1, 2]
    assert util._valor("true", {"type": "boolean"}) is True
    assert util._valor("60 mm", {"type": ["number", "string"]}) == "60 mm"


def test_args_y_args_file(pieza, tmp_path, capsys):
    archivo = tmp_path / "args.json"
    archivo.write_text('{"name": "k", "expression": "7 mm", "comment": "útil"}', encoding="utf-8-sig")
    assert correr(capsys, "call", "create_parameter", "--doc", pieza, "--args-file", archivo)[0] == 0
    codigo, out, _ = correr(capsys, "call", "get_parameters", "--doc", pieza, "--json")
    k = next(p for p in como_json(out)["result"]["parameters"] if p["name"] == "k")
    assert k["comment"] == "útil"


# ---------------------------------------------------------------- errores
def test_error_de_herramienta_exit_1_con_error_kind(pieza, capsys):
    antes = pieza.read_bytes()
    codigo, out, _ = correr(capsys, "call", "set_parameter", "--doc", pieza, "--json",
                            "name=nope", "expression=1")
    r = como_json(out)
    assert codigo == 1 and r["ok"] is False and r["error_kind"] == "PARAMETER_NOT_FOUND"
    assert r["mensaje"] and isinstance(r["pistas"], list)
    assert pieza.read_bytes() == antes                          # si falla, no se guarda nada
    codigo, out, err = correr(capsys, "call", "set_parameter", "--doc", pieza, "name=nope", "expression=1")
    assert codigo == 1 and out == "" and "PARAMETER_NOT_FOUND" in err and "pista:" in err


def test_argumentos_invalidos_de_la_herramienta_exit_1(pieza, capsys):
    codigo, out, _ = correr(capsys, "call", "create_box", "--doc", pieza, "--json", "length=10")
    assert codigo == 1 and como_json(out)["error_kind"] == "INVALID_ARGUMENTS"


@pytest.mark.parametrize("argv", [
    [],                                                     # sin subcomando
    ["call"],                                               # falta la herramienta
    ["call", "no_existe_la_herramienta"],
    ["tools", "--opcion-rara"],
    ["call", "get_scene_info", "--args", "{no es json"],
    ["call", "get_scene_info", "--args", "[1, 2]"],
    ["call", "get_scene_info", "--args", "{}", "--args-file", "x.json"],     # excluyentes
    ["call", "get_scene_info", "--args-file", "no_existe.json"],
    ["call", "get_scene_info", "--doc", "no_existe.omnicad"],
    ["info", "no_existe.omnicad"],
    ["render", "a.omnicad", "b.png", "--size", "grande"],
    ["render", "a.omnicad", "b.jpg"],
    ["batch", "no_existe.jsonl"],
    ["run", "no_existe.py"],
    ["run", "no_existe.py", "--save"],
])
def test_uso_incorrecto_exit_2(argv, capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, out, err = correr(capsys, *argv)
    assert codigo == 2
    assert out == "" or "uso:" in out                      # nada de JSON de éxito ni resultados
    assert err or out


def test_error_de_uso_con_json_da_cli_usage(capsys, tmp_path):
    codigo, out, _ = correr(capsys, "info", tmp_path / "no_existe.omnicad", "--json")
    r = como_json(out)
    assert codigo == 2 and r["ok"] is False and r["error_kind"] == "CLI_USAGE"


def test_doc_corrupto_es_error_de_herramienta(tmp_path, capsys):
    mal = tmp_path / "mal.omnicad"
    mal.write_bytes(b"esto no es un zip")
    codigo, out, _ = correr(capsys, "info", mal, "--json")
    assert codigo == 1 and como_json(out)["error_kind"] == "INVALID_PROJECT"


# ---------------------------------------------------------------- render y export
def test_render_escribe_un_png_valido(pieza, tmp_path, capsys):
    from PIL import Image
    salida = tmp_path / "sub" / "vista.png"
    codigo, out, _ = correr(capsys, "render", pieza, salida, "--view", "front", "--size", "320x240", "--json")
    assert codigo == 0, out
    assert salida.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(salida) as im:
        assert im.size == (320, 240)
    r = como_json(out)
    assert r["result"]["image"]["path"] == str(salida.resolve())
    assert "iVBOR" not in out and len(out) < 2000            # nunca base64 por consola


def test_call_imagen_a_temporal_si_no_hay_image_out(pieza, capsys):
    codigo, out, _ = correr(capsys, "call", "get_viewport_image", "--doc", pieza, "--json",
                            "width=64", "height=48")
    assert codigo == 0
    ruta = Path(como_json(out)["result"]["image"]["path"])
    try:
        assert ruta.is_file() and ruta.read_bytes()[:4] == b"\x89PNG"
    finally:
        ruta.unlink(missing_ok=True)


def test_render_vista_invalida_es_uso(pieza, tmp_path, capsys):
    codigo, _, err = correr(capsys, "render", pieza, tmp_path / "x.png", "--view", "diagonal")
    assert codigo == 2 and "iso" in err


def test_export_stl(pieza, tmp_path, capsys):
    salida = tmp_path / "pieza.stl"
    codigo, out, _ = correr(capsys, "export", pieza, salida, "--json")
    assert codigo == 0, out
    assert salida.stat().st_size > 100
    assert como_json(out)["result"]["format"] == "stl"
    codigo, out, _ = correr(capsys, "export", pieza, salida, "--json")        # ya existe
    assert codigo == 1 and como_json(out)["error_kind"] == "FILE_EXISTS"
    assert correr(capsys, "export", pieza, salida, "--overwrite")[0] == 0


def test_export_sin_cuerpos_exit_1(tmp_path, capsys):
    vacio = tmp_path / "v.omnicad"
    correr(capsys, "new", vacio)
    codigo, out, _ = correr(capsys, "export", vacio, tmp_path / "v.stl", "--json")
    assert codigo == 1 and como_json(out)["error_kind"] == "NOTHING_TO_EXPORT"


# ---------------------------------------------------------------- batch
def escribir_pasos(ruta, pasos):
    ruta.write_text("\n".join(json.dumps(p) for p in pasos) + "\n", encoding="utf-8")
    return ruta


def test_batch_tres_pasos_ok_guarda_una_vez(pieza, tmp_path, capsys):
    pasos = escribir_pasos(tmp_path / "p.jsonl", [
        {"tool": "create_parameter", "args": {"name": "a", "expression": "1 mm"}},
        {"tool": "create_parameter", "args": {"name": "b", "expression": "a + 1 mm"}},
        {"tool": "get_parameters"},
    ])
    codigo, out, _ = correr(capsys, "batch", pasos, "--doc", pieza, "--json")
    resultados = como_json(out)
    assert codigo == 0 and len(resultados) == 3 and all(r["ok"] for r in resultados)
    assert [p["name"] for p in resultados[2]["result"]["parameters"]] == ["ancho", "a", "b"]
    _, info, _ = correr(capsys, "info", pieza, "--json")
    assert [p["name"] for p in como_json(info)["result"]["parameters"]] == ["ancho", "a", "b"]


def test_batch_con_un_paso_que_falla_para_y_no_guarda(pieza, tmp_path, capsys):
    antes = pieza.read_bytes()
    pasos = escribir_pasos(tmp_path / "p.jsonl", [
        {"tool": "create_parameter", "args": {"name": "a", "expression": "1 mm"}},
        {"tool": "set_parameter", "args": {"name": "no_existe", "expression": "2"}},
        {"tool": "create_parameter", "args": {"name": "c", "expression": "3 mm"}},
    ])
    codigo, out, _ = correr(capsys, "batch", pasos, "--doc", pieza, "--json")
    resultados = como_json(out)
    assert codigo == 1
    assert len(resultados) == 2 and resultados[0]["ok"] and resultados[1]["error_kind"] == "PARAMETER_NOT_FOUND"
    assert pieza.read_bytes() == antes                            # NO guarda nada
    codigo, _, err = correr(capsys, "batch", pasos, "--doc", pieza)
    assert codigo == 1 and "paso 2" in err and "NO se guardó nada" in err


def test_batch_continue_on_error_sigue_y_guarda(pieza, tmp_path, capsys):
    pasos = escribir_pasos(tmp_path / "p.jsonl", [
        {"tool": "create_parameter", "args": {"name": "a", "expression": "1 mm"}},
        {"tool": "set_parameter", "args": {"name": "no_existe", "expression": "2"}},
        {"tool": "create_parameter", "args": {"name": "c", "expression": "3 mm"}},
    ])
    codigo, out, _ = correr(capsys, "batch", pasos, "--doc", pieza, "--continue-on-error", "--json")
    resultados = como_json(out)
    assert codigo == 1 and [r["ok"] for r in resultados] == [True, False, True]
    _, info, _ = correr(capsys, "info", pieza, "--json")
    assert [p["name"] for p in como_json(info)["result"]["parameters"]] == ["ancho", "a", "c"]


def test_batch_json_invalido_o_herramienta_inexistente_no_ejecuta_nada(pieza, tmp_path, capsys):
    antes = pieza.read_bytes()
    mal = tmp_path / "mal.jsonl"
    mal.write_text('{"tool": "create_parameter", "args": {"name": "a", "expression": "1"}}\nesto no es json\n',
                   encoding="utf-8")
    codigo, _, err = correr(capsys, "batch", mal, "--doc", pieza)
    assert codigo == 2 and "línea 2" in err
    raro = escribir_pasos(tmp_path / "raro.jsonl", [
        {"tool": "create_parameter", "args": {"name": "a", "expression": "1"}}, {"tool": "no_existe"}])
    assert correr(capsys, "batch", raro, "--doc", pieza)[0] == 2
    assert pieza.read_bytes() == antes


def test_batch_arma_una_pieza_completa_en_un_proceso(tmp_path, capsys):
    destino = tmp_path / "nueva.omnicad"
    pasos = escribir_pasos(tmp_path / "p.jsonl", [
        {"tool": "new_document", "args": {"name": "Lote"}},
        {"tool": "create_parameter", "args": {"name": "ancho", "expression": "40 mm"}},
        {"tool": "create_box", "args": {"length": "ancho", "width": 20, "height": 5}},
        {"tool": "save_document", "args": {"path": str(destino)}},
    ])
    codigo, out, _ = correr(capsys, "batch", pasos, "--json")
    assert codigo == 0 and len(como_json(out)) == 4
    _, info, _ = correr(capsys, "info", destino, "--json")
    assert como_json(info)["result"]["bodies"][0]["volume"] == pytest.approx(4000)


# ---------------------------------------------------------------- run
def test_run_script_con_llamar(pieza, tmp_path, capsys):
    script = tmp_path / "s.py"
    script.write_text(
        "r = llamar('create_parameter', {'name': 'grueso', 'expression': '3 mm', 'comment': 'ñandú útil'})\n"
        "assert r['ok'], r\n"
        "print('hola', len(doc.parametros))\n"
        "result = {'n': len(doc.parametros)}\n", encoding="utf-8")
    antes = pieza.read_bytes()
    codigo, out, _ = correr(capsys, "run", script, "--doc", pieza)
    assert codigo == 0 and "hola 2" in out and "result" in out
    assert pieza.read_bytes() == antes                            # sin --save no se toca
    codigo, out, _ = correr(capsys, "run", script, "--doc", pieza, "--save", "--json")
    assert codigo == 0 and como_json(out)["result"]["result"] == {"n": 2}
    _, info, _ = correr(capsys, "info", pieza, "--json")
    params = {p["name"]: p for p in como_json(info)["result"]["parameters"]}
    assert params["grueso"]["comment"] == "ñandú útil"


def test_run_script_con_error_exit_1_y_no_guarda(pieza, tmp_path, capsys):
    script = tmp_path / "malo.py"
    script.write_text("llamar('create_parameter', {'name': 'x', 'expression': '1'})\nraise ValueError('falló a propósito')\n",
                      encoding="utf-8")
    antes = pieza.read_bytes()
    codigo, out, _ = correr(capsys, "run", script, "--doc", pieza, "--save", "--json")
    r = como_json(out)
    assert codigo == 1 and r["error_kind"] == "CODE_ERROR" and "falló a propósito" in r["mensaje"]
    assert pieza.read_bytes() == antes


def test_run_script_corre_sin_tiempo_maximo(pieza, tmp_path, capsys, monkeypatch):
    from omnicad.api import herramientas_avanzado as av
    plazos = []
    original = av._plazo
    monkeypatch.setattr(av, "_plazo", lambda co, seg, ses: plazos.append(seg) or original(co, seg, ses))
    script = tmp_path / "corto.py"
    script.write_text("result = 1\n", encoding="utf-8")
    codigo, _, _ = correr(capsys, "run", script, "--doc", pieza)
    assert codigo == 0 and plazos == [None]


# ---------------------------------------------------------------- UTF-8
def test_textos_con_tildes_no_rompen_la_salida_con_consola_no_utf8(pieza):
    """Aunque Python crea que la consola es cp1252/ascii, la CLI escribe UTF-8 sin caer."""
    for codificacion in ("cp1252", "ascii"):
        entorno = {"PYTHONIOENCODING": codificacion}
        r = subproceso("call", "create_parameter", "--doc", pieza, "name=p" + codificacion[:2],
                       "expression=1 mm", "comment=Ancho útil ñandú «ok»", env=entorno)
        assert r.returncode == 0, r.stderr
        r = subproceso("call", "get_parameters", "--doc", pieza, env=entorno)
        assert r.returncode == 0, r.stderr
        assert "Ancho útil ñandú «ok»" in r.stdout.decode("utf-8")
        r = subproceso("describe", "create_parameter", env=entorno)
        assert r.returncode == 0 and "parámetro" in r.stdout.decode("utf-8")
        r = subproceso("call", "herramienta_que_no_existe", env=entorno)
        assert r.returncode == 2 and "No existe la herramienta" in r.stderr.decode("utf-8")
