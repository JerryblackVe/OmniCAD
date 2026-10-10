# -*- coding: utf-8 -*-
"""Programación visual sin ventana (`omnicad/grafo/`): árboles de datos y emparejado (GH1), motor con orden
topológico, ciclos y caché (GH2) y catálogo de nodos (GH3). Resultados exactos."""
import json
import math
import sys

import pytest

from omnicad.grafo import (Arbol, ErrorArbol, ErrorGrafo, Grafo, Ruta, catalogo, definicion, emparejar,
                           emparejar_ramas, motor_para)
from omnicad.grafo.arbol import aplicar_modificador
from omnicad.grafo.tipos import Curva, Plano, convertir
from omnicad.nucleo import geometria as geo


def arbol(d):
    return Arbol.desde_dict(d)


def evaluar(nodos, entradas=None, parametros=None):
    g = Grafo.desde_json({"nodos": nodos})
    return g, g.evaluar(entradas, parametros)


def ramas(r, ref):
    return r.arbol(ref).a_dict()


# ================================================================ GH1: rutas y árboles
def test_ruta_se_escribe_y_se_lee():
    assert Ruta.de("{0;1}") == Ruta(0, 1) == Ruta((0, 1)) == Ruta.de([0, 1])
    assert str(Ruta(2, 0, 5)) == "{2;0;5}" and Ruta(0).mas(3) == Ruta(0, 3)
    assert sorted([Ruta(1), Ruta(0, 1), Ruta(0), Ruta(0, 0)]) == [Ruta(0), Ruta(0, 0), Ruta(0, 1), Ruta(1)]
    for malo in ("0;1", "{a}", "{}", "{-1}"):
        with pytest.raises(ErrorArbol):
            Ruta.de(malo)
    for malo in ((), (-1,), (True,), (1.5,)):
        with pytest.raises(ErrorArbol):
            Ruta(*malo)


def test_arbol_basico_y_orden_de_ramas():
    a = Arbol()
    a.extender("{1}", ["c"])
    a.extender((0,), ["a", "b"])
    a.agregar(Ruta(0, 2), None)
    assert a.rutas() == [Ruta(0), Ruta(0, 2), Ruta(1)]
    assert a.items() == ["a", "b", None, "c"] and len(a) == 4 and a.cantidad_ramas == 3
    assert a.a_dict() == {"{0}": ["a", "b"], "{0;2}": [None], "{1}": ["c"]}
    assert Arbol.desde_dict(a.a_dict()) == a and a.primero() == "a"
    assert Arbol().vacio and Arbol.de_lista([]).vacio and Arbol.de_lista([]).cantidad_ramas == 1
    with pytest.raises(ErrorArbol):
        Arbol.desde_dict({"{0}": 3})


def test_aplanar_injertar_simplificar_invertir():
    a = arbol({"{0;0}": [1, 2], "{0;1}": [3], "{1;0}": [4, 5, 6]})
    assert a.aplanar().a_dict() == {"{0}": [1, 2, 3, 4, 5, 6]}
    assert a.injertar().a_dict() == {"{0;0;0}": [1], "{0;0;1}": [2], "{0;1;0}": [3], "{1;0;0}": [4], "{1;0;1}": [5],
                                     "{1;0;2}": [6]}
    assert arbol({"{0;0;0}": [1], "{0;0;1}": [2]}).simplificar().a_dict() == {"{0}": [1], "{1}": [2]}
    assert arbol({"{0;1;0}": [1], "{0;1;1}": [2], "{0;2;0}": [3]}).simplificar().a_dict() == \
        {"{1;0}": [1], "{1;1}": [2], "{2;0}": [3]}
    assert arbol({"{0;0;3}": [7]}).simplificar().a_dict() == {"{3}": [7]}           # una rama: conserva el último
    assert arbol({"{0}": [1], "{0;1}": [2]}).simplificar() == arbol({"{0}": [1], "{0;1}": [2]})
    # invertir (flip matrix): 2 filas de 3 → 3 filas de 2; con largos distintos, los huecos son nulos
    assert arbol({"{0}": [1, 2, 3], "{1}": [4, 5, 6]}).invertir().a_dict() == {"{0}": [1, 4], "{1}": [2, 5],
                                                                              "{2}": [3, 6]}
    assert arbol({"{0}": [1, 2], "{1}": [3]}).invertir().a_dict() == {"{0}": [1, 3], "{1}": [2, None]}
    assert Arbol().invertir() == Arbol() and Arbol().simplificar() == Arbol()
    # los modificadores devuelven árboles nuevos: el original no cambia
    assert a.a_dict() == {"{0;0}": [1, 2], "{0;1}": [3], "{1;0}": [4, 5, 6]}
    assert aplicar_modificador(a, None) is a and aplicar_modificador(a, "aplanar") == a.aplanar()
    with pytest.raises(ErrorArbol):
        aplicar_modificador(a, "rotar")


