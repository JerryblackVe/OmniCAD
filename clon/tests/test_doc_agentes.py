# -*- coding: utf-8 -*-
"""Documentación para agentes (`docs/agentes/`): `herramientas.md` está generado desde el catálogo y tiene que
coincidir con él; los demás documentos no pueden tener enlaces rotos, configuraciones inválidas ni subcomandos o
opciones sin documentar."""
import copy
import json
import re
import tomllib
from pathlib import Path

import pytest

from omnicad import api
from omnicad.api import doc_markdown
from omnicad.cli import construir_parser, main

RAIZ = Path(__file__).resolve().parents[2]            # D:/PROGRAMA
DOCS = RAIZ / "docs" / "agentes"
EJEMPLOS = RAIZ / "ejemplos" / "agentes"
HERRAMIENTAS = DOCS / "herramientas.md"
CLIENTES = ("Claude Code", "Claude Desktop", "OpenCode", "Codex CLI", "Cursor", "Gemini CLI", "VS Code")


def lf(texto):
    """Tolera archivos con saltos CRLF (git en Windows puede convertirlos)."""
    return texto.replace("\r\n", "\n")


def leer(ruta):
    return lf(Path(ruta).read_text(encoding="utf-8"))


def documentos():
    return sorted(DOCS.glob("*.md")) + [EJEMPLOS / "README.md"]


# ---------------------------------------------------------------- herramientas.md (generado)
def test_herramientas_md_coincide_con_el_catalogo():
    esperado = doc_markdown.catalogo_a_markdown(api.catalogo())
    assert leer(HERRAMIENTAS) == esperado, (
        f"{HERRAMIENTAS.relative_to(RAIZ)} está desactualizado respecto del catálogo. Regenerarlo con: "
        f"{doc_markdown.COMANDO_REGENERAR}")


def test_el_generador_nota_un_cambio_de_descripcion():
    """Si cambia una descripción del catálogo, el texto generado cambia (y entonces el test de arriba falla)."""
    catalogo = api.catalogo()
    tocado = copy.deepcopy(catalogo)
    tocado[0]["descripcion"] += " (cambiada)"
    assert doc_markdown.catalogo_a_markdown(tocado) != doc_markdown.catalogo_a_markdown(catalogo)
    sin_una = [h for h in catalogo if h["nombre"] != catalogo[-1]["nombre"]]
    assert doc_markdown.catalogo_a_markdown(sin_una) != doc_markdown.catalogo_a_markdown(catalogo)


def test_cli_markdown_da_lo_mismo_que_el_archivo(capsys, tmp_path):
    capsys.readouterr()
    assert main(["tools", "--markdown"]) == 0
    assert lf(capsys.readouterr().out) == leer(HERRAMIENTAS)
    destino = tmp_path / "carpeta nueva" / "herramientas.md"
    assert main(["tools", "--markdown", "--output", str(destino)]) == 0
    assert b"\r" not in destino.read_bytes()                       # siempre "\n", sin importar el sistema
    assert destino.read_text(encoding="utf-8") == leer(HERRAMIENTAS)


@pytest.mark.parametrize("argv", [["tools", "--markdown", "--json"], ["tools", "--markdown", "--group", "solido"],
                                  ["tools", "--output", "x.md"]])
def test_cli_markdown_combinaciones_invalidas(argv, capsys):
    assert main(argv) == 2
    salida = capsys.readouterr()
    assert "error" in salida.out + salida.err


def test_todas_las_herramientas_estan_documentadas():
    texto = leer(HERRAMIENTAS)
    assert texto.startswith("<!-- ARCHIVO GENERADO: no editar a mano")
    for h in api.catalogo():
        assert f"### `{h['nombre']}`" in texto, h["nombre"]
        assert h["grupo"] in doc_markdown.GRUPOS, f"grupo nuevo sin descripción en doc_markdown.GRUPOS: {h['grupo']}"
        for parametro in h["esquema"]["properties"]:
            assert f"`{parametro}`" in texto


# ---------------------------------------------------------------- enlaces y bloques de código
def test_los_documentos_existen():
    for nombre in ("README", "conectar", "guia_diseno", "cli", "puente", "herramientas"):
        assert (DOCS / f"{nombre}.md").is_file(), nombre


def enlaces(ruta):
    texto = re.sub(r"```.*?```", "", leer(ruta), flags=re.S)       # los bloques de código no tienen enlaces
    texto = re.sub(r"`[^`\n]*`", "", texto)
    return re.findall(r"\]\(([^)\s]+)\)", texto)


