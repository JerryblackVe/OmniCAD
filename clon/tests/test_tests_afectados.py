"""Selección por impacto del paquete C: Git real, AST sin imports y ejecución por grupos."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "tests_afectados.py"
ESPEC = importlib.util.spec_from_file_location("tests_afectados", SCRIPT)
selector = importlib.util.module_from_spec(ESPEC)
ESPEC.loader.exec_module(selector)


def _escribir(raiz, ruta, texto):
    archivo = raiz / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(texto, encoding="utf-8")


def _git(raiz, *argumentos):
    return subprocess.run(["git", *argumentos], cwd=raiz, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def _guardar(raiz):
    _git(raiz, "add", ".")
    _git(raiz, "-c", "user.name=Prueba", "-c", "user.email=prueba@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-m", "Caso de prueba")
    return _git(raiz, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    archivos = {
        "clon/omnicad/__init__.py": "",
        "clon/omnicad/base.py": 'valor = 3\nraise RuntimeError("El selector no debe importar este módulo")\n',
        "clon/omnicad/servicio.py": "from .base import valor\n",
        "clon/omnicad/fachada/__init__.py": "from .puente import valor\n",
        "clon/omnicad/fachada/puente.py": "from .. import servicio\nvalor = servicio.valor\n",
        "clon/tests/conftest.py": "",
        "clon/tests/test_uno.py": "from omnicad import fachada\n",
        "clon/tests/test_dos.py": '"""Documentos de docs/seguimiento y manual.md."""\n',
        "scripts/prueba_ui/todo.py": 'PIEZAS = []\nPIEZAS.append("pieza")\n',
        "scripts/prueba_ui/pieza.py": "from apoyo import valor\n",
        "scripts/prueba_ui/apoyo.py": "from omnicad.servicio import valor\n",
        "docs/nota.md": "Una nota sin referencias.\n",
    }
    for ruta, texto in archivos.items():
        _escribir(tmp_path, ruta, texto)
    _git(tmp_path, "init", "--initial-branch=main")
    _guardar(tmp_path)
    return tmp_path


@pytest.mark.parametrize("ruta,hay_pieza", [
    ("base.py", True), ("servicio.py", True), ("fachada/puente.py", False),
    ("fachada/__init__.py", False), ("__init__.py", True),
])
def test_cierre_transitivo_relativos_reexportacion_y_auxiliar_de_pieza(repo, ruta, hay_pieza):
    archivo = repo / "clon/omnicad" / ruta
    archivo.write_text(archivo.read_text(encoding="utf-8") + "# Cambio\n", encoding="utf-8")
    tests, piezas, globales = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_uno.py"]
    assert list(piezas) == (["scripts/prueba_ui/pieza.py"] if hay_pieza else [])
    assert not globales


def test_import_absoluto_alias_estrella_y_ciclo(repo):
    _escribir(repo, "clon/tests/test_uno.py", "import omnicad.fachada.puente as p\n")
    _escribir(repo, "clon/omnicad/servicio.py", "from .base import *\nfrom . import fachada\n")
    _guardar(repo)
    _escribir(repo, "clon/omnicad/base.py", "valor = 4\n")
    tests, piezas, _ = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_uno.py"]
    assert list(piezas) == ["scripts/prueba_ui/pieza.py"]


@pytest.mark.parametrize("codigo", [
    "def usar():\n    from omnicad.base import valor\n",
    "class Clase:\n    from omnicad.base import valor\n",
    "if False:\n    import omnicad.base\n",
    "try:\n    pass\nexcept Exception:\n    import omnicad.base\n",
    "match 1:\n    case 1:\n        import omnicad.base\n",
])
def test_imports_dentro_de_bloques_sin_recorrer_expresiones(repo, codigo):
    _escribir(repo, "clon/tests/test_uno.py", codigo)
    _guardar(repo)
    _escribir(repo, "clon/omnicad/base.py", "valor = 4\n")
    assert list(selector.seleccionar(repo)[0]) == ["tests/test_uno.py"]


def test_markdown_sin_referencias_no_elige_nada(repo):
    _escribir(repo, "docs/nota.md", "Otra nota.\n")
    assert selector.seleccionar(repo) == ({}, {}, [])


@pytest.mark.parametrize("ruta", ["docs/manual.md", "datos/manual.md"])
def test_documento_nombrado_por_archivo(repo, ruta):
    _escribir(repo, ruta, "Documento nombrado por un test.\n")
    tests, piezas, globales = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_dos.py"]
    assert "nombra" in tests["tests/test_dos.py"]
    assert not piezas and not globales


def test_carpeta_de_docs_y_nombre_repetido_no_eligen(repo):
    # Un test que nombra «docs/seguimiento» en un comentario o un README.md cualquiera no se elige por otro documento.
    _escribir(repo, "clon/tests/test_dos.py", '"""Ver docs/seguimiento y README.md."""\n')
    _escribir(repo, "otro/README.md", "x\n")
    _escribir(repo, "docs/README.md", "x\n")
    _guardar(repo)
    _escribir(repo, "docs/seguimiento/bugs.md", "Cambio.\n")
    _escribir(repo, "docs/README.md", "Cambio.\n")
    assert selector.seleccionar(repo) == ({}, {}, [])


def test_documento_de_docs_elige_test_seguimiento(repo):
    _escribir(repo, "clon/tests/test_seguimiento.py", "# revisa los prompts de cada documento\n")
    _guardar(repo)
    _escribir(repo, "docs/nota.md", "## Prompt para el agente\n")
    tests, _, _ = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_seguimiento.py"]


@pytest.mark.parametrize("ruta", ["clon/tests/conftest.py", "clon/pyproject.toml",
                                  "clon/requirements.txt", "clon/requirements-dev.txt"])
def test_configuracion_compartida_elige_suite_entera(repo, ruta, capsys):
    _escribir(repo, ruta, "# Cambio\n")
    tests, _, globales = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_dos.py", "tests/test_uno.py"]
    assert globales == [ruta]
    assert selector.main(["--raiz", str(repo)]) == 0
    assert "SUITE COMPLETA por cambio en: " + ruta in capsys.readouterr().out


def test_test_tocado_y_nuevo_entran_siempre(repo):
    _escribir(repo, "clon/tests/test_dos.py", "# Test cambiado\n")
    _escribir(repo, "clon/tests/test_nuevo.py", "# Test sin seguimiento\n")
    tests, piezas, _ = selector.seleccionar(repo)
    assert tests == {"tests/test_dos.py": "test tocado", "tests/test_nuevo.py": "test tocado"}
    assert not piezas


def test_diff_incluye_indice_arbol_y_nuevos_con_espacios_y_tildes(repo):
    _escribir(repo, "clon/omnicad/base.py", "valor = 4\n")
    _git(repo, "add", "clon/omnicad/base.py")
    _escribir(repo, "docs/nota.md", "Sin preparar.\n")
    _escribir(repo, "docs/niño nuevo.md", "Sin seguimiento.\n")
    assert selector.archivos_tocados(repo) == ["clon/omnicad/base.py", "docs/niño nuevo.md", "docs/nota.md"]


def test_referencias_no_mezclan_el_arbol_de_trabajo(repo):
    antes = _git(repo, "rev-parse", "HEAD")
    _escribir(repo, "clon/omnicad/base.py", "valor = 4\n")
    despues = _guardar(repo)
    _escribir(repo, "clon/tests/test_dos.py", "# Cambio posterior\n")
    _escribir(repo, "clon/tests/test_nuevo.py", "# Sin seguimiento\n")
    assert selector.archivos_tocados(repo, antes, despues) == ["clon/omnicad/base.py"]
    tests, _, _ = selector.seleccionar(repo, antes, despues)
    assert list(tests) == ["tests/test_uno.py"]


def test_modulo_borrado_conserva_sus_importadores(repo):
    (repo / "clon/omnicad/base.py").unlink()
    tests, piezas, _ = selector.seleccionar(repo)
    assert list(tests) == ["tests/test_uno.py"]
    assert list(piezas) == ["scripts/prueba_ui/pieza.py"]


def test_script_y_datos_se_eligen_por_referencia_textual(repo):
    _escribir(repo, "clon/tests/test_dos.py", 'ARCHIVOS = ["utilidad.py", "entrada.json"]\n')
    _guardar(repo)
    _escribir(repo, "scripts/utilidad.py", "# No se importa\n")
    _escribir(repo, "datos/entrada.json", "{}")
    assert list(selector.seleccionar(repo)[0]) == ["tests/test_dos.py"]


def test_agrupacion_por_tiempos_y_defecto_sin_medicion():
    tests = [f"tests/test_{i}.py" for i in range(5)]
    tiempos = dict(zip(tests[:4], [390, 10, 500, 1], strict=True))
    grupos = selector.agrupar(reversed(tests), tiempos)
    assert grupos == [[tests[0]], [tests[1]], [tests[2]], tests[3:]]
    assert selector.agrupar([], {}) == []
    assert selector.TOPE_GRUPO == 400
    assert list(map(len, selector.agrupar([f"{i:03}.py" for i in range(60)], {}))) == [13, 13, 13, 13, 8]
    assert all(len(grupo) * selector.SEGUNDOS_SIN_MEDIR < selector.TOPE_GRUPO
               for grupo in selector.agrupar([f"{i:03}.py" for i in range(50)], {}))


def test_correr_respeta_turno_tiempos_y_fallo_sin_ejecutar_piezas(repo, monkeypatch, capsys):
    _escribir(repo, "clon/tests/conftest.py", "# Suite completa del repo mínimo\n")
    _escribir(repo, "scripts/prueba_ui/pieza.py", "# Pieza tocada\n")
    _escribir(repo, "evidencias/tiempos.json", json.dumps({"archivos": {
        "tests/test_dos.py": 400, "tests/test_uno.py": 400}}))
    llamadas = []
    ejecutar = subprocess.run

    def simular_grupo(comando, **opciones):
        if comando[0] == "git":
            return ejecutar(comando, **opciones)
        llamadas.append((comando, opciones))
        return SimpleNamespace(returncode=1 if len(llamadas) == 1 else 0)

    monkeypatch.setattr(selector.subprocess, "run", simular_grupo)
    assert selector.main(["--raiz", str(repo), "--correr"]) == 1
    assert len(llamadas) == 2
    for (comando, opciones), test in zip(llamadas, ("test_dos.py", "test_uno.py"), strict=True):
        assert opciones == {"cwd": repo / "clon"}
        assert comando == [sys.executable, "../scripts/turno.py", "--plazo", "900", "--", sys.executable,
                           "-m", "pytest", f"tests/{test}", "-q", "-W", "error", "-p", "no:cacheprovider"]
    salida = capsys.readouterr().out
    assert "../scripts/prueba_ui/todo.py pieza" in salida
    assert salida.count("Aviso: un archivo solo alcanza los 400 s;") == 2
    assert "Resultado: 2 grupos, 1 fallidos" in salida


@pytest.mark.parametrize("codigo_final", [0, 1, 124])
def test_correr_repite_en_mitades_y_archivo_solo_cortado_falla(repo, monkeypatch, capsys, codigo_final):
    tests = [f"tests/test_{i}.py" for i in range(7)]
    monkeypatch.setattr(selector, "seleccionar", lambda *args: (dict.fromkeys(tests, "test tocado"), {}, []))
    llamadas = []
    ejecutar = subprocess.run
    limite = 2

    def simular_grupo(comando, **opciones):
        if comando[0] == "git":
            return ejecutar(comando, **opciones)
        grupo = comando[8:-5]
        assert opciones == {"cwd": repo / "clon"}
        assert comando == [sys.executable, "../scripts/turno.py", "--plazo", "900", "--", sys.executable,
                           "-m", "pytest", *grupo, "-q", "-W", "error", "-p", "no:cacheprovider"]
        llamadas.append(grupo)
        codigo = 124 if len(grupo) > limite else codigo_final if tests[0] in grupo else 0
        return SimpleNamespace(returncode=codigo)

    monkeypatch.setattr(selector.subprocess, "run", simular_grupo)
    assert selector.main(["--raiz", str(repo), "--correr"]) == int(codigo_final != 0)
    assert llamadas == [tests, tests[:3], tests[:1], tests[1:3], tests[3:], tests[3:5], tests[5:]]
    salida = capsys.readouterr().out
    aviso = "Grupo 1: cortado por el plazo de 900 s (124); lo repito en dos mitades"
    assert salida.count(aviso) == 3
    assert f"Grupo 1: salida {codigo_final}" in salida
    assert f"Resultado: 1 grupos, {int(codigo_final != 0)} fallidos" in salida

    tests = tests[:1]
    limite = 0
    llamadas.clear()
    assert selector.main(["--raiz", str(repo), "--correr"]) == 1
    assert llamadas == [tests]
    salida = capsys.readouterr().out
    assert aviso not in salida
    assert "Grupo 1: salida 124" in salida
    assert "Resultado: 1 grupos, 1 fallidos" in salida


def test_correr_worktree_usa_tiempos_del_checkout_principal(repo, monkeypatch, capsys):
    arbol = repo / "arbol"
    _git(repo, "worktree", "add", "--detach", str(arbol), "HEAD")
    _escribir(arbol, "clon/tests/conftest.py", "# Configuración común\n")
    _escribir(repo, "evidencias/tiempos.json", json.dumps({"archivos": {
        "tests/test_dos.py": 350, "tests/test_uno.py": 350}}))
    assert not (arbol / "evidencias/tiempos.json").exists()
    llamadas = []
    ejecutar = subprocess.run

    def simular_grupo(comando, **opciones):
        if comando[0] == "git":
            return ejecutar(comando, **opciones)
        assert opciones == {"cwd": arbol / "clon"}
        llamadas.append(comando[8:-5])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(selector.subprocess, "run", simular_grupo)
    assert selector.main(["--raiz", str(arbol), "--correr"]) == 0
    assert llamadas == [["tests/test_dos.py"], ["tests/test_uno.py"]]
    salida = capsys.readouterr().out
    assert salida.count("1 archivos, 350.0 s estimados") == 2
    assert "Resultado: 2 grupos, 0 fallidos" in salida

    (repo / "evidencias/tiempos.json").unlink()
    llamadas.clear()
    assert selector.main(["--raiz", str(arbol), "--correr"]) == 0
    assert llamadas == [["tests/test_dos.py", "tests/test_uno.py"]]
    assert "2 archivos, 60.0 s estimados" in capsys.readouterr().out


def test_cli_sin_correr_no_lanza_pytest_y_lista_ordenada(repo):
    _escribir(repo, "clon/tests/conftest.py", "# Configuración común\n")
    resultado = subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(repo)], capture_output=True,
                               text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.index("  tests/test_dos.py") < resultado.stdout.index("  tests/test_uno.py")
    assert "Grupo " not in resultado.stdout


def test_error_de_git_se_informa_sin_exito(repo, capsys):
    assert selector.main(["--raiz", str(repo), "--desde", "referencia_inexistente"]) == 2
    assert "No se pudo seleccionar" in capsys.readouterr().err