def test_fusionar_concatena_ramas_iguales():
    a = arbol({"{0}": [1], "{1}": [2]}).fusionar(arbol({"{0}": [3], "{2}": [4]}))
    assert a.a_dict() == {"{0}": [1, 3], "{1}": [2], "{2}": [4]}


def test_emparejado_de_listas():
    assert emparejar([[1, 2, 3], ["a"]], "larga") == [(1, "a"), (2, "a"), (3, "a")]
    assert emparejar([[1, 2, 3], ["a", "b"]], "larga") == [(1, "a"), (2, "b"), (3, "b")]
    assert emparejar([[1, 2, 3], ["a", "b"]], "corta") == [(1, "a"), (2, "b")]
    assert emparejar([[1, 2], ["a", "b", "c"]], "cruzada") == [(1, "a"), (1, "b"), (1, "c"), (2, "a"), (2, "b"),
                                                              (2, "c")]
    assert emparejar([[1, 2], []], "larga") == [] and emparejar([], "corta") == [()]
    with pytest.raises(ErrorArbol):
        emparejar([[1]], "media")


def test_emparejado_de_ramas_manda_el_arbol_con_mas_ramas():
    a = arbol({"{0}": [1], "{1}": [2], "{2}": [3]})
    b = arbol({"{5}": [10, 20]})
    grupos = emparejar_ramas([b, a])
    assert [(str(r), x) for r, x in grupos] == [("{0}", [[10, 20], [1]]), ("{1}", [[10, 20], [2]]),
                                                 ("{2}", [[10, 20], [3]])]
    assert emparejar_ramas([a, Arbol()]) == []


# ================================================================ GH2: motor
def test_emparejado_dentro_de_un_nodo():
    _g, r = evaluar([{"id": "s", "tipo": "sumar", "entradas": {"a": [1, 2, 3], "b": 10}}])
    assert ramas(r, "s") == {"{0}": [11.0, 12.0, 13.0]}
    _g, r = evaluar([{"id": "s", "tipo": "sumar", "emparejado": "corta", "entradas": {"a": [1, 2, 3], "b": [10, 20]}}])
    assert ramas(r, "s") == {"{0}": [11.0, 22.0]}
    _g, r = evaluar([{"id": "s", "tipo": "sumar", "emparejado": "cruzada", "entradas": {"a": [1, 2], "b": [10, 20]}}])
    assert ramas(r, "s") == {"{0}": [11.0, 21.0, 12.0, 22.0]}


def test_arboles_en_un_nodo_y_salida_lista_en_subramas():
    _g, r = evaluar([{"id": "s", "tipo": "multiplicar",
                      "entradas": {"a": {"arbol": {"{0}": [1, 2], "{1}": [3]}}, "b": [10, 100]}}])
    assert ramas(r, "s") == {"{0}": [10.0, 200.0], "{1}": [30.0, 300.0]}    # la rama {1} repite y empareja con b
    # «serie» corre dos veces en la rama {0}: cada lista va a su sub-rama {0;vuelta}; con una sola vuelta, a {0}
    _g, r = evaluar([{"id": "n", "tipo": "serie", "entradas": {"cantidad": [2, 3]}},
                     {"id": "uno", "tipo": "serie", "entradas": {"cantidad": 2, "paso": 5}}])
    assert ramas(r, "n") == {"{0;0}": [0.0, 1.0], "{0;1}": [0.0, 1.0, 2.0]}
    assert ramas(r, "uno") == {"{0}": [0.0, 5.0]}


def test_modificador_en_la_entrada_y_varios_cables_se_fusionan():
    _g, r = evaluar([{"id": "a", "tipo": "serie", "entradas": {"cantidad": 3}},
                     {"id": "b", "tipo": "serie", "entradas": {"inicio": 10, "cantidad": 2}},
                     {"id": "t", "tipo": "total", "entradas": {"numeros": {"de": ["a", "b.numeros"]}}},
                     {"id": "i", "tipo": "total", "entradas": {"numeros": {"de": "a", "modificador": "injertar"}}}])
    assert ramas(r, "t") == {"{0}": [24.0]}                  # 0 + 1 + 2 + 10 + 11: una lista con las dos
    assert ramas(r, "i") == {"{0;0}": [0.0], "{0;1}": [1.0], "{0;2}": [2.0]}      # injertada: un total por ítem


