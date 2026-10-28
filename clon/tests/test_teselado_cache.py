# -*- coding: utf-8 -*-
"""Equivalencia y rendimiento de la caché visual de caras; no cambia el B-rep.

Banco real, desde clon/, reutilizando sin modificaciones medir_previa_comandos.py:
    .venv/Scripts/python.exe ../scripts/turno.py --plazo 1500 -- .venv/Scripts/python.exe tests/test_teselado_cache.py --medir antes --modelo placa200
La salida propia vive en evidencias/teselado_cache_2026-10-28/<etapa>/, fuera de los informes anteriores.
"""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import render_cpu as rc
from omnicad.nucleo import solidos_modificar as sm


@pytest.fixture(autouse=True)
def cache_vacia():
    rc._vaciar_cache_caras()
    yield
    rc._vaciar_cache_caras()


def _placa():
    agujeros = [geo.cilindro(2, 14, (8 + i % 5 * 12, 10 + i // 5 * 16, -2)) for i in range(10)]
    return geo.booleano(geo.caja(80, 50, 10), geo.compuesto(agujeros), "cortar")


def _empalmar(forma, radio):
    return sm.empalme(forma, [{"aristas": [refs.subformas(forma, "arista")[0]],
                              "tipo": "constante", "radio": radio}], cadena_tangente=False)


def _forma(caso):
    if caso == "empalme":
        return _empalmar(geo.caja(20, 30, 10), 2)
    placa = _placa()
    if caso in ("cortar", "unir"):
        return geo.booleano(placa, geo.caja(16, 20, 8, (75, 35, 4)), caso)
    if caso == "patron":
        return geo.compuesto([placa, geo.trasladar(placa, (100, 0, 0)),
                              geo.rotar(placa, (0, 0, 0), (0, 0, 1), 60)])
    return placa


def _sin_cache(forma, deflexion=0.05, angular=0.3):
    """Referencia independiente: el recorrido de malla_suave anterior a la caché."""
    from omnicad.nucleo.analisis import _indices, _props_nodos
    partes = []
    for cara, tris in geo.teselar_por_cara(forma, deflexion, angular):
        if geo.BRep_Tool.Surface_s(cara) is None:
            n = rc.normales_suaves(tris, None, 60.0)[1]
        else:
            tri = geo.BRep_Tool.Triangulation_s(cara, geo.TopLoc_Location())
            idx = _indices(tri, cara)
            n = _props_nodos(cara, tri, idx, tris, False)[0][idx].reshape(-1, 3)
        partes.append((tris.reshape(-1, 3), n))
    return rc._juntar(partes)


def _iguales(esperada, obtenida):
    for a, b in zip(esperada, obtenida, strict=True):
        assert a.shape == b.shape
        assert np.allclose(a, b, atol=1e-6, rtol=1e-6)


def _volumen_malla(vertices):
    tris = np.asarray(vertices, float).reshape(-1, 3, 3)
    tris = tris - tris.mean(axis=(0, 1))
    return abs(float(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum()) / 6)


@pytest.mark.parametrize("caso", ["empalme", "placa", "cortar", "unir", "patron"])
def test_cache_igual_al_recorrido_original(caso):
    forma = _forma(caso)
    volumen = geo.volumen(forma)
    esperada = _sin_cache(forma)
    _iguales(esperada, rc.malla_suave(forma, 0.05, 0.3))
    _iguales(esperada, rc.malla_suave(forma, 0.05, 0.3))
    assert _volumen_malla(esperada[0]) == pytest.approx(volumen, rel=0.01)
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(volumen, rel=1e-10)


def test_deflexion_y_angulo_invalidan_cache(monkeypatch):
    forma = geo.cilindro(10, 20)
    convertir = geo._triangulos_cara
    llamadas = []

    def contar(*args):
        llamadas.append(1)
        return convertir(*args)
    monkeypatch.setattr(geo, "_triangulos_cara", contar)
    rc.malla_suave(forma, 0.05, 0.3)
    n = len(llamadas)
    assert n == 3
    rc.malla_suave(forma, 0.05, 0.3)
    assert len(llamadas) == n
    rc.malla_suave(forma, 0.02, 0.3)
    assert len(llamadas) == 2 * n
    rc.malla_suave(forma, 0.02, 0.1)
    assert len(llamadas) == 3 * n


def test_otro_teselado_mas_fino_no_devuelve_arrays_viejos():
    forma = geo.cilindro(10, 20)
    vieja = rc.malla_suave(forma, 0.2, 0.6)
    geo.teselar_por_cara(forma, 0.005, 0.1, rehacer=True)
    esperada = _sin_cache(forma, 0.2, 0.6)
    nueva = rc.malla_suave(forma, 0.2, 0.6)
    assert len(nueva[0]) > len(vieja[0])
    _iguales(esperada, nueva)


def test_editar_arista_no_reutiliza_geometria_vieja():
    caja = geo.caja(20, 30, 10)
    vieja = rc.malla_suave(caja, 0.03, 0.2)
    for radio in (1, 3):
        editada = _empalmar(caja, radio)
        nueva = rc.malla_suave(editada, 0.03, 0.2)
        _iguales(_sin_cache(editada, 0.03, 0.2), nueva)
        assert _volumen_malla(nueva[0]) == pytest.approx(geo.volumen(editada), rel=0.005)
        assert geo.volumen(editada) < _volumen_malla(vieja[0])
        assert geo.es_valida(editada)


def test_ubicacion_y_orientacion_no_se_confunden():
    cara = geo.caras(geo.caja(10, 20, 30))[0]
    original = rc.malla_suave(cara, 0.05, 0.3)
    for otra in (cara.Reversed(), geo.trasladar(cara, (40, 30, 20))):
        _iguales(_sin_cache(otra), rc.malla_suave(otra, 0.05, 0.3))
    invertida = rc.malla_suave(cara.Reversed(), 0.05, 0.3)
    assert np.allclose(invertida[1], -original[1])


def test_tres_copias_con_location_reusan_arrays_locales(monkeypatch):
    from omnicad.nucleo import solidos_crear as sc
    original = _empalmar(geo.caja(20, 30, 10), 2)
    traslado = np.eye(4)
    traslado[:3, 3] = (50, 60, 70)
    giro = np.array([[0., -1., 0., 20.], [1., 0., 0., 40.], [0., 0., 1., 10.], [0., 0., 0., 1.]])
    patron = geo.compuesto([original, sc.instanciar(original, traslado), sc.instanciar(original, giro)])
    esperada = _sin_cache(patron)
    rc.malla_suave(original, 0.05, 0.3)
    convertir = geo._triangulos_cara
    llamadas = []

    def contar(*args):
        llamadas.append(1)
        return convertir(*args)
    monkeypatch.setattr(geo, "_triangulos_cara", contar)
    _iguales(esperada, rc.malla_suave(patron, 0.05, 0.3))
    assert not llamadas
    assert geo.es_valida(patron)
    assert _volumen_malla(esperada[0]) == pytest.approx(3 * geo.volumen(original), rel=0.005)


def test_lru_acota_bytes_y_conserva_la_cara_usada(monkeypatch):
    monkeypatch.setattr(rc, "_TOPE_CACHE_CARAS", 3)
    monkeypatch.setattr(rc, "_TOPE_BYTES_CARAS", 1000)
    rc.malla_suave(geo.caja(10, 20, 30), 0.05, 0.3)
    assert len(rc._CACHE_CARAS) == 3
    primera, segunda, _ = rc._CACHE_CARAS
    rc._leer_malla_cara(primera)
    rc._guardar_malla_cara(("nueva",), np.zeros((6, 3)), np.zeros((6, 3)))
    assert primera in rc._CACHE_CARAS and segunda not in rc._CACHE_CARAS
    assert rc._CACHE_CARAS_BYTES == sum(v.nbytes + n.nbytes for v, n in rc._CACHE_CARAS.values()) <= 1000


def test_modificar_arrays_devuelto_no_contamina_cache():
    forma = geo.caja(10, 20, 30)
    vertices, normales = rc.malla_suave(forma)
    vertices[:] = 999
    normales[:] = 0
    _iguales(_sin_cache(forma, 0.05, 0.25), rc.malla_suave(forma))


def test_arrastre_grueso_conserva_malla_fina_y_cuerpo():
    forma = _placa()
    fina = rc.malla_suave(forma, 0.05, 0.3)
    volumen = geo.volumen(forma)
    gruesa = rc._malla_arrastre(forma, 0.05, 0.3)
    assert len(gruesa[0]) < len(fina[0]) / 2
    _iguales(fina, _sin_cache(forma, 0.05, 0.3))
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(volumen, rel=1e-10)


def test_visor_recupera_malla_fina_al_soltar(monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.operaciones import Cuerpo, EstadoModelo
    from omnicad.ui.visor3d import Visor3D, teselar_cuerpo
    app = QApplication.instance() or QApplication([])
    forma = geo.compuesto([geo.cilindro(2, 10, (i * 6, 0, 0)) for i in range(22)])  # 66 caras
    visor = Visor3D()
    estado = EstadoModelo()
    estado.cuerpos["c1"] = Cuerpo("c1", "Prueba", forma, "op1")
    fina = teselar_cuerpo(forma, visor._deflexion(forma), visor.config.angular, False)
    arrastrando = [True]
    monkeypatch.setattr(visor, "_arrastrando_previa", lambda: arrastrando[0])
    try:
        visor.set_modelo(estado, apariencias={"c1": (0.2, 0.3, 0.4)})
        assert visor._previa_gruesa
        assert len(visor._mallas[0]["v"]) < len(fina[0]) / 2
        arrastrando[0] = False
        QTest.qWait(300)
        assert not visor._previa_gruesa and visor._modelo_por_refinar is None
        _iguales(fina, (visor._mallas[0]["v"], visor._mallas[0]["n"]))
        assert visor._mallas[0]["color"] == (0.2, 0.3, 0.4)
    finally:
        visor.close()
        visor.deleteLater()
        app.processEvents()


def _medir():
    etapa = sys.argv[sys.argv.index("--medir") + 1]
    assert etapa in ("antes", "cara", "despues", "despues_final"), etapa
    raiz = Path(__file__).resolve().parents[2]
    salida = raiz / "evidencias" / "teselado_cache_2026-10-28" / etapa
    assert (raiz / "evidencias").is_dir()
    (salida / "docs" / "auditorias").mkdir(parents=True, exist_ok=True)
    (salida / "evidencias").mkdir(exist_ok=True)
    banco = runpy.run_path(str(raiz / "scripts" / "medir_previa_comandos.py"))
    banco["main"].__globals__["RAIZ"] = salida
    modelo = sys.argv[sys.argv.index("--modelo") + 1]
    sys.argv = ["medir_previa_comandos.py", "--modelo", modelo, "--comandos", "empalme", "chaflan", "cortar", "unir",
                "patron_rectangular", "patron_circular"]
    banco["main"]()


def _sondar_grueso():
    """Costo previo a elegir detalle de arrastre; tres muestras frías, sin ventana ni caché."""
    import time
    from omnicad.timeline.documento import Documento
    raiz = Path(__file__).resolve().parents[2]
    banco = runpy.run_path(str(raiz / "scripts" / "medir_previa_comandos.py"))
    receta, _ = banco["_modelo"]("placa200")
    doc = Documento.desde_dict(receta)
    forma = next(iter(doc.estado_final.cuerpos.values())).forma
    arista = max(refs.subformas(forma, "arista"), key=lambda a: refs.firma_arista(a)["largo"])
    formas = {"empalme": sm.empalme(forma, [{"aristas": [arista], "tipo": "constante", "radio": 1}]),
              "cortar": geo.booleano(forma, geo.caja(20, 30, 12, (385, 285, 5)), "cortar"),
              "copia_patron": geo.trasladar(forma, (120, 0, 0))}
    rc._TOPE_CACHE_CARAS = 0
    for caso, cuerpo in formas.items():
        for factor, angular in ((1, 0.3), (4, rc.ANGULAR_ARRASTRE)):
            tiempos = []
            for _ in range(3):
                copia = geo.BRepBuilderAPI_Copy(cuerpo, False, False).Shape()
                inicio = time.perf_counter()
                vertices, _ = rc.malla_suave(copia, rc.deflexion_para(cuerpo) * factor, angular, rehacer=True)
                tiempos.append(round((time.perf_counter() - inicio) * 1000, 1))
            print(caso, "factor", factor, "angular", angular, "ms", tiempos, "triangulos", len(vertices) // 3, flush=True)


def _comparar():
    """Verifica los umbrales sobre las corridas reales guardadas; no modifica el informe previo."""
    from datetime import date
    import json
    raiz = Path(__file__).resolve().parents[2] / "evidencias" / "teselado_cache_2026-10-28"
    datos = {}
    for etapa in ("antes", "despues_final"):
        ruta = raiz / etapa / "docs" / "auditorias" / f"previa-comandos-{date.today().isoformat()}.md"
        texto = ruta.read_text(encoding="utf-8")
        datos[etapa] = json.loads(texto.split("<!-- DATOS_PREVIA -->\n```json\n", 1)[1].split("\n```", 1)[0])
        assert len(datos[etapa]["casos"]) == 6
        for modelos in datos[etapa]["casos"].values():
            assert set(modelos) == {"chico", "mediano", "grande", "placa200"}
            for corridas in modelos.values():
                validas = [r for r in corridas if r["valida"]]
                assert len(validas) == 3
                assert all(r["fps"] > 0 and r["previa_ok"] for r in validas)
    print("caso | T antes | T después | reducción T | previa antes | previa después | reducción previa")
    for caso in datos["antes"]["casos"]:
        medidas = []
        for etapa in datos:
            rs = [r for r in datos[etapa]["casos"][caso]["placa200"] if r["valida"]]
            medidas.append([float(np.median([v for r in rs for v in r["muestras_ms"][k]]))
                            for k in ("teselado_por_modelo", "previa")])
        (ta, pa), (td, pd) = medidas
        assert td <= ta / 2, (caso, ta, td)
        assert pd <= pa * 0.7, (caso, pa, pd)
        print(f"{caso} | {ta:.1f} | {td:.1f} | {100 * (1 - td / ta):.1f}% | "
              f"{pa:.1f} | {pd:.1f} | {100 * (1 - pd / pa):.1f}%")
    for modelo in ("chico", "mediano", "grande"):
        maximos = []
        for etapa in datos:
            maximos.append(max(r["etapas"]["previa"]["p95"] for ms in datos[etapa]["casos"].values()
                               for r in ms[modelo] if r["valida"]))
        assert maximos[1] <= 33, (modelo, maximos)
        print(modelo, "máximo p95 por corrida antes/después:", maximos)
    print("Umbrales OK: T >=50% y previa >=30% menos en los seis casos; 72 corridas válidas por etapa.")


if __name__ == "__main__":
    if "--comparar" in sys.argv:
        _comparar()
    elif "--sondar-grueso" in sys.argv:
        _sondar_grueso()
    else:
        _medir()
