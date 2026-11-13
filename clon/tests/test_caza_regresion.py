# -*- coding: utf-8 -*-
"""Cazador de errores (scripts/caza): repite los casos mínimos confirmados de tests/corpus_caza/ y prueba sus piezas.

Un caso cuyo bug sigue abierto en docs/seguimiento/ queda como xfail; cuando la fila se borra, tiene que pasar."""
import json
import random
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "caza"))

import cazar  # noqa: E402
import generador as gen  # noqa: E402
import jueces as j  # noqa: E402
import trabajador  # noqa: E402
from omnicad import api  # noqa: E402

CASOS = sorted((Path(__file__).parent / "corpus_caza").glob("*.json"))
SEGUIMIENTO = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "docs" / "seguimiento").glob("*.md"))


def abierto(ident):
    return f"| {ident} |" in SEGUIMIENTO


@pytest.fixture(scope="module")
def proceso(tmp_path_factory):
    """Los casos corren en un proceso aparte: algunos tiran abajo el proceso, y tiene que ser ese."""
    cazar.ESTADO = tmp_path_factory.mktemp("caza")       # la bitácora no pisa la de una corrida real
    fuente = cazar.Fuente()
    yield fuente
    fuente.cerrar()


@pytest.mark.parametrize("ruta", CASOS, ids=lambda r: r.stem)
def test_caso_del_corpus(ruta, proceso):
    caso = json.loads(ruta.read_text(encoding="utf-8"))
    fallo = proceso.pedir({"tipo": "repetir", "pasos": caso["pasos"], "pesado": caso.get("pesado", False)}, 40)["fallo"]   # `pesado`: autointersecciones también en caras curvas
    if fallo and abierto(caso["id"]):
        pytest.xfail(f"{caso['id']} sigue abierto: {cazar.firma_de(fallo)}")
    assert fallo is None, f"{caso['id']} volvió a fallar: {fallo}"


def test_conocidos_nombran_filas_abiertas():
    conocidos = json.loads(cazar.CONOCIDOS.read_text(encoding="utf-8"))
    cerrados = {i for i in conocidos.values() if not abierto(i)}
    assert not cerrados, f"Firmas que apuntan a filas ya borradas: {cerrados}"


def test_lista_de_exclusiones_sin_nombres_muertos():
    nombres = {h["nombre"] for h in api.catalogo()}
    assert set(gen.EXCLUIDAS) <= nombres
    assert gen.FUERA_DE_CADENA <= nombres
    assert set(gen.FIJOS) <= nombres


def test_reductor_deja_el_caso_minimo():
    class FuenteFalsa:
        pedidos = 0

        def pedir(self, ped, _plazo):
            self.pedidos += 1
            pasos = ped["pasos"]
            importa = [p for p in pasos if p["tool"] in ("b", "d") and p["args"].get("radio")]
            return {"fallo": {"juez": "geometria", "op": "d", "kind": "x"} if len(importa) == 2 else None}

    receta = [{"tool": t, "args": {"radio": 1.23456, "basura": True}} for t in "abcde"]
    minimo = cazar.reducir(FuenteFalsa(), receta, "geometria|d|x", 30)
    assert minimo == [{"tool": t, "args": {"radio": 1.2}} for t in "bd"]


def test_el_plan_sigue_lo_que_falta_y_aguanta_listas_vacias(tmp_path, monkeypatch):
    monkeypatch.setattr(cazar, "ESTADO", tmp_path)
    cob = cazar.Cobertura()
    assert set(cazar.RELATIVAS) == set(gen.FACTORES)
    cob.pares = {f">{h}": 9 for h in "ab"}          # "c" es el par que falta después de la pieza semilla
    rng = random.Random(0)
    primeros = [cob.plan(rng, ["a", "b", "c"], None, ["a", "b", "c"], 1)[0] for _ in range(60)]
    assert sum(h == "c" for h, _ in primeros) > 30
    assert all(c in (*cazar.RELATIVAS, *cazar.EXTREMAS) for _, c in primeros)
    assert cob.plan(rng, ["a"], [], [], 2)


def test_un_memoryerror_atrapado_es_hallazgo():
    j.vigilar_memoria()
    try:
        try:
            raise MemoryError
        except MemoryError:
            pass
        falla = j.juez_memoria("fillet")
    finally:
        sys.monitoring.set_events(j.TOOL_MEMORIA, 0)
        sys.monitoring.free_tool_id(j.TOOL_MEMORIA)
    assert falla["juez"] == "memoria" and falla["kind"].startswith("MemoryError@")
    assert j.juez_memoria("fillet") is None
    assert j.juez_memoria("fillet", 300, 2000)["kind"] == "pico"
    assert j.juez_memoria("fillet", 300, 900) is None