@pytest.mark.parametrize("ruta", documentos(), ids=lambda r: r.name)
def test_enlaces_relativos_apuntan_a_archivos_que_existen(ruta):
    for destino in enlaces(ruta):
        if destino.startswith(("http://", "https://", "mailto:", "#")):
            continue
        archivo = destino.split("#")[0]
        assert (ruta.parent / archivo).resolve().exists(), f"{ruta.name}: enlace roto a {destino}"


def anclas(ruta):
    """Anclas de los títulos, como las arma GitHub (minúsculas, sin signos, espacios a guiones)."""
    resultado = set()
    for titulo in re.findall(r"^#{1,6}\s+(.+)$", re.sub(r"```.*?```", "", leer(ruta), flags=re.S), flags=re.M):
        limpio = re.sub(r"[^\w\s-]", "", titulo.lower().replace("`", ""))
        resultado.add(re.sub(r"\s", "-", limpio.strip()))
    return resultado


@pytest.mark.parametrize("ruta", documentos() + [RAIZ / "docs" / "arquitectura.md"], ids=lambda r: r.name)
def test_anclas_de_los_enlaces_existen(ruta):
    for destino in enlaces(ruta):
        if destino.startswith(("http://", "https://", "mailto:")) or "#" not in destino:
            continue
        archivo, _, ancla = destino.partition("#")
        objetivo = ruta if not archivo else (ruta.parent / archivo).resolve()
        if objetivo.suffix == ".md" and objetivo.exists():
            assert ancla in anclas(objetivo), f"{ruta.name}: el ancla #{ancla} no existe en {objetivo.name}"


def bloques(ruta, lenguaje):
    return re.findall(rf"```{lenguaje}\n(.*?)```", leer(ruta), flags=re.S)


def test_los_bloques_json_y_toml_son_validos():
    for ruta in documentos():
        for texto in bloques(ruta, "json"):
            json.loads(texto)
        for texto in bloques(ruta, "toml"):
            tomllib.loads(texto)
    assert len(bloques(DOCS / "conectar.md", "json")) >= 5 and len(bloques(DOCS / "conectar.md", "toml")) == 1


# ---------------------------------------------------------------- conectar.md
def secciones(ruta):
    partes = re.split(r"^## ", leer(ruta), flags=re.M)
    return {p.split("\n", 1)[0].strip(): p for p in partes[1:]}


@pytest.mark.parametrize("cliente", CLIENTES)
def test_cada_cliente_dice_no_probado_y_trae_su_comando(cliente):
    seccion = secciones(DOCS / "conectar.md")[cliente]
    assert "no probado" in seccion.lower()
    assert "omnicad.servidor_mcp" in seccion
    assert "Fuente:" in seccion


def test_conectar_tiene_los_siete_clientes():
    nombres = set(secciones(DOCS / "conectar.md"))
    assert set(CLIENTES) <= nombres


def test_el_comando_del_mcp_existe():
    texto = leer(DOCS / "conectar.md")
    assert "D:/PROGRAMA/clon/.venv/Scripts/python.exe -m omnicad.servidor_mcp" in texto
    assert "omnicad-mcp.exe" in texto
    assert (RAIZ / "clon" / "omnicad" / "servidor_mcp" / "__main__.py").is_file()


def test_las_opciones_del_servidor_mcp_estan_documentadas():
    from omnicad.servidor_mcp.principal import _parser
    texto = leer(DOCS / "conectar.md") + leer(DOCS / "puente.md")
    for accion in _parser()._actions:
        for opcion in accion.option_strings:
            if opcion.startswith("--") and opcion not in ("--help", "--version"):
                assert opcion in texto, f"la opción {opcion} de omnicad-mcp no está en conectar.md ni puente.md"


# ---------------------------------------------------------------- cli.md y puente.md
def test_cada_subcomando_de_la_cli_esta_en_cli_md():
    subparsers = next(a for a in construir_parser()._actions if a.dest == "comando")
    texto = leer(DOCS / "cli.md")
    for nombre in subparsers.choices:
        assert f"### {nombre}\n" in texto, f"el subcomando {nombre} no tiene sección en cli.md"


def test_cada_error_del_puente_esta_en_puente_md():
    texto = leer(DOCS / "puente.md")
    for kind in ("UNAUTHORIZED", "APP_BUSY", "APP_NOT_RUNNING", "APP_NOT_RESPONDING", "UNSAVED_CHANGES",
                 "LIVE_NOT_ALLOWED", "BRIDGE_ERROR", "NESTED_CHECKS"):
        assert kind in texto, kind


def test_los_temas_de_la_guia_estan_en_guia_diseno_md():
    texto = leer(DOCS / "guia_diseno.md")
    for tema in sorted((RAIZ / "clon" / "omnicad" / "api" / "guia").glob("*.md")):
        assert f"({'../../clon/omnicad/api/guia/' + tema.name})" in texto, tema.name
