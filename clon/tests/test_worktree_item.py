"""Contrato de worktree_item.sh con Git real, siempre dentro de tmp_path."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "worktree_item.sh"


def _ejecutar(raiz, *comando):
    # Los tests afectados pueden heredar otro índice; tampoco usamos configuración global.
    entorno = {clave: valor for clave, valor in os.environ.items()
               if not clave.upper().startswith("GIT_")}
    entorno.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(comando, cwd=raiz, env=entorno, capture_output=True,
                          text=True, encoding="utf-8", timeout=30)


def _git(raiz, *argumentos):
    resultado = _ejecutar(raiz, "git", "-c", f"core.hooksPath={(raiz / '.sin-hooks').as_posix()}",
                          *argumentos)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return resultado.stdout.strip()


def _guardar(raiz):
    _git(raiz, "add", ".")
    _git(raiz, "-c", "user.name=Prueba", "-c", "user.email=prueba@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-m", "Caso de prueba")
    return _git(raiz, "rev-parse", "HEAD")


def _script(bash, raiz, *argumentos):
    return _ejecutar(raiz, bash, SCRIPT.as_posix(), *argumentos)


def _estado(repo):
    return (_git(repo, "show-ref"), _git(repo, "worktree", "list", "--porcelain", "-z"),
            _git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
            sorted(ruta.name for ruta in repo.parent.iterdir()))


def _rechaza_sin_cambios(bash, repo, *argumentos):
    antes = _estado(repo)
    resultado = _script(bash, repo, *argumentos)
    assert resultado.returncode != 0, resultado.stdout + resultado.stderr
    assert resultado.stdout or resultado.stderr, "El rechazo debe explicar el motivo"
    assert _estado(repo) == antes


def _crear(bash, repo, identificador="G-01", origen=None):
    resultado = _script(bash, origen or repo, "crear", identificador)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    destino = repo.with_name(f"{repo.name}-{identificador}")
    assert destino.is_dir()
    assert _git(destino, "branch", "--show-current") == f"item/{identificador}"
    assert _git(destino, "rev-parse", "HEAD") == _git(repo, "rev-parse", "main")
    assert not (destino / "clon/.venv").exists()
    for ruta in (destino, repo / "clon/.venv"):
        texto = ruta.as_posix()
        variantes = [texto]
        if ruta.drive:
            variantes.append(f"/{texto[0].lower()}{texto[2:]}")
        assert any(variante in resultado.stdout.replace("\\", "/") for variante in variantes), (
            f"La salida debe informar la ruta {texto}: {resultado.stdout}"
        )
    assert (repo / "clon/.venv/testigo.txt").read_text(encoding="utf-8") == "Entorno compartido\n"
    return destino


@pytest.fixture
def bash():
    ejecutable = shutil.which("bash")
    if ejecutable is None:
        pytest.skip("Se necesita bash para probar scripts/worktree_item.sh")
    return ejecutable


@pytest.fixture
def repo(tmp_path, bash):
    raiz = tmp_path / "repo con espacios"
    raiz.mkdir()
    _git(raiz, "init", "--initial-branch=main", "--template=")
    (raiz / ".gitignore").write_text("clon/.venv/\n", encoding="utf-8")
    (raiz / "control.txt").write_text("Contenido inicial\n", encoding="utf-8")
    _guardar(raiz)
    entorno = raiz / "clon/.venv"
    entorno.mkdir(parents=True)
    (entorno / "testigo.txt").write_text("Entorno compartido\n", encoding="utf-8")
    return raiz


@pytest.mark.parametrize("origen", ["principal", "subcarpeta", "worktree"])
def test_crear_desde_cualquier_origen_usa_principal_y_main(repo, bash, origen):
    _git(repo, "checkout", "-b", "trabajo")
    (repo / "solo_trabajo.txt").write_text("No pertenece a main\n", encoding="utf-8")
    assert _guardar(repo) != _git(repo, "rev-parse", "main")
    carpeta = repo
    if origen == "subcarpeta":
        carpeta = repo / "subcarpeta con espacios"
        carpeta.mkdir()
    elif origen == "worktree":
        carpeta = repo.parent / "otro worktree"
        _git(repo, "worktree", "add", "-b", "auxiliar", carpeta.as_posix(), "main")
    destino = _crear(bash, repo, origen=carpeta)
    assert not (destino / "solo_trabajo.txt").exists()
    assert _git(repo, "branch", "--show-current") == "trabajo"
    assert not _git(destino, "status", "--porcelain=v1", "--untracked-files=all")
    if carpeta != repo:
        assert not carpeta.with_name(f"{carpeta.name}-G-01").exists()


def test_crear_repetido_conserva_worktree_y_rama(repo, bash):
    destino = _crear(bash, repo)
    testigo = destino / "sin_seguimiento.txt"
    testigo.write_text("No sobrescribir\n", encoding="utf-8")
    antes = _git(destino, "status", "--porcelain=v1", "--untracked-files=all")
    _rechaza_sin_cambios(bash, repo, "crear", "G-01")
    assert testigo.read_text(encoding="utf-8") == "No sobrescribir\n"
    assert _git(destino, "status", "--porcelain=v1", "--untracked-files=all") == antes


@pytest.mark.parametrize("accion", ["crear", "borrar"])
@pytest.mark.parametrize("identificador", ["", "../escape", "con/barra", "con_guion_bajo",
                                          "con espacio", "niño", "Ａ", "G\n"])
def test_id_fuera_de_ascii_permitido_no_altera_nada(repo, bash, accion, identificador):
    _rechaza_sin_cambios(bash, repo, accion, identificador)


@pytest.mark.parametrize("argumentos", [(), ("crear",), ("borrar",), ("desconocida", "G-01"),
                                       ("crear", "G-01", "extra"), ("borrar", "G-01", "extra")])
def test_argumentos_invalidos_no_alteran_nada(repo, bash, argumentos):
    _rechaza_sin_cambios(bash, repo, *argumentos)


def test_carpeta_preexistente_conserva_contenido_y_no_crea_rama(repo, bash):
    destino = repo.with_name(f"{repo.name}-G-01")
    destino.mkdir()
    testigo = destino / "contenido.txt"
    testigo.write_text("Contenido ajeno\n", encoding="utf-8")
    _rechaza_sin_cambios(bash, repo, "crear", "G-01")
    assert testigo.read_text(encoding="utf-8") == "Contenido ajeno\n"
    assert sorted(ruta.name for ruta in destino.iterdir()) == ["contenido.txt"]


def test_rama_preexistente_no_crea_carpeta_ni_cambia_referencia(repo, bash):
    _git(repo, "branch", "item/G-01", "main")
    _rechaza_sin_cambios(bash, repo, "crear", "G-01")
    assert not repo.with_name(f"{repo.name}-G-01").exists()


def test_borrar_commit_no_fusionado_conserva_rama_y_worktree(repo, bash):
    destino = _crear(bash, repo)
    archivo = destino / "control.txt"
    archivo.write_text("Trabajo sin fusionar\n", encoding="utf-8")
    commit = _guardar(destino)
    assert not _git(destino, "status", "--porcelain=v1", "--untracked-files=all")
    _rechaza_sin_cambios(bash, repo, "borrar", "G-01")
    assert archivo.read_text(encoding="utf-8") == "Trabajo sin fusionar\n"
    assert _git(destino, "rev-parse", "HEAD") == commit
    assert _git(repo, "rev-parse", "item/G-01") == commit


@pytest.mark.parametrize("cambio", ["tracked", "staged", "untracked"])
def test_borrar_dirty_conserva_contenido_indice_y_worktree(repo, bash, cambio):
    destino = _crear(bash, repo)
    archivo = destino / ("nuevo.txt" if cambio == "untracked" else "control.txt")
    archivo.write_text("Trabajo pendiente\n", encoding="utf-8")
    if cambio == "staged":
        _git(destino, "add", "control.txt")
    antes = _git(destino, "status", "--porcelain=v1", "--untracked-files=all")
    indice = _git(destino, "diff", "--cached")
    _rechaza_sin_cambios(bash, repo, "borrar", "G-01")
    assert archivo.read_text(encoding="utf-8") == "Trabajo pendiente\n"
    assert _git(destino, "status", "--porcelain=v1", "--untracked-files=all") == antes
    assert _git(destino, "diff", "--cached") == indice


def test_borrar_worktree_manual_con_patron_item_jamas_lo_elimina(repo, bash):
    destino = repo.with_name(f"{repo.name}-G-01")
    _git(repo, "worktree", "add", "-b", "item/G-01", destino.as_posix(), "main")
    _rechaza_sin_cambios(bash, repo, "borrar", "G-01")
    assert (destino / "control.txt").read_text(encoding="utf-8") == "Contenido inicial\n"
    assert _git(destino, "branch", "--show-current") == "item/G-01"


def test_borrar_rechaza_worktree_propio_cambiado_a_otra_rama(repo, bash):
    destino = _crear(bash, repo)
    _git(destino, "checkout", "-b", "rama-ajena")
    _rechaza_sin_cambios(bash, repo, "borrar", "G-01")
    assert _git(destino, "branch", "--show-current") == "rama-ajena"
    assert (destino / "control.txt").exists()


def test_fusionar_y_borrar_elimina_solo_item_y_deja_principal_limpio(repo, bash):
    destino = _crear(bash, repo)
    (destino / "control.txt").write_text("Trabajo fusionado\n", encoding="utf-8")
    commit = _guardar(destino)
    _git(repo, "merge", "--ff-only", "item/G-01")
    assert _git(repo, "rev-parse", "main") == commit
    resultado = _script(bash, repo / "clon", "borrar", "G-01")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert not destino.exists()
    assert _git(repo, "branch", "--list") == "* main"
    assert _git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1
    assert not _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    assert (repo / "control.txt").read_text(encoding="utf-8") == "Trabajo fusionado\n"
    assert (repo / "clon/.venv/testigo.txt").read_text(encoding="utf-8") == "Entorno compartido\n"


def test_variables_git_heredadas_no_salen_de_tmp_path(repo, bash, monkeypatch):
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.setenv(variable, str(repo.parent / "ruta_inexistente"))
    destino = _crear(bash, repo)
    assert _git(destino, "rev-parse", "--show-toplevel").replace("\\", "/") == destino.as_posix()
    assert not (repo.parent / "ruta_inexistente").exists()