def test_el_contrato_marca_lo_suelto_y_acepta_lo_claro():
    assert j.juez_contrato({"ok": True}) is None
    assert j.juez_contrato({"ok": False, "error_kind": "OPERATION_FAILED", "mensaje": "No se pudo calcular el paso."}) is None
    assert j.juez_contrato({"ok": False, "mensaje": "x"})["kind"] == "sin_error_kind"
    assert j.juez_contrato({"ok": False, "error_kind": "INTERNAL_ERROR", "mensaje": "x"})["kind"] == "INTERNAL_ERROR"
    assert j.juez_contrato({"ok": False, "error_kind": "OPERATION_FAILED", "mensaje": "command not done, object is invalid"})
    assert j.juez_contrato({"ok": True}, "radius")["kind"] == "acepta_invalido"
    assert j.juez_contrato({"ok": False, "error_kind": "INVALID_ARGUMENTS", "mensaje": "start=object necesita una cara."}) is None


def test_la_pieza_real_exige_que_sus_pasos_validos_se_completen():
    rechazo = {"ok": False, "error_kind": "OPERATION_FAILED", "mensaje": "La distancia debe ser positiva."}
    assert j.juez_contrato(rechazo) is None
    assert j.juez_contrato(rechazo, exito=True)["kind"] == "rechaza_valido"
    assert j.juez_contrato({"ok": True}, exito=True) is None
    for nombre, cadena in gen.CADENAS_REALES.items():
        caso = json.loads((Path(__file__).parent / "corpus_caza" / f"real_{nombre}.json").read_text(encoding="utf-8"))
        pasos = [{"tool": t, "args": a, "exito": True} for t, a in cadena(random.Random(1))]
        assert caso["pasos"] == pasos


def test_geometria_cuenta_solo_lo_que_aparece_en_el_paso():
    previo = {"C": {"autointersecciones": 2, "abierto": 0}}
    assert j.juez_geometria(previo, previo) is None
    assert j.juez_geometria(previo, {"C": {"autointersecciones": 3, "abierto": 0}})["kind"] == "autointersecciones"


def test_la_pieza_real_conserva_solidos_cerrados_incluso_con_defectos_previos():
    class ApiFalsa:
        def llamar(self, _s, tool, _args):
            assert tool == "check_geometry"
            return {"ok": True, "result": {"bodies": [
                {"name": "Sólido", "type": "solid", "valid": True, "closed": True},
                {"name": "Abierto", "type": "solid", "valid": True, "closed": False},
                {"name": "Superficie", "type": "surface", "valid": True},
            ]}}

    d = j.defectos(ApiFalsa(), None, False, solidos=True)
    assert j.juez_geometria({}, {"Sólido": d["Sólido"]}) is None
    assert j.juez_geometria({}, {"Abierto": d["Abierto"]})["kind"] == "abierto"
    assert j.juez_geometria({}, {"Superficie": d["Superficie"]})["kind"] == "no_solido"
    with patch.object(j, "foto", return_value={}), patch.object(j, "defectos", return_value=d) as leer:
        f, _, _ = trabajador.juzgar(api.Sesion(), "section_view", {}, [], d, {}, ".", False, False, 0, exito=True)
    assert f["kind"] == "abierto"
    assert leer.call_args.kwargs["solidos"] is True


def test_las_cadenas_reales_cubren_ambos_signos_y_los_dos_desfases_de_b310():
    for semilla in range(5):
        for signo, nombre in ((1, "desfase_unido_positivo"), (-1, "desfase_unido_negativo")):
            pasos = gen.CADENAS_REALES[nombre](random.Random(semilla))
            radio = pasos[0][1]["radius"]
            assert pasos[1][1]["z"] == pasos[0][1]["height"]
            assert pasos[-2][0] == "boolean_operation"
            assert pasos[-1][1]["distance"] == signo * 0.05 * radio
        for nombre, distancia in (("desfase_liso_leve", -1.24), ("desfase_liso_profundo", -6.13)):
            ped = {"pieza": nombre, "plan": []}
            pasos = list(trabajador.pasos_cadena(ped, random.Random(semilla))(None))
            assert all(p["exito"] for p in pasos)
            assert [p["tool"] for p in pasos] == ["create_cylinder", "offset_faces"]
            assert pasos[0]["args"]["radius"] == 15.5
            assert pasos[-1]["args"]["distance"] == distancia


def test_un_paso_real_se_juzga_aunque_no_cambie_la_receta():
    paso = {"tool": "section_view", "args": {}, "exito": True}
    with patch.object(trabajador, "llamar", return_value={"ok": True}), \
            patch.object(trabajador, "juzgar", return_value=(None, {}, {})) as juzgar:
        resultado = trabajador.correr(lambda _s: iter([paso]), ".")
        assert resultado["fallo"] is None
        assert juzgar.call_count == 1
        assert juzgar.call_args.args[-1] is True
        juzgar.reset_mock()
        trabajador.correr(lambda _s: iter([{**paso, "exito": False}]), ".")
        juzgar.assert_not_called()


