# -*- coding: utf-8 -*-
"""Regresión de las consultas extraídas de API/timeline/visor."""
import ast
from pathlib import Path

import numpy as np

from omnicad.nucleo import consultas as c
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs


def test_consultas_de_caja_conservan_medidas_y_seleccion():
    caja = geo.caja(10, 20, 30)
    assert c.es_forma(caja) and geo.es_valida(caja)
    assert np.isclose(geo.volumen(caja), 6000)
    assert c.dentro_solidos([caja], (5, 10, 15))
    assert not c.dentro_solidos([caja], (50, 10, 15))
    assert c.distancia_a_punto(caja, (15, 10, 15)) == 5
    assert np.allclose(c.centroide(caja), (5, 10, 15))
    assert c.firma_importacion(caja, "solido")[:2] == ("solido", 6)
    assert len(c.hijos_compuesto(geo.compuesto([caja, geo.trasladar(caja, (20, 0, 0))]))) == 2
    arista = refs.subformas(caja, "arista")[0]
    a, b = c.extremos_arista(arista)
    punto, tangente = c.punto_y_tangente(arista)
    assert np.allclose(punto, (a + b) / 2)
    assert np.isclose(np.linalg.norm(tangente), 1)
    assert np.isclose(np.linalg.norm(c.datos_arista(arista, caja)[1]), 1)
    cara = geo.caras(caja)[0]
    assert c.punto_en_cara(cara, geo.centro_masa(cara, True))
    assert len(c.puntos_enganche_cara(cara)) >= 5


def test_importador_sab_conserva_identidad_del_modulo():
    from omnicad.io_archivos import acis_occ as anterior
    from omnicad.nucleo import acis_occ as nuevo
    assert anterior is nuevo


def test_solo_el_nucleo_importa_el_kernel():
    raiz = Path(__file__).resolve().parents[1] / "omnicad"
    encontrados = []
    for ruta in raiz.rglob("*.py"):
        if ruta.is_relative_to(raiz / "nucleo"):
            continue
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8-sig"))):
            modulos = [nodo.module or ""] if isinstance(nodo, ast.ImportFrom) else (
                [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else [])
            if any(m == "OCP" or m.startswith("OCP.") for m in modulos):
                encontrados.append((str(ruta.relative_to(raiz)), nodo.lineno))
    assert encontrados == []
