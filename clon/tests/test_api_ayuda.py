# -*- coding: utf-8 -*-
"""search_help (api/herramientas_ayuda.py): la ayuda local de OmniCAD, con su fuente."""
import time

import pytest

from omnicad import api
from omnicad.api import herramientas_ayuda


@pytest.fixture
def sesion():
    return api.Sesion()


def buscar(sesion, query, **kw):
    return api.llamar(sesion, "search_help", {"query": query, **kw})


@pytest.mark.parametrize("query", ["empalme", "EMPALMÉ", "fillet", "Fillet"])
def test_encuentra_empalme_con_y_sin_tilde(sesion, query):
    r = buscar(sesion, query)
    assert r["ok"] and r["avisos"] == []
    primero = r["result"]["results"][0]
    assert primero["source"] == "herramienta fillet" and primero["score"] > 0 and "empalme" in primero["text"].lower()
    puntajes = [x["score"] for x in r["result"]["results"]]
    assert puntajes == sorted(puntajes, reverse=True)


def test_busca_en_la_guia_y_en_la_doc_del_repo(sesion):
    fuentes = [x["source"] for x in buscar(sesion, "agujero roscado ajuste", limit=20)["result"]["results"]]
    assert "api/guia/flujo.md › Agujeros, roscas y ajustes" in fuentes
    fuentes = [x["source"] for x in buscar(sesion, "toolsets", limit=20)["result"]["results"]]
    assert any(f.startswith("docs/agentes/conectar.md") for f in fuentes)
    assert not any("fusion_docs" in f or "herramientas.md" in f for f in fuentes)


def test_limit_y_errores(sesion):
    assert len(buscar(sesion, "boceto", limit=2)["result"]["results"]) == 2
    for query in ("", "   ", "¿?"):
        r = buscar(sesion, query)
        assert r["error_kind"] == "INVALID_ARGUMENTS" and "vacía" in r["mensaje"], query
    for limit in (0, 21):
        assert buscar(sesion, "empalme", limit=limit)["error_kind"] == "INVALID_ARGUMENTS"


def test_sin_resultados_avisa(sesion):
    r = buscar(sesion, "xyzzyq")
    assert r["ok"] and r["result"]["results"] == [] and "sin inventar" in r["avisos"][0]


def test_sin_docs_del_repo_no_falla(sesion, tmp_path, monkeypatch):
    """La app instalada no trae docs/: busca igual en el catálogo y la guía."""
    (tmp_path / "README.md").write_text("toolsets selector de otra cosa", encoding="utf-8")   # carpeta ajena
    monkeypatch.setattr(herramientas_ayuda, "RAIZ_REPO", tmp_path)
    fuentes = [x["source"] for x in buscar(sesion, "toolsets selector", limit=20)["result"]["results"]]
    assert fuentes and not any(f.startswith(("docs/", "README")) for f in fuentes)


def test_es_rapida(sesion):
    inicio = time.perf_counter()
    buscar(sesion, "como hago un agujero roscado con empalme")
    buscar(sesion, " ".join(f"palabra{i}" for i in range(3000)))      # un pegado enorme tampoco tarda
    assert time.perf_counter() - inicio < 1