def test_nulos_y_errores_por_nodo():
    _g, r = evaluar([
        {"id": "d", "tipo": "dividir", "entradas": {"a": [1, 2, 3], "b": [1, 0, 3]}},
        {"id": "mas", "tipo": "sumar", "entradas": {"a": {"de": "d"}, "b": 1}},
        {"id": "it", "tipo": "item", "entradas": {"lista": [5, 6], "indice": 7}},
        {"id": "falta", "tipo": "caja_envolvente", "entradas": {}},
    ])
    d, mas, it, falta = (r.nodos[x] for x in ("d", "mas", "it", "falta"))
    assert d.estado == "error" and d.mensajes == ["División por cero."]
    assert ramas(r, "d") == {"{0}": [1.0, None, 1.0]}                      # las otras vueltas siguen
    assert mas.estado == "aviso" and ramas(r, "mas") == {"{0}": [2.0, None, 2.0]}
    assert "nula" in mas.mensajes[0]
    assert it.estado == "aviso" and ramas(r, "it") == {"{0}": [None]} and "fuera de la lista" in it.mensajes[0]
    assert falta.estado == "aviso" and "«cuerpo»" in falta.mensajes[0] and r.arbol("falta.minimo").vacio
    assert r.errores == [("d", "División por cero.")]


def test_producto_cruzado_gigante_se_frena_antes_de_armarlo():
    _g, r = evaluar([{"id": "a", "tipo": "serie", "entradas": {"cantidad": 1000}},
                     {"id": "s", "tipo": "sumar", "emparejado": "cruzada", "entradas": {"a": {"de": "a"}, "b": {"de": "a"}}}])
    assert r.nodos["s"].estado == "error" and "1000000 vueltas" in r.nodos["s"].mensajes[0] and r.arbol("s").vacio


def test_literal_invalido_es_error_del_nodo_con_el_puerto():
    _g, r = evaluar([{"id": "s", "tipo": "sumar", "entradas": {"a": "3 +", "b": "no_existe * 2"}}])
    assert r.nodos["s"].estado == "error" and r.nodos["s"].mensajes[0].startswith("Entrada «a»")
    _g, r = evaluar([{"id": "c", "tipo": "caja", "entradas": {"ancho": "10 deg"}}])
    assert r.nodos["c"].estado == "error" and "longitud" in r.nodos["c"].mensajes[0]


def test_ciclo_detectado_con_su_recorrido():
    with pytest.raises(ErrorGrafo) as e:
        Grafo.desde_json({"nodos": [
            {"id": "x", "tipo": "numero"},
            {"id": "a", "tipo": "sumar", "entradas": {"a": {"de": "x"}, "b": {"de": "c"}}},
            {"id": "b", "tipo": "sumar", "entradas": {"a": {"de": "a"}}},
            {"id": "c", "tipo": "sumar", "entradas": {"a": {"de": "b"}}},
            {"id": "fin", "tipo": "salida", "entradas": {"valor": {"de": "c"}}}]})
    assert str(e.value) == "El grafo tiene un ciclo: a → b → c → a."
    assert any("propia salida" in p for p in e.value.pistas)
    with pytest.raises(ErrorGrafo, match="ciclo: a → a"):
        Grafo.desde_json({"nodos": [{"id": "a", "tipo": "sumar", "entradas": {"a": {"de": "a"}}}]})


@pytest.mark.parametrize("datos, texto", [
    ({"nodos": [{"id": "a", "tipo": "cajaa"}]}, "Tipo de nodo desconocido: «cajaa»"),
    ({"nodos": [{"id": "a", "tipo": "caja", "entradas": {"anchura": 3}}]}, "no tiene la entrada «anchura»"),
    ({"nodos": [{"id": "a", "tipo": "caja", "entradas": {"ancho": {"de": "b"}}}]}, "viene de «b», que no existe"),
    ({"nodos": [{"id": "n", "tipo": "numero"}, {"id": "a", "tipo": "caja", "entradas": {"ancho": {"de": "n.x"}}}]},
     "no tiene la salida «x»"),
    ({"nodos": [{"id": "a", "tipo": "numero"}, {"id": "a", "tipo": "numero"}]}, "dos nodos con el id «a»"),
    ({"nodos": [{"id": "1a", "tipo": "numero"}]}, "Id de nodo inválido"),
    ({"nodos": [{"id": "a", "tipo": "numero", "entradas": {"valor": {"de": "x", "valor": 1}}}]}, "UNA de estas"),
    ({"nodos": [{"id": "a", "tipo": "numero", "entradas": {"valor": {"valor": 1, "modificador": "x"}}}]},
     "Modificador desconocido"),
    ({"nodos": [{"id": "a", "tipo": "numero", "emparejado": "media"}]}, "Emparejado desconocido"),
    ({"nodos": [{"id": "a", "tipo": "numero", "color": 1}]}, "Claves desconocidas en el nodo"),
    ({"nodos": "a"}, "Falta la lista «nodos»"),
    ({"nodos": [], "formato": "otro"}, "Formato de grafo desconocido"),
    ({"nodos": [], "version": 99}, "Versión de grafo no soportada"),
    ("{no es json", "no es JSON válido"),
])
def test_grafos_mal_formados_dan_errores_claros(datos, texto):
    with pytest.raises(ErrorGrafo) as e:
        Grafo.desde_json(datos)
    assert texto in str(e.value)


def test_tipo_desconocido_sugiere_el_parecido():
    with pytest.raises(ErrorGrafo) as e:
        Grafo.desde_json({"nodos": [{"id": "a", "tipo": "cilindr"}]})
    assert any("cilindro" in p for p in e.value.pistas)