def test_el_tema_pieza_real_reanuda_y_el_nombre_elige_solo_su_cadena():
    for foco, desde, esperadas in (("pieza_real", 2, list(gen.CADENAS_REALES)[2:]), ("dos_lados", 0, ["dos_lados"])):
        corrida = cazar.Corrida.__new__(cazar.Corrida)
        corrida.foco, corrida.pesado, corrida.plazo = foco, False, 40
        corrida.av = {"semilla": 1}
        corrida.fuente = Mock()
        corrida.fuente.pedir.return_value = {"avance": [], "fallo": None}
        corrida.cob = Mock()
        capa = {"reales": desde, "hechos": desde}
        corrida.capa_b(capa, lambda: True)
        assert [c.args[0]["pieza"] for c in corrida.fuente.pedir.call_args_list] == esperadas
        assert capa["hechos"] == desde + len(esperadas)


def test_numeros_y_fotos():
    bien = {"C": {"id": "op1.c1", "tipo": "solid", "v": 8.0, "a": 24.0, "min": [0, 0, 0], "max": [2, 2, 2]}}
    assert j.juez_numeros(bien) is None and j.distintas(bien, bien) is None
    assert j.juez_numeros({"C": {**bien["C"], "v": float("nan")}})
    assert j.juez_numeros({"C": {**bien["C"], "v": -1.0}})
    assert j.juez_numeros({"C": {**bien["C"], "max": [-1, 2, 2]}})
    assert j.distintas(bien, {"C": {**bien["C"], "v": 8.1}})


def test_el_empalme_nunca_saca_material_fuera_de_la_caja():
    a = {"C": {"id": "c", "tipo": "solid", "v": 8.0, "a": 1.0, "min": [0, 0, 0], "max": [2, 2, 2]}}
    b = {"C": {**a["C"], "max": [2, 3, 2]}}
    assert j.juez_esperado("fillet", {}, a, b)["kind"] == "caja_crece"
    assert j.juez_esperado("fillet", {}, b, a) is None


def test_mover_solo_vale_para_pasos_con_ids():
    assert j.movible({"edges": ["Cuerpo1/E3"], "radius": 2.0})
    assert not j.movible({"plane": "XY", "edges": ["Cuerpo1/E3"]})
    assert not j.movible({"feature": "op3"})


def test_las_medidas_salen_de_la_pieza():
    caras = [{"body": "c", "type": "plane", "normal": [0, 0, 1], "center": [0, 0, 5]},
             {"body": "c", "type": "plane", "normal": [0, 0, -1], "center": [0, 0, 3]}]
    m = gen.medidas([], [{"length": 9.0}], caras)
    assert m["pared"] == [2.0] and m["arista"] == [9.0, 9.0]

    class Ctx:
        medidas = {"pared": [2.0]}
    assert gen.medida(Ctx, random.Random(1), "10m") == 20.0
    assert gen.medida(Ctx, random.Random(1), "neg") == -2.0


def test_cada_pieza_semilla_se_arma(tmp_path):
    for nombre, pieza in gen.PIEZAS.items():
        s = api.Sesion()
        for tool, args in pieza(random.Random(0)):
            r = api.llamar(s, tool, args)
            assert r["ok"], (nombre, tool, r)


def test_mutar_cambia_los_bytes_y_se_repite():
    datos = bytes(range(256)) * 8
    assert trabajador.mutar(datos, random.Random(3)) == trabajador.mutar(datos, random.Random(3))
    assert any(trabajador.mutar(datos, random.Random(i)) != datos for i in range(5))


def test_repetir_confirma_tambien_los_pendientes_sin_confirmar(tmp_path, capsys):
    firma = "proceso|herramienta_de_prueba|colgado"            # una firma que no esté en el corpus
    receta = [{"tool": "create_box", "args": {"length": 80}}, {"tool": "herramienta_de_prueba", "args": {}}]
    (tmp_path / "pendientes.json").write_text(json.dumps(
        {firma: {"fallo": {}, "receta": receta, "veces": 1, "capa": "B", "ignorar": []}}), encoding="utf-8")
    fuente = Mock()
    fuente.pedir.return_value = {"fallo": {"juez": "proceso", "kind": "colgado", "op": "herramienta_de_prueba"}}
    with patch.object(cazar, "ESTADO", tmp_path), patch.object(cazar, "Fuente", return_value=fuente):
        assert cazar.repetir_firma(firma) == 1
        assert "Sigue fallando" in capsys.readouterr().out
        assert fuente.pedir.call_args.args[0]["pasos"] == receta
        assert cazar.repetir_firma("proceso|no_existe|colgado") == 2
