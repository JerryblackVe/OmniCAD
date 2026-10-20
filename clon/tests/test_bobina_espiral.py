# -*- coding: utf-8 -*-
"""Bobina de Fusion: espiral plana, giro local y compatibilidad de recetas."""
import copy

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import operacion_desde_dict


def _bobina(**datos):
    return sc.bobina((3, 5, 7), (0, 0, 1), diametro=20, revoluciones=2, paso=4,
                     tamano_seccion=2, eje_x=(1, 0, 0), **datos)


def _dimensiones(forma):
    assert geo.es_valida(forma)
    assert geo.volumen(forma) > 0
    minimo, maximo = geo.caja_envolvente(forma)
    return np.subtract(maximo, minimo)


@pytest.mark.parametrize("seccion", ["circular", "cuadrada", "triangular_externa", "triangular_interna"])
@pytest.mark.parametrize("horario", [False, True])
def test_espiral_plana_secciones_y_sentidos(seccion, horario):
    forma = _bobina(tipo="espiral", seccion=seccion, horario=horario)
    dimensiones = _dimensiones(forma)
    altura = {"circular": 2, "cuadrada": np.sqrt(2),
              "triangular_externa": np.sqrt(3), "triangular_interna": np.sqrt(3)}[seccion]
    assert dimensiones[2] == pytest.approx(altura, abs=1e-3)
    assert dimensiones[0] > 20 + 2 * 2 * 4 - 4


def test_espiral_crece_con_revoluciones_y_paso():
    def ancho(revoluciones, paso):
        forma = sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, revoluciones=revoluciones,
                          paso=paso, tamano_seccion=2, tipo="espiral", eje_x=(1, 0, 0))
        return _dimensiones(forma)[0]

    assert ancho(3, 4) - ancho(1, 4) == pytest.approx(2 * (3 - 1) * 4, abs=0.1)
    assert ancho(2, 6) > ancho(2, 4)


@pytest.mark.parametrize("tipo", ["rev_altura", "espiral"])
def test_giro_rota_caja_en_y_local_y_conserva_volumen(tipo):
    base = _bobina(tipo=tipo)
    girada = _bobina(tipo=tipo, girar=True)
    assert _dimensiones(girada) == pytest.approx(_dimensiones(base)[[2, 1, 0]], abs=1e-3)
    minimo, maximo = np.asarray(geo.caja_envolvente(base)) - (3, 5, 7)
    caja_esperada = np.array([[minimo[2], minimo[1], -maximo[0]],
                             [maximo[2], maximo[1], -minimo[0]]]) + (3, 5, 7)
    assert np.asarray(geo.caja_envolvente(girada)) == pytest.approx(caja_esperada, abs=1e-3)
    assert geo.volumen(girada) == pytest.approx(geo.volumen(base), rel=1e-6)


@pytest.mark.parametrize("tipo", ["rev_paso", "espiral"])
def test_giro_respeta_marco_local_fuera_de_xy(tipo):
    datos = dict(diametro=20, revoluciones=2, paso=4, tamano_seccion=2,
                 tipo=tipo, eje_x=(0, 1, 0))
    base = sc.bobina((3, 5, 7), (1, 0, 0), **datos)
    girada = sc.bobina((3, 5, 7), (1, 0, 0), girar=True, **datos)
    assert _dimensiones(girada) == pytest.approx(_dimensiones(base)[[1, 0, 2]], abs=1e-3)
    assert geo.volumen(girada) == pytest.approx(geo.volumen(base), rel=1e-6)


def test_receta_vieja_sin_girar_conserva_volumen_anterior():
    receta = {"tipo": "bobina", "id": "op1", "params": {
        "diametro": "20 mm", "tipo": "rev_altura", "revoluciones": "2",
        "altura": "12 mm", "tamano": "2 mm"}}
    op = operacion_desde_dict(receta)
    assert op.p["girar"] is False
    parametros = copy.deepcopy(op.p)
    doc = Documento()
    resultado = doc.agregar(op)
    assert resultado.estado == "ok", resultado.mensaje
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(394.7842576007823, rel=1e-6)
    assert op.p == parametros
    assert "girar" not in receta["params"]


@pytest.mark.parametrize("girar", [False, True])
def test_espiral_por_api(girar):
    sesion = api.Sesion()
    descripcion = api.llamar(sesion, "describe_operation", {"type": "bobina"})
    assert descripcion["ok"], descripcion
    campos = {p["name"]: p for p in descripcion["result"]["params"]}
    assert "espiral" in campos["tipo"]["choices"]
    assert campos["girar"]["default"] is False
    resultado = api.llamar(sesion, "run_operation", {"type": "bobina", "params": {
        "tipo": "espiral", "revoluciones": "2", "paso": "4 mm", "tamano": "2 mm",
        "girar": girar, "altura": "no se usa", "angulo": "no se usa"}})
    assert resultado["ok"], resultado
    assert resultado["result"]["status"] == "ok", resultado
    forma = sesion.doc.estado_final.cuerpos[resultado["result"]["new_bodies"][0]].forma
    assert _dimensiones(forma)[0 if girar else 2] == pytest.approx(2, abs=1e-3)


def test_dialogo_espiral_campos_y_giro():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Bobina

    doc = Documento()
    ctx = ContextoComando(doc)
    comando = Bobina()
    campos = {c.clave: c for c in comando.campos(ctx)}
    valores = {k: c.defecto for k, c in campos.items()}
    valores.update(tipo="espiral", girar=True, revoluciones="2", tamano="2 mm")
    for clave in ("revoluciones", "paso"):
        assert campos[clave].visible_si(valores)
    for clave in ("altura", "angulo"):
        assert not campos[clave].visible_si(valores)
    assert campos["girar"].defecto is False
    op = comando.construir(valores, ctx)
    resultado = doc.agregar(op)
    assert resultado.estado == "ok", resultado.mensaje
    forma = doc.estado_final.cuerpos[f"{op.id}.c1"].forma
    assert _dimensiones(forma)[0] == pytest.approx(2, abs=1e-3)
    editados = comando.desde_op(op, ContextoComando(doc, op=op))
    assert editados["tipo"] == "espiral" and editados["girar"] is True


@pytest.mark.parametrize("datos", [{"revoluciones": 0, "paso": 4}, {"revoluciones": 2, "paso": 0},
                                  {"revoluciones": 2, "paso": 1}, {"altura": 10, "paso": 4}])
def test_espiral_rechaza_datos_invalidos(datos):
    with pytest.raises(geo.ErrorGeometria):
        sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, tamano_seccion=2, tipo="espiral", **datos)