def test_cache_recalcula_solo_lo_que_cuelga_de_la_entrada_cambiada():
    g = Grafo.desde_json({"nodos": [
        {"id": "lado", "tipo": "numero", "entradas": {"valor": 10}},
        {"id": "alto", "tipo": "numero", "nombre": "altura", "entradas": {"valor": 10}},
        {"id": "grilla", "tipo": "puntos_grilla", "entradas": {"paso_x": {"de": "lado"}, "paso_y": {"de": "lado"}}},
        {"id": "cajas", "tipo": "caja", "entradas": {"centro": {"de": "grilla"}, "ancho": {"de": "lado"},
                                                     "largo": {"de": "lado"}, "alto": {"de": "alto"}}},
        {"id": "union", "tipo": "unir", "entradas": {"cuerpos": {"de": "cajas"}}},
        {"id": "vol", "tipo": "volumen", "entradas": {"cuerpo": {"de": "union"}}},
        {"id": "otro", "tipo": "sumar", "entradas": {"a": {"de": "lado"}, "b": 1}},
        {"id": "v", "tipo": "salida", "nombre": "volumen", "entradas": {"valor": {"de": "vol"}}}]})
    r = g.evaluar()
    assert r.salidas["volumen"].items() == [pytest.approx(9000.0)]
    assert len(r.ejecutados) == 8 and set(g._motor.ejecuciones.values()) == {1}
    r = g.evaluar()                                                   # nada cambió: todo de la caché
    assert r.ejecutados == [] and r.salidas["volumen"].items() == [pytest.approx(9000.0)]
    r = g.evaluar({"altura": 20})                                     # solo cajas → unir → volumen → salida
    assert r.ejecutados == ["alto", "cajas", "union", "vol", "v"]
    assert r.salidas["volumen"].items() == [pytest.approx(18000.0)]
    assert g._motor.ejecuciones == {"lado": 1, "alto": 2, "grilla": 1, "cajas": 2, "union": 2, "vol": 2, "otro": 1,
                                    "v": 2}
    assert not r.nodos["grilla"].ejecutado and r.nodos["grilla"].duracion > 0     # el tiempo de su último cálculo
    g.poner_entrada("otro", "b", 2)                                   # cambiar un literal también invalida solo eso
    r = g.evaluar({"altura": 20})
    assert r.ejecutados == ["otro"] and r.arbol("otro").items() == [12.0]
    r = g.evaluar()                                                   # volver al valor de antes: recalcula de nuevo
    assert r.ejecutados == ["alto", "cajas", "union", "vol", "v"]


def test_parametros_del_documento_en_literales_y_en_el_nodo_parametro():
    g = Grafo.desde_json({"nodos": [
        {"id": "p", "tipo": "parametro", "entradas": {"nombre": "ancho"}},
        {"id": "e", "tipo": "numero", "entradas": {"valor": "ancho / 2 + 1 mm"}},
        {"id": "x", "tipo": "expresion", "entradas": {"expresion": "x * alto", "x": 3}},
        {"id": "pt", "tipo": "punto", "entradas": {"valor": ["ancho", 0, "alto"]}}]})
    assert sorted(g.expresiones()) == sorted(["ancho", "ancho / 2 + 1 mm", "x * alto", "ancho", "alto"])
    r = g.evaluar(parametros={"ancho": 40.0, "alto": 5.0})
    assert [r.arbol(n).items() for n in ("p", "e", "x", "pt")] == [[40.0], [21.0], [15.0], [(40.0, 0.0, 5.0)]]
    r = g.evaluar(parametros={"ancho": 40.0, "alto": 6.0})          # cambia «alto»: «p» y «e» salen de la caché
    assert r.ejecutados == ["x", "pt"] and r.arbol("x").items() == [18.0]
    r = g.evaluar(parametros={"alto": 6.0})
    assert r.nodos["p"].estado == "error" and "«ancho»" in r.nodos["p"].mensajes[0]


def test_entradas_por_nombre_id_y_nodo_punto_entrada():
    g = Grafo.desde_json({"nodos": [
        {"id": "a", "tipo": "deslizador", "nombre": "lado", "entradas": {"valor": 3, "maximo": 5}},
        {"id": "b", "tipo": "numero"},
        {"id": "s", "tipo": "sumar", "entradas": {"a": {"de": "a"}, "b": {"de": "b"}}}]})
    assert g.evaluar({"lado": 4, "b": 1, "s.b": 2}).arbol("s").items() == [6.0]       # s.b reemplaza el cable
    r = g.evaluar({"lado": 9})
    assert r.arbol("a").items() == [5.0] and r.nodos["a"].estado == "aviso"           # el deslizador recorta
    with pytest.raises(ErrorGrafo, match="no tiene la entrada «ladoo»") as e:
        g.evaluar({"ladoo": 1})
    assert any("lado" in p for p in e.value.pistas)
    with pytest.raises(ErrorGrafo, match="no es un nodo de entrada"):
        g.evaluar({"s": 1})
    with pytest.raises(ErrorGrafo, match="no tiene la entrada «c»"):
        g.evaluar({"s.c": 1})


def test_json_ida_y_vuelta():
    datos = {"formato": "omnicad.grafo", "version": 1, "nombre": "Prueba",
             "nodos": [{"id": "n", "tipo": "numero", "nombre": "lado", "entradas": {"valor": "ancho"},
                        "posicion": [10, 20]},
                       {"id": "c", "tipo": "caja", "entradas": {"ancho": {"de": "n"}}, "emparejado": "cruzada"}]}
    g = Grafo.desde_json(datos)
    assert g.a_json() == datos and Grafo.desde_json(json.dumps(datos)).a_json() == datos
    g2 = Grafo()
    g2.agregar("numero", "n", {"valor": 4})
    g2.agregar("caja", "c")
    g2.conectar("n", "c.ancho")
    g2.conectar("n.valor", "c.largo")
    assert g2.a_json()["nodos"][1]["entradas"] == {"ancho": {"de": ["n"]}, "largo": {"de": ["n.valor"]}}
    assert geo.caja_envolvente(g2.evaluar().arbol("c").primero())[1] == pytest.approx((2, 2, 10))


def test_grilla_de_3x3_cajas_unidas_volumen_exacto():
    """La prueba de fuego del pedido: 9 cajas de 10 × 10 × 4 en una grilla de paso 10, unidas → un solo sólido de
    30 × 30 × 4 = 3600 mm³. Con paso 15 no se tocan: 9 piezas del mismo volumen total."""
    nodos = [
        {"id": "lado", "tipo": "numero", "entradas": {"valor": 10}},
        {"id": "paso", "tipo": "numero", "nombre": "paso", "entradas": {"valor": 10}},
        {"id": "grilla", "tipo": "puntos_grilla", "entradas": {"paso_x": {"de": "paso"}, "paso_y": {"de": "paso"}}},
        {"id": "cajas", "tipo": "caja", "entradas": {"centro": {"de": "grilla.puntos"}, "ancho": {"de": "lado"},
                                                     "largo": {"de": "lado"}, "alto": 4}},
        {"id": "union", "tipo": "unir", "entradas": {"cuerpos": {"de": "cajas"}}},
        {"id": "piezas", "tipo": "separar", "entradas": {"cuerpo": {"de": "union"}}},
        {"id": "pieza", "tipo": "salida", "entradas": {"valor": {"de": "union"}}}]
    g, r = evaluar(nodos)
    assert len(r.arbol("grilla").items()) == 9 and len(r.arbol("cajas").items()) == 9
    (nombre, forma), = r.cuerpos()
    assert nombre == "pieza" and geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(3600.0, rel=1e-9)
    assert geo.caja_envolvente(forma) == (pytest.approx((-5, -5, 0)), pytest.approx((25, 25, 4)))
    assert len(geo.solidos(forma)) == 1 and len(r.arbol("piezas").items()) == 1
    assert len(geo.caras(forma)) == 6                               # booleana limpia: caras coplanares fusionadas
    r = g.evaluar({"paso": 15})
    forma = r.cuerpos()[0][1]
    assert geo.volumen(forma) == pytest.approx(3600.0, rel=1e-9) and len(r.arbol("piezas").items()) == 9


def test_motor_para_comparte_la_cache_del_mismo_grafo():
    datos = {"nodos": [{"id": "a", "tipo": "serie", "entradas": {"cantidad": 4}},
                       {"id": "t", "tipo": "total", "entradas": {"numeros": {"de": "a"}}}]}
    m = motor_para(datos)
    assert motor_para(json.loads(json.dumps(datos))) is m
    assert m.evaluar().arbol("t").items() == [6.0]
    assert m.evaluar({"a.cantidad": 5}).ejecutados == ["a", "t"] and m.evaluar().ejecutados == ["a", "t"]


def test_importar_el_grafo_no_carga_qt_ni_occ():
    import subprocess
    from pathlib import Path
    codigo = ("import sys; import omnicad.grafo as g; g.Arbol(); "
              "assert 'PySide6' not in sys.modules and 'OCP' not in sys.modules, sorted(sys.modules); print('ok')")
    r = subprocess.run([sys.executable, "-c", codigo], cwd=Path(__file__).resolve().parent.parent,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr


# ================================================================ GH3: catálogo de nodos
def test_catalogo_por_categoria_y_bien_descripto():
    cat = catalogo()
    assert len(cat) >= 60
    por = {}
    for d in cat.values():
        por.setdefault(d.categoria, []).append(d.tipo)
        assert d.titulo and d.descripcion.endswith((".", ")")) and d.salidas
        json.dumps(d.a_json())
    assert set(por) == {"entrada", "matematica", "listas", "arboles", "vectores", "curvas", "solidos", "salida"}
    for tipo in ("deslizador", "numero", "booleano", "texto", "punto", "rango", "serie", "expresion", "largo", "item",
                 "sublista", "invertir_lista", "ordenar", "repetir", "construir_punto", "descomponer",
                 "sumar_vectores", "escalar_vector", "distancia", "caja", "cilindro", "esfera", "mover", "rotar",
                 "unir", "cortar", "volumen", "area", "caja_envolvente", "puntos_grilla", "puntos_circulo", "salida",
                 "aplanar", "injertar", "simplificar", "invertir_matriz"):
        assert tipo in cat, tipo
    assert definicion("no_existe") is None


def _alimentar(d):
    """Entradas para correr el nodo solo: cuerpos y curvas por cable; listas y textos obligatorios, literales."""
    entradas = {}
    for p in d.entradas:
        if p.tipo == "cuerpo":
            entradas[p.nombre] = {"de": "esfera_base" if p.nombre in ("herramientas", "b") else "caja_base"}
        elif p.tipo == "curva":
            entradas[p.nombre] = {"de": "circulo_base"}
        elif p.obligatorio and p.tipo == "texto":
            entradas[p.nombre] = "ancho"
        elif p.obligatorio:
            entradas[p.nombre] = [3, 1, 2]
    return entradas


@pytest.mark.parametrize("tipo", sorted(catalogo()))
def test_cada_nodo_corre_con_sus_valores_por_defecto(tipo):
    d = definicion(tipo)
    _g, r = evaluar([{"id": "caja_base", "tipo": "caja"},
                     {"id": "esfera_base", "tipo": "esfera"},
                     {"id": "circulo_base", "tipo": "circulo"},
                     {"id": "nodo", "tipo": tipo, "entradas": _alimentar(d)}], parametros={"ancho": 10.0})
    info = r.nodos["nodo"]
    assert info.estado == "ok", info.mensajes
    for s in d.salidas:
        assert not info.salidas[s.nombre].vacio, s.nombre
        for x in info.salidas[s.nombre].items():
            if s.tipo == "cuerpo":
                assert geo.es_valida(x) and not geo.esta_vacia(x)
            elif s.tipo in ("numero", "entero"):
                assert isinstance(x, (int, float)) and math.isfinite(x)


def test_nodos_de_numeros_y_listas():
    _g, r = evaluar([
        {"id": "rango", "tipo": "rango", "entradas": {"inicio": 0, "fin": 1, "pasos": 4}},
        {"id": "serie", "tipo": "serie", "entradas": {"inicio": 2, "paso": 3, "cantidad": 4}},
        {"id": "orden", "tipo": "ordenar", "entradas": {"lista": [3, 1, 2], "claves": [30, 10, 20]}},
        {"id": "sub", "tipo": "sublista", "entradas": {"lista": [0, 1, 2, 3, 4], "inicio": 1, "fin": -1}},
        {"id": "rep", "tipo": "repetir", "entradas": {"lista": ["a", "b"], "veces": 3}},
        {"id": "fil", "tipo": "filtrar", "entradas": {"lista": [1, 2, 3, 4, 5]}},
        {"id": "des", "tipo": "desplazar", "entradas": {"lista": [1, 2, 3], "cantidad": 1}},
        {"id": "item", "tipo": "item", "entradas": {"lista": ["a", "b", "c"], "indice": -1}},
        {"id": "env", "tipo": "item", "entradas": {"lista": ["a", "b", "c"], "indice": 4, "envolver": True}},
        {"id": "largo", "tipo": "largo", "entradas": {"lista": [1, None, 3]}},
        {"id": "inv", "tipo": "invertir_lista", "entradas": {"lista": [1, 2, 3]}},
        {"id": "pot", "tipo": "potencia", "entradas": {"a": 2, "b": 10}},
        {"id": "res", "tipo": "resto", "entradas": {"a": -7, "b": 3}},
        {"id": "cmp", "tipo": "comparar", "entradas": {"a": [1, 2, 3], "b": 2, "operador": ">="}},
        {"id": "sen", "tipo": "seno", "entradas": {"angulo": 30}},
        {"id": "exp", "tipo": "expresion", "entradas": {"expresion": "sqrt(x**2 + y**2)", "x": 3, "y": 4}},
        {"id": "azar", "tipo": "aleatorio", "entradas": {"cantidad": 3, "semilla": 7}},
        {"id": "azar2", "tipo": "aleatorio", "entradas": {"cantidad": 3, "semilla": 7}},
    ])
    assert r.arbol("rango").items() == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert r.arbol("serie").items() == [2.0, 5.0, 8.0, 11.0]
    assert r.arbol("orden.lista").items() == [1, 2, 3] and r.arbol("orden.indices").items() == [1, 2, 0]
    assert r.arbol("sub").items() == [1, 2, 3]
    assert r.arbol("rep").items() == ["a", "b"] * 3
    assert r.arbol("fil").items() == [1, 3, 5]                      # patrón por defecto: sí, no
    assert r.arbol("des").items() == [2, 3, 1]
    assert r.arbol("item").items() == ["c"] and r.arbol("env").items() == ["b"]
    assert r.arbol("largo").items() == [3] and r.arbol("inv").items() == [3, 2, 1]
    assert r.arbol("pot").items() == [1024.0] and r.arbol("res").items() == [2.0]
    assert r.arbol("cmp").items() == [False, True, True]
    assert r.arbol("sen").items() == [pytest.approx(0.5)] and r.arbol("exp").items() == [5.0]
    assert r.arbol("azar").items() == r.arbol("azar2").items() and len(set(r.arbol("azar").items())) == 3


def test_nodos_de_vectores_y_planos():
    _g, r = evaluar([
        {"id": "p", "tipo": "construir_punto", "entradas": {"x": 1, "y": 2, "z": "3 cm"}},
        {"id": "d", "tipo": "descomponer", "entradas": {"punto": {"de": "p"}}},
        {"id": "v", "tipo": "vector_2p", "entradas": {"a": [1, 1, 1], "b": [4, 5, 1]}},
        {"id": "sv", "tipo": "sumar_vectores", "entradas": {"a": [1, 2, 3], "b": [1, 1, 1]}},
        {"id": "ev", "tipo": "escalar_vector", "entradas": {"vector": [1, 2, 3], "factor": 2}},
        {"id": "dist", "tipo": "distancia", "entradas": {"a": [0, 0, 0], "b": [3, 4, 12]}},
        {"id": "u", "tipo": "unitario", "entradas": {"vector": [0, 3, 4]}},
        {"id": "cruz", "tipo": "producto_vectorial", "entradas": {"a": [1, 0, 0], "b": [0, 1, 0]}},
        {"id": "esc", "tipo": "producto_escalar", "entradas": {"a": [1, 2, 3], "b": [4, 5, 6]}},
        {"id": "circ", "tipo": "puntos_circulo", "entradas": {"radio": 10, "cantidad": 4}},
        {"id": "pl", "tipo": "plano_origen", "entradas": {"nombre": "XZ", "origen": [0, 0, 5]}},
        {"id": "gr", "tipo": "puntos_grilla", "entradas": {"plano": {"de": "pl"}, "cantidad_x": 2, "cantidad_y": 2,
                                                           "paso_x": 10, "paso_y": 20}},
        {"id": "nulo", "tipo": "unitario", "entradas": {"vector": [0, 0, 0]}},
    ])
    assert r.arbol("p").items() == [(1.0, 2.0, 30.0)]
    assert [r.arbol(f"d.{c}").items() for c in "xyz"] == [[1.0], [2.0], [30.0]]
    assert r.arbol("v.vector").items() == [(3.0, 4.0, 0.0)] and r.arbol("v.largo").items() == [5.0]
    assert r.arbol("sv").items() == [(2.0, 3.0, 4.0)] and r.arbol("ev").items() == [(2.0, 4.0, 6.0)]
    assert r.arbol("dist").items() == [13.0] and r.arbol("u").items() == [(0.0, 0.6, 0.8)]
    assert r.arbol("cruz").items() == [(0.0, 0.0, 1.0)] and r.arbol("esc").items() == [32.0]
    puntos = r.arbol("circ").items()
    assert [tuple(round(c, 9) + 0.0 for c in q) for q in puntos] == [(10, 0, 0), (0, 10, 0), (-10, 0, 0), (0, -10, 0)]
    plano = r.arbol("pl").items()[0]
    assert isinstance(plano, Plano) and plano.z == (0.0, -1.0, 0.0) and plano.y == (0.0, 0.0, 1.0)
    assert r.arbol("gr").items() == [(0.0, 0.0, 5.0), (10.0, 0.0, 5.0), (0.0, 0.0, 25.0), (10.0, 0.0, 25.0)]
    assert r.nodos["nulo"].estado == "error" and "nulo" in r.nodos["nulo"].mensajes[0]


def test_nodos_de_curvas_y_solidos():
    _g, r = evaluar([
        {"id": "circ", "tipo": "circulo", "entradas": {"radio": 5}},
        {"id": "ext", "tipo": "extruir", "entradas": {"curva": {"de": "circ"}, "distancia": 10}},
        {"id": "rect", "tipo": "rectangulo", "entradas": {"plano": "XZ", "ancho": 20, "largo": 10}},
        {"id": "ext2", "tipo": "extruir", "entradas": {"curva": {"de": "rect"}, "distancia": 3}},
        {"id": "lin", "tipo": "linea", "entradas": {"a": [0, 0, 0], "b": [3, 4, 0]}},
        {"id": "largos", "tipo": "largo_curva", "entradas": {"curva": {"de": ["lin", "circ", "rect"]}}},
        {"id": "abierta", "tipo": "extruir", "entradas": {"curva": {"de": "lin"}}},
        {"id": "caja", "tipo": "caja", "entradas": {"ancho": 20, "largo": 10, "alto": 5}},
        {"id": "mov", "tipo": "mover", "entradas": {"cuerpo": {"de": "caja"}, "vector": [1, 2, 3]}},
        {"id": "rot", "tipo": "rotar", "entradas": {"cuerpo": {"de": "caja"}, "angulo": 90}},
        {"id": "esc", "tipo": "escalar", "entradas": {"cuerpo": {"de": "caja"}, "factor": 2}},
        {"id": "sim", "tipo": "simetria", "entradas": {"cuerpo": {"de": "mov"}, "plano": "YZ"}},
        {"id": "agujero", "tipo": "cilindro", "entradas": {"radio": 2, "alto": 5}},
        {"id": "corte", "tipo": "cortar", "entradas": {"cuerpo": {"de": "caja"}, "herramientas": {"de": "agujero"}}},
        {"id": "inter", "tipo": "intersecar", "entradas": {"a": {"de": "caja"}, "b": {"de": "mov"}}},
        {"id": "vol", "tipo": "volumen", "entradas": {"cuerpo": {"de": ["ext", "ext2", "caja", "esc", "corte", "inter"]}}},
        {"id": "area", "tipo": "area", "entradas": {"cuerpo": {"de": "caja"}}},
        {"id": "cm", "tipo": "centro_masa", "entradas": {"cuerpo": {"de": "mov"}}},
        {"id": "bb", "tipo": "caja_envolvente", "entradas": {"cuerpo": {"de": ["rot", "sim"]}}},
    ])
    assert all(r.nodos[n].estado == "ok" for n in r.orden if n != "abierta"), r.errores
    assert isinstance(r.arbol("circ").primero(), Curva) and r.arbol("circ").primero().cerrada
    largos = r.arbol("largos").items()
    assert largos == [pytest.approx(5.0), pytest.approx(10 * math.pi), pytest.approx(60.0)]
    assert r.nodos["abierta"].estado == "error" and "cerrada" in r.nodos["abierta"].mensajes[0]
    assert r.arbol("vol").items() == [pytest.approx(250 * math.pi), pytest.approx(600.0), pytest.approx(1000.0),
                                      pytest.approx(8000.0), pytest.approx(1000 - 20 * math.pi),
                                      pytest.approx(19 * 8 * 2)]
    assert r.arbol("area").items() == [pytest.approx(2 * (200 + 100 + 50))]
    assert r.arbol("cm").items() == [pytest.approx((1.0, 2.0, 5.5))]
    rot_min, sim_min = r.arbol("bb.minimo").items()
    rot_max, sim_max = r.arbol("bb.maximo").items()
    assert rot_min == pytest.approx((-5, -10, 0)) and rot_max == pytest.approx((5, 10, 5))
    assert sim_min == pytest.approx((-11, -3, 3)) and sim_max == pytest.approx((9, 7, 8))
    ext2 = r.arbol("ext2").primero()
    assert geo.caja_envolvente(ext2) == (pytest.approx((-10, -3, -5)), pytest.approx((10, 0, 5)))   # XZ: normal −Y


def test_docs_grafo_md_lista_todos_los_nodos_y_su_ejemplo_corre():
    import re
    from pathlib import Path
    texto = (Path(__file__).resolve().parents[2] / "docs" / "grafo.md").read_text(encoding="utf-8")
    documentados = set(re.findall(r"^\| `([a-z_0-9]+)` \|", texto, flags=re.M))
    assert documentados == set(catalogo()), (set(catalogo()) - documentados, documentados - set(catalogo()))
    ejemplo = json.loads(re.search(r"```json\n(.*?)```", texto, flags=re.S).group(1))
    (nombre, forma), = Grafo.desde_json(ejemplo).evaluar().cuerpos()
    assert nombre == "pieza" and geo.volumen(forma) == pytest.approx(9 * 10 * 10 * 10)


def test_conversiones_de_tipo():
    assert convertir("2 * 3", "numero") == 6.0 and convertir(2.6, "entero") == 3
    assert convertir("sí", "booleano") is True and convertir(0, "booleano") is False
    assert convertir(3.0, "texto") == "3" and convertir([1, "2 cm"], "punto") == (1.0, 20.0, 0.0)
    assert convertir("YZ", "plano").z == (1.0, 0.0, 0.0)
    assert convertir({"origen": [0, 0, 1], "normal": [0, 0, 2]}, "plano") == Plano.de_nombre("XY", (0, 0, 1))
    from omnicad.grafo import ErrorTipo
    for valor, tipo in (("hola", "numero"), ([1, 2, 3, 4], "punto"), ("XW", "plano"), (3, "curva"), ("x", "cuerpo"),
                        ("quizás", "booleano")):
        with pytest.raises(ErrorTipo):
            convertir(valor, tipo)
