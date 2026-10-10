# -*- coding: utf-8 -*-
"""
Grafo de nodos y su motor de evaluación (GH2 de `docs/brechas_grasshopper.md`).

El grafo es flujo de datos puro: cada nodo toma árboles de datos por sus entradas, corre su función y entrega árboles
por sus salidas. No toca el documento; «Hornear» (`timeline/ops_grafo.py`) lo pasa al timeline.

Formato JSON (lo que guardan `a_json` / `desde_json`, y lo que va dentro del paso «Grafo» del `.omnicad`):

    {"formato": "omnicad.grafo", "version": 1,
     "nodos": [
       {"id": "lado", "tipo": "deslizador", "nombre": "lado", "entradas": {"valor": 10, "minimo": 1, "maximo": 50}},
       {"id": "grilla", "tipo": "puntos_grilla", "entradas": {"paso_x": {"de": "lado"}, "paso_y": {"de": "lado"}}},
       {"id": "cajas", "tipo": "caja", "entradas": {"centro": {"de": "grilla.puntos"}, "ancho": {"de": "lado"}}},
       {"id": "pieza", "tipo": "unir", "entradas": {"cuerpos": {"de": "cajas"}}},
       {"id": "resultado", "tipo": "salida", "entradas": {"valor": {"de": "pieza"}}}]}

  - `id`: identificador (letras, dígitos y «_»); `tipo`: un tipo del catálogo (`nodos.catalogo()`); `nombre`: opcional,
    el nombre público de una entrada o salida; `emparejado`: "larga" (por defecto), "corta" o "cruzada";
    `posicion`: [x, y] en el lienzo (se guarda y no se usa al evaluar).
  - Cada entrada es un literal (número, texto o expresión con parámetros del documento, booleano, lista, punto
    [x, y, z], plano "XY"…), un cable {"de": "nodo"} / {"de": "nodo.salida"} / {"de": ["a", "b.x"]} (varios cables se
    fusionan), un árbol literal {"arbol": {"{0}": [...], "{1}": [...]}} o {"valor": literal}. Con "modificador":
    "aplanar" | "injertar" | "simplificar" | "invertir" se transforma el árbol antes de usarlo.

Evaluación: orden topológico (los ciclos son un ErrorGrafo con el ciclo nombrado), caché por nodo con una huella de sus
entradas (literales ya evaluados, huellas de los nodos de los que cuelga y, si el nodo lee parámetros del documento,
sus valores): al cambiar una entrada solo se recalcula lo que está aguas abajo. Cada nodo informa estado ("ok",
"aviso", "error"), mensajes y su tiempo. Un nodo con error no frena al resto: sus salidas quedan vacías o nulas.

Sin Qt y sin OpenCascade (los nodos de geometría lo importan recién al cargarse el catálogo).
"""
import copy
import difflib
import hashlib
import heapq
import json
import re
import sys
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field

from ..timeline.parametros import ErrorExpresion, nombres_usados
from .arbol import (MODIFICADORES, MODOS_EMPAREJADO, Arbol, ErrorArbol, Ruta, aplicar_modificador, cantidad_vueltas,
                    emparejar, emparejar_ramas)
from .nodos import ContextoNodo, ErrorNodo, catalogo, definicion
from .tipos import LIMITE_ITEMS, ErrorTipo, Plano, convertir, es_coordenada_literal, es_forma

FORMATO = "omnicad.grafo"
VERSION = 1
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CLAVES_GRAFO = {"formato", "version", "nombre", "descripcion", "nodos"}
_CLAVES_NODO = {"id", "tipo", "nombre", "entradas", "emparejado", "posicion"}
_CLAVES_ENTRADA = {"de", "valor", "arbol", "modificador"}
_MAX_MENSAJES = 5
_MAX_MOTORES = 8
PISTA_CATALOGO = "list_graph_nodes lista los tipos de nodo con sus entradas y salidas."
PISTA_CABLE = 'Un cable se escribe {"de": "nodo"} o {"de": "nodo.salida"}; un literal va directo (10, "ancho / 2", [0, 0, 0]).'


class ErrorGrafo(ValueError):
    """Grafo mal formado: tipo de nodo, puerto o cable inexistente, id repetido, ciclo…"""

    def __init__(self, mensaje, *pistas):
        super().__init__(mensaje)
        self.mensaje, self.pistas = mensaje, list(pistas)


@dataclass
class NodoGrafo:
    id: str
    tipo: str
    nombre: str = ""
    entradas: dict = field(default_factory=dict)
    emparejado: str = "larga"
    posicion: list | None = None

    @property
    def publico(self):
        """Nombre con el que se lo cita desde afuera: su nombre o, si no tiene, su id."""
        return self.nombre or self.id

    def a_json(self):
        d = {"id": self.id, "tipo": self.tipo}
        if self.nombre:
            d["nombre"] = self.nombre
        if self.entradas:
            d["entradas"] = copy.deepcopy(self.entradas)
        if self.emparejado != "larga":
            d["emparejado"] = self.emparejado
        if self.posicion is not None:
            d["posicion"] = list(self.posicion)
        return d


# ---------------------------------------------------------------- entradas: literal o cable
def _ref(texto):
    """'nodo' → ('nodo', None); 'nodo.salida' → ('nodo', 'salida')."""
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorGrafo(f"Cable mal escrito: {texto!r}.", PISTA_CABLE)
    nodo, _, puerto = texto.strip().partition(".")
    return nodo, (puerto or None)


def partes_entrada(valor):
    """(fuentes, literal, modificador) de una entrada: `fuentes` es [(nodo, puerto|None)] si es un cable, si no
    None (y `literal` es el valor)."""
    if isinstance(valor, dict) and _CLAVES_ENTRADA & set(valor) and set(valor) <= _CLAVES_ENTRADA:
        mod = valor.get("modificador")
        if "de" in valor:
            de = valor["de"]
            lista = [de] if isinstance(de, str) else de
            if not isinstance(lista, list) or not lista:
                raise ErrorGrafo(f"«de» tiene que ser un texto o una lista de textos: llegó {de!r}.", PISTA_CABLE)
            return [_ref(x) for x in lista], None, mod
        if "arbol" in valor:
            return None, {"arbol": valor["arbol"]}, mod
        if "valor" in valor:
            return None, valor["valor"], mod
        return None, None, mod
    return None, valor, None


def literal_a_arbol(literal, puerto, parametros=None):
    """Árbol de un literal del JSON convertido al tipo del puerto (las expresiones se evalúan con `parametros`)."""
    if literal is None:
        return Arbol()
    conv = lambda x: convertir(x, puerto.tipo, puerto.unidad, parametros)  # noqa: E731
    if isinstance(literal, dict) and set(literal) == {"arbol"}:
        try:
            return Arbol.desde_dict(literal["arbol"]).mapear(conv)
        except ErrorArbol as e:
            raise ErrorTipo(str(e)) from None
    if puerto.tipo in ("punto", "vector", "plano") and es_coordenada_literal(literal):
        return Arbol.de_valor(conv(literal))
    if isinstance(literal, list):
        return Arbol.de_lista([conv(x) for x in literal])
    return Arbol.de_valor(conv(literal))


def _textos(valor, saltar=()):
    if isinstance(valor, str):
        return [] if valor.strip().upper() in saltar else [valor]
    if isinstance(valor, dict):
        return [t for k, v in valor.items() if k != "nombre" for t in _textos(v, saltar)]
    if isinstance(valor, (list, tuple)):
        return [t for v in valor for t in _textos(v, saltar)]
    return []


def _expresiones_literal(literal, puerto, tipo_nodo):
    """Textos de un literal que son expresiones con parámetros del documento (o el nombre de un parámetro)."""
    if tipo_nodo == "parametro" and puerto.nombre == "nombre" or tipo_nodo == "expresion" and puerto.nombre == "expresion":
        return [t for t in _textos(literal) if t.strip()]
    if puerto.tipo in ("numero", "entero", "punto", "vector"):
        return _textos(literal)
    if puerto.tipo == "plano":
        return _textos(literal, saltar=set(Plano.NOMBRES))
    return []


# ---------------------------------------------------------------- grafo
class Grafo:
    """Nodos en orden de carga, con sus entradas (literales o cables). Se arma con `agregar` / `conectar` o desde el
    JSON (`desde_json`). `evaluar` corre el grafo con caché (el motor queda guardado en el grafo)."""

    def __init__(self, nombre="", descripcion=""):
        self.nombre, self.descripcion = nombre, descripcion
        self.nodos = {}
        self._motor = None

    # ------------------------------------------------------------ armar
    def agregar(self, tipo, id=None, entradas=None, nombre="", emparejado="larga", posicion=None):
        """Agrega un nodo y lo devuelve. Valida el tipo, el id, los nombres de las entradas y su forma (los cables a
        otros nodos se validan en `validar`)."""
        d = definicion(tipo) if isinstance(tipo, str) else None
        if d is None:
            parecidos = difflib.get_close_matches(str(tipo), list(catalogo()), n=3)
            raise ErrorGrafo(f"Tipo de nodo desconocido: «{tipo}».",
                             *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []), PISTA_CATALOGO)
        if id is None:
            k = 1
            while f"{tipo}{k}" in self.nodos:
                k += 1
            id = f"{tipo}{k}"
        if not isinstance(id, str) or not _ID.match(id):
            raise ErrorGrafo(f"Id de nodo inválido: {id!r} (letras, dígitos y «_», sin empezar con dígito).")
        if id in self.nodos:
            raise ErrorGrafo(f"Hay dos nodos con el id «{id}».")
        if not isinstance(nombre, str):
            raise ErrorGrafo(f"El nombre del nodo «{id}» tiene que ser un texto.")
        if emparejado not in MODOS_EMPAREJADO:
            raise ErrorGrafo(f"Emparejado desconocido en «{id}»: {emparejado!r}. Válidos: {', '.join(MODOS_EMPAREJADO)}.")
        entradas = {} if entradas is None else entradas
        if not isinstance(entradas, dict):
            raise ErrorGrafo(f"Las entradas del nodo «{id}» van en un objeto {{puerto: valor}}.")
        validas = [p.nombre for p in d.entradas]
        for puerto, valor in entradas.items():
            if puerto not in validas:
                raise ErrorGrafo(f"El nodo «{id}» ({tipo}) no tiene la entrada «{puerto}».",
                                 f"Entradas de {tipo}: {', '.join(validas) or '(ninguna)'}.", PISTA_CATALOGO)
            if isinstance(valor, dict) and {"de", "valor", "arbol"} & set(valor):
                sobran = set(valor) - _CLAVES_ENTRADA
                if sobran or sum(k in valor for k in ("de", "valor", "arbol")) != 1:
                    raise ErrorGrafo(f"La entrada «{id}.{puerto}» lleva UNA de estas claves: de, valor o arbol (y "
                                     "opcionalmente modificador)" + (f"; sobran: {', '.join(sorted(sobran))}" if sobran
                                                                      else "") + ".", PISTA_CABLE)
            _fuentes, _lit, mod = partes_entrada(valor)
            if mod is not None and mod not in MODIFICADORES:
                raise ErrorGrafo(f"Modificador desconocido en «{id}.{puerto}»: {mod!r}. Válidos: {', '.join(MODIFICADORES)}.")
        if posicion is not None and not (isinstance(posicion, list) and len(posicion) == 2
                                         and all(isinstance(c, (int, float)) for c in posicion)):
            raise ErrorGrafo(f"La posición del nodo «{id}» es [x, y].")
        try:
            entradas = json.loads(json.dumps(entradas))
        except (TypeError, ValueError):
            raise ErrorGrafo(f"Las entradas del nodo «{id}» tienen que ser datos JSON.") from None
        n = NodoGrafo(id, tipo, nombre, entradas, emparejado, posicion)
        self.nodos[id] = n
        return n

    def conectar(self, desde, hacia):
        """Cable de `desde` ("nodo" o "nodo.salida") a `hacia` ("nodo.entrada"); se suma a los cables que ya tenga."""
        nodo, puerto = _ref(hacia)
        if nodo not in self.nodos or puerto is None:
            raise ErrorGrafo(f"Destino de cable inválido: «{hacia}» (va «nodo.entrada»).")
        n = self.nodos[nodo]
        if definicion(n.tipo).entrada(puerto) is None:
            raise ErrorGrafo(f"El nodo «{nodo}» no tiene la entrada «{puerto}».")
        fuentes, _lit, mod = partes_entrada(n.entradas.get(puerto))
        lista = [f"{a}.{b}" if b else a for a, b in (fuentes or [])] + [desde]
        n.entradas[puerto] = {"de": lista} if mod is None else {"de": lista, "modificador": mod}
        self.validar()

    def poner_entrada(self, nodo, puerto, valor):
        """Reemplaza la entrada `puerto` del nodo por `valor` (literal o cable)."""
        n = self._nodo(nodo)
        if definicion(n.tipo).entrada(puerto) is None:
            raise ErrorGrafo(f"El nodo «{n.id}» no tiene la entrada «{puerto}».")
        n.entradas[puerto] = json.loads(json.dumps(valor))

    def quitar(self, nodo):
        del self.nodos[self._nodo(nodo).id]

    def _nodo(self, ref):
        if ref in self.nodos:
            return self.nodos[ref]
        hallados = [n for n in self.nodos.values() if n.nombre == ref]
        if len(hallados) == 1:
            return hallados[0]
        if hallados:
            raise ErrorGrafo(f"Hay {len(hallados)} nodos llamados «{ref}»: {', '.join(n.id for n in hallados)}.")
        parecidos = difflib.get_close_matches(str(ref), list(self.nodos) + [n.nombre for n in self.nodos.values() if n.nombre], n=3)
        raise ErrorGrafo(f"No existe el nodo «{ref}».", *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))

    # ------------------------------------------------------------ estructura
    def fuentes(self, nodo):
        """{entrada: ([(nodo, salida)], modificador)} de los cables del nodo, con la salida ya resuelta."""
        salida = {}
        for puerto, valor in nodo.entradas.items():
            fuentes, _lit, mod = partes_entrada(valor)
            if fuentes is None:
                continue
            resueltas = []
            for origen, sal in fuentes:
                if origen not in self.nodos:
                    parecidos = difflib.get_close_matches(origen, list(self.nodos), n=3)
                    raise ErrorGrafo(f"El cable de «{nodo.id}.{puerto}» viene de «{origen}», que no existe.",
                                     *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []), PISTA_CABLE)
                d = definicion(self.nodos[origen].tipo)
                if sal is None:
                    sal = d.salidas[0].nombre
                elif d.salida(sal) is None:
                    raise ErrorGrafo(f"El nodo «{origen}» ({d.tipo}) no tiene la salida «{sal}» (cable a «{nodo.id}.{puerto}»).",
                                     f"Salidas de {d.tipo}: {', '.join(p.nombre for p in d.salidas)}.")
                resueltas.append((origen, sal))
            salida[puerto] = (resueltas, mod)
        return salida

    def validar(self):
        """Revisa cables y ciclos (lo demás ya lo revisó `agregar`). Lanza ErrorGrafo."""
        self.orden()

    def orden(self):
        """Ids en orden topológico (estable: a igualdad, el orden de carga). Un ciclo es un ErrorGrafo que lo nombra."""
        ids = list(self.nodos)
        indice = {nid: i for i, nid in enumerate(ids)}
        deps = {nid: {o for lista, _m in self.fuentes(n).values() for o, _s in lista} for nid, n in self.nodos.items()}
        hijos = {nid: [] for nid in ids}
        for nid, ds in deps.items():
            for o in ds:
                hijos[o].append(nid)
        pendientes = {nid: len(ds) for nid, ds in deps.items()}
        listos = [indice[nid] for nid in ids if pendientes[nid] == 0]
        heapq.heapify(listos)
        salida = []
        while listos:
            nid = ids[heapq.heappop(listos)]
            salida.append(nid)
            for h in hijos[nid]:
                pendientes[h] -= 1
                if pendientes[h] == 0:
                    heapq.heappush(listos, indice[h])
        if len(salida) < len(ids):
            ciclo = self._un_ciclo(deps, set(ids) - set(salida))
            raise ErrorGrafo(f"El grafo tiene un ciclo: {' → '.join(ciclo)}.",
                             "Un nodo no puede depender (directa o indirectamente) de su propia salida: sacá uno de "
                             "los cables del ciclo.")
        return salida

    def _un_ciclo(self, deps, restantes):
        """Un ciclo entre los nodos que no se pudieron ordenar, en el sentido de los cables."""
        actual = next(nid for nid in self.nodos if nid in restantes)
        camino, visto = [], {}
        while actual not in visto:
            visto[actual] = len(camino)
            camino.append(actual)
            actual = next(o for o in sorted(deps[actual], key=list(self.nodos).index) if o in restantes)
        ciclo = camino[visto[actual]:] + [actual]
        return list(reversed(ciclo))

    # ------------------------------------------------------------ entradas y salidas públicas
    def entradas_publicas(self):
        """Nodos de la categoría «entrada» que tienen el puerto «valor»: se cambian por su nombre (o id)."""
        return [n for n in self.nodos.values()
                if definicion(n.tipo).categoria == "entrada" and definicion(n.tipo).entrada("valor") is not None]

    def salidas_publicas(self):
        return [n for n in self.nodos.values() if definicion(n.tipo).categoria == "salida"]

    def destino(self, clave):
        """(id, entrada) que cambia la clave de `entradas`: el nombre o id de un nodo de entrada (su «valor») o
        "nodo.entrada" para cualquier entrada de cualquier nodo."""
        if not isinstance(clave, str) or not clave.strip():
            raise ErrorGrafo(f"Nombre de entrada inválido: {clave!r}.")
        nombres = [n.publico for n in self.entradas_publicas()]
        if "." in clave:
            ref, _, puerto = clave.rpartition(".")
            n = self._nodo(ref)
            if definicion(n.tipo).entrada(puerto) is None:
                raise ErrorGrafo(f"El nodo «{n.id}» ({n.tipo}) no tiene la entrada «{puerto}».",
                                 f"Entradas: {', '.join(p.nombre for p in definicion(n.tipo).entradas)}.")
            return n.id, puerto
        publicas = self.entradas_publicas()
        hallados = [n for n in publicas if n.nombre == clave] or [n for n in publicas if n.id == clave]
        if len(hallados) > 1:
            raise ErrorGrafo(f"Hay {len(hallados)} entradas llamadas «{clave}»: usá el id ({', '.join(n.id for n in hallados)}).")
        if not hallados:
            if clave in self.nodos:
                raise ErrorGrafo(f"«{clave}» no es un nodo de entrada: para cambiar una de sus entradas usá "
                                 f"«{clave}.<entrada>».")
            parecidos = difflib.get_close_matches(clave, nombres, n=3)
            raise ErrorGrafo(f"El grafo no tiene la entrada «{clave}».",
                             f"Entradas del grafo: {', '.join(nombres) or '(ninguna)'}.",
                             *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []),
                             "Cualquier entrada de un nodo se cambia con «nodo.entrada».")
        return hallados[0].id, "valor"

    def resolver_entradas(self, entradas):
        """{(id, entrada): valor} de un dict de entradas externas (ver `destino`)."""
        if entradas is None:
            return {}
        if not isinstance(entradas, dict):
            raise ErrorGrafo("Las entradas van en un objeto {nombre: valor}.")
        salida = {}
        for clave, valor in entradas.items():
            destino = self.destino(clave)
            if destino in salida:
                raise ErrorGrafo(f"La entrada «{clave}» se cambia dos veces.")
            if partes_entrada(valor)[0] is not None:
                raise ErrorGrafo(f"La entrada «{clave}» recibe un valor, no un cable.",
                                 "Los cables van dentro del grafo; desde afuera se pasan números, expresiones, listas, "
                                 "puntos o {\"arbol\": {...}}.")
            salida[destino] = valor
        return salida

    def expresiones(self, entradas=None):
        """Textos de los literales que son expresiones con parámetros del documento (y nombres de parámetro): con
        ellos el documento sabe qué parámetros usa el grafo horneado."""
        salida = []
        cambios = {}
        try:
            cambios = self.resolver_entradas(entradas)
        except ErrorGrafo:
            salida += [v for v in (entradas or {}).values() if isinstance(v, str)]
        for n in self.nodos.values():
            d = definicion(n.tipo)
            for p in d.entradas:
                valor = cambios.get((n.id, p.nombre), n.entradas.get(p.nombre))
                fuentes, literal, _mod = partes_entrada(valor)
                if fuentes is None:
                    salida += _expresiones_literal(literal, p, n.tipo)
        return salida

    # ------------------------------------------------------------ JSON
    def a_json(self):
        d = {"formato": FORMATO, "version": VERSION}
        if self.nombre:
            d["nombre"] = self.nombre
        if self.descripcion:
            d["descripcion"] = self.descripcion
        d["nodos"] = [n.a_json() for n in self.nodos.values()]
        return d

    @classmethod
    def desde_json(cls, datos):
        """Grafo desde su JSON (dict o texto). Valida tipos, puertos, cables y ciclos: lanza ErrorGrafo."""
        if isinstance(datos, str):
            try:
                datos = json.loads(datos)
            except ValueError as e:
                raise ErrorGrafo(f"El grafo no es JSON válido: {e}") from None
        if not isinstance(datos, dict):
            raise ErrorGrafo("El grafo es un objeto JSON con la lista «nodos».", PISTA_CATALOGO)
        desconocidas = set(datos) - _CLAVES_GRAFO
        if desconocidas:
            raise ErrorGrafo(f"Claves desconocidas en el grafo: {', '.join(sorted(desconocidas))}.",
                             f"Claves válidas: {', '.join(sorted(_CLAVES_GRAFO))}.")
        if datos.get("formato", FORMATO) != FORMATO:
            raise ErrorGrafo(f"Formato de grafo desconocido: {datos.get('formato')!r} (se esperaba «{FORMATO}»).")
        version = datos.get("version", VERSION)
        if not isinstance(version, int) or isinstance(version, bool) or version > VERSION:
            raise ErrorGrafo(f"Versión de grafo no soportada: {version!r} (esta versión lee hasta la {VERSION}).")
        nodos = datos.get("nodos")
        if not isinstance(nodos, list):
            raise ErrorGrafo("Falta la lista «nodos» del grafo.", PISTA_CATALOGO)
        g = cls(str(datos.get("nombre") or ""), str(datos.get("descripcion") or ""))
        for i, d in enumerate(nodos):
            if not isinstance(d, dict):
                raise ErrorGrafo(f"El nodo {i} no es un objeto {{id, tipo, entradas}}.")
            sobran = set(d) - _CLAVES_NODO
            if sobran:
                raise ErrorGrafo(f"Claves desconocidas en el nodo {d.get('id', i)!r}: {', '.join(sorted(sobran))}.",
                                 f"Claves válidas: {', '.join(sorted(_CLAVES_NODO))}.")
            if "tipo" not in d:
                raise ErrorGrafo(f"Al nodo {d.get('id', i)!r} le falta el «tipo».", PISTA_CATALOGO)
            g.agregar(d["tipo"], d.get("id"), d.get("entradas"), d.get("nombre") or "", d.get("emparejado") or "larga",
                      d.get("posicion"))
        g.validar()
        return g

    # ------------------------------------------------------------ evaluar
    def evaluar(self, entradas=None, parametros=None):
        """Corre el grafo (con la caché de las evaluaciones anteriores de ESTE grafo). Ver `Motor.evaluar`."""
        if self._motor is None:
            self._motor = Motor(self)
        return self._motor.evaluar(entradas, parametros)


def a_json(grafo):
    """El grafo como dict JSON (para guardarlo, p. ej. dentro de un paso del `.omnicad`)."""
    return grafo.a_json()


def desde_json(datos):
    """Grafo desde su dict JSON (o texto JSON)."""
    return Grafo.desde_json(datos)


# ---------------------------------------------------------------- resultado
@dataclass
class InfoNodo:
    id: str
    tipo: str
    nombre: str
    estado: str                 # "ok" | "aviso" | "error"
    mensajes: list
    duracion: float             # segundos de la última vez que se calculó
    ejecutado: bool             # False: salió de la caché
    salidas: dict               # salida → Arbol


class Resultado:
    """Lo que dejó una evaluación: estado y salidas de cada nodo, en orden topológico."""

    def __init__(self, grafo, orden, nodos, duracion):
        self.grafo, self.orden, self.nodos, self.duracion = grafo, orden, nodos, duracion

    def arbol(self, ref):
        """Árbol de una salida: "nodo" (su primera salida) o "nodo.salida"; el nodo por id o nombre."""
        nodo, puerto = _ref(ref)
        n = self.grafo._nodo(nodo)
        info = self.nodos[n.id]
        puerto = puerto or next(iter(info.salidas))
        if puerto not in info.salidas:
            raise ErrorGrafo(f"El nodo «{n.id}» no tiene la salida «{puerto}».")
        return info.salidas[puerto]

    @property
    def salidas(self):
        """{nombre público: Arbol} de los nodos de salida, en orden de carga."""
        return {n.publico: self.nodos[n.id].salidas["valor"] for n in self.grafo.salidas_publicas()}

    def cuerpos(self, nombres=None):
        """[(nombre de la salida, forma)] de los cuerpos que llegan a las salidas (todas, o solo `nombres`)."""
        salidas = self.salidas
        if nombres:
            faltan = [x for x in nombres if x not in salidas]
            if faltan:
                raise ErrorGrafo(f"El grafo no tiene las salidas: {', '.join(faltan)}.",
                                 f"Salidas: {', '.join(salidas) or '(ninguna)'}.")
            salidas = {k: v for k, v in salidas.items() if k in nombres}
        return [(k, x) for k, a in salidas.items() for x in a.items() if es_forma(x)]

    @property
    def ejecutados(self):
        return [nid for nid in self.orden if self.nodos[nid].ejecutado]

    def _mensajes(self, estado):
        return [(nid, m) for nid in self.orden if self.nodos[nid].estado == estado for m in self.nodos[nid].mensajes]

    @property
    def errores(self):
        """[(id, mensaje)] de los nodos con error."""
        return self._mensajes("error")

    @property
    def avisos(self):
        return self._mensajes("aviso")


# ---------------------------------------------------------------- motor
def _canon(arbol):
    return json.dumps(arbol.a_dict(), sort_keys=True, ensure_ascii=False, default=repr)


def _parametros_canon(parametros):
    items = dict.items(parametros) if isinstance(parametros, dict) else parametros.items()   # sin marcar lecturas
    return sorted((str(k), float(v)) for k, v in items)


def _sin_marcar(parametros, nombre):
    """Valor de un parámetro sin anotarlo como leído (el `_Lecturas` del timeline anota lo que se consulta)."""
    v = dict.get(parametros, nombre) if isinstance(parametros, dict) else parametros.get(nombre)
    return None if v is None else float(v)


def _lecturas(n, d, cambios, cables, parametros):
    """Parámetros del documento que lee un nodo `usa_contexto`, para su huella: los nombrados en sus entradas de texto
    (el nombre del nodo «parametro», la expresión del nodo «expresion»). Si un texto llega por cable puede nombrar
    cualquiera: entran todos."""
    textos = []
    for p in d.entradas:
        if p.tipo != "texto":
            continue
        if p.nombre in cables:
            return _parametros_canon(parametros)
        valor = cambios[(n.id, p.nombre)] if (n.id, p.nombre) in cambios else n.entradas.get(p.nombre)
        _f, literal, _m = partes_entrada(valor)
        textos += _textos(p.defecto if literal is None and isinstance(p.defecto, str) else literal)
    nombres = sorted({x for t in textos for x in nombres_usados(t)})
    return [(x, _sin_marcar(parametros, x)) for x in nombres]


def _mensaje(e):
    if isinstance(e, (ErrorNodo, ErrorTipo, ErrorExpresion, ErrorArbol)):
        return str(e)
    geo = sys.modules.get(f"{__package__.rpartition('.')[0]}.nucleo.geometria")    # sin cargar OCC si no se usó
    if geo is not None and isinstance(e, geo.ErrorGeometria):
        return str(e)
    if isinstance(e, ZeroDivisionError):
        return "División por cero."
    if isinstance(e, OverflowError):
        return "El resultado es demasiado grande."
    return f"Error inesperado ({type(e).__name__}): {e}"


def _nulos(d):
    return tuple(None for _ in d.salidas)


def _anotar(lista, texto):
    if texto not in lista:
        lista.append(texto)


def _vuelta(d, combo, ctx, errores):
    """Una vuelta de un nodo ítem/lista: convierte, corre la función y devuelve una tupla con una por salida."""
    args = {}
    for p, unidad in zip(d.entradas, combo, strict=True):
        try:
            if p.acceso == "lista":
                args[p.nombre] = None if unidad is None else [convertir(x, p.tipo, p.unidad, ctx.parametros)
                                                              for x in unidad]
            else:
                v = convertir(unidad, p.tipo, p.unidad, ctx.parametros)
                if v is None and p.defecto is not None:
                    _anotar(ctx.avisos, f"Entrada nula en «{p.nombre}»: esa vuelta da nulo.")
                    return _nulos(d)
                args[p.nombre] = v
        except (ErrorTipo, ErrorExpresion) as e:
            _anotar(errores, f"Entrada «{p.nombre}»: {e}")
            return _nulos(d)
    if d.recibe_ctx:
        args["ctx"] = ctx
    try:
        r = d.funcion(**args)
    except Exception as e:  # noqa: BLE001 — una vuelta que falla da nulo; el nodo informa el error
        _anotar(errores, _mensaje(e))
        return _nulos(d)
    r = (r,) if len(d.salidas) == 1 else tuple(r)
    if len(r) != len(d.salidas):
        _anotar(errores, f"Error interno del nodo {d.tipo}: devolvió {len(r)} valores para {len(d.salidas)} salidas.")
        return _nulos(d)
    return r


def _convertidor(p, parametros):
    return lambda x: convertir(x, p.tipo, p.unidad, parametros)


def _correr_por_arbol(d, efectivos, ctx, errores, salidas):
    """Nodo con alguna entrada «arbol»: corre una vez con los árboles enteros."""
    args = {}
    for p in d.entradas:
        a = efectivos[p.nombre]
        try:
            if p.acceso == "arbol":
                args[p.nombre] = a.mapear(_convertidor(p, ctx.parametros))
            elif p.acceso == "lista":
                args[p.nombre] = [convertir(x, p.tipo, p.unidad, ctx.parametros) for x in a.ramas()[0][1]]
            else:
                args[p.nombre] = convertir(a.primero(), p.tipo, p.unidad, ctx.parametros)
        except (ErrorTipo, ErrorExpresion) as e:
            _anotar(errores, f"Entrada «{p.nombre}»: {e}")
            return salidas
    if d.recibe_ctx:
        args["ctx"] = ctx
    try:
        r = d.funcion(**args)
    except Exception as e:  # noqa: BLE001
        _anotar(errores, _mensaje(e))
        return salidas
    r = (r,) if len(d.salidas) == 1 else tuple(r)
    for s, v in zip(d.salidas, r, strict=True):
        if s.acceso == "arbol":
            salidas[s.nombre] = v if isinstance(v, Arbol) else Arbol.de_valor(v)
        elif s.acceso == "lista":
            salidas[s.nombre] = Arbol.de_lista(v or [])
        else:
            salidas[s.nombre] = Arbol.de_valor(v)
    return salidas


def ejecutar_nodo(d, arboles, emparejado="larga", parametros=None):
    """Corre el nodo `d` con los árboles de sus entradas: (salidas {nombre: Arbol}, avisos, errores).

    Entradas vacías: si es obligatoria, el nodo no corre (aviso); si no, se usa su valor por defecto. Las ramas se
    emparejan como «lista más larga» y, dentro de cada grupo de ramas, los ítems según `emparejado`. Una salida
    «lista» de un nodo que corre varias veces en la misma rama va a sub-ramas {ruta;vuelta}."""
    ctx = ContextoNodo({} if parametros is None else parametros)
    errores = []
    salidas = {s.nombre: Arbol() for s in d.salidas}
    faltan = [p.nombre for p in d.entradas if p.obligatorio and arboles.get(p.nombre, Arbol()).vacio]
    if faltan:
        ctx.aviso("Faltan datos en " + ", ".join(f"«{x}»" for x in faltan) + ": el nodo no corrió.")
        return salidas, ctx.avisos, errores
    efectivos, sin_lista = {}, set()
    for p in d.entradas:
        a = arboles.get(p.nombre) or Arbol()
        if a.vacio:
            if p.acceso == "lista" and p.defecto is None:
                sin_lista.add(p.nombre)
                a = Arbol.de_valor(None)
            elif p.acceso == "lista":
                a = Arbol.de_lista(p.defecto)
            else:
                a = Arbol.de_valor(p.defecto)
        efectivos[p.nombre] = a
    if d.por_arbol:
        return _correr_por_arbol(d, efectivos, ctx, errores, salidas), ctx.avisos, errores
    unidades = []
    for p in d.entradas:
        a = efectivos[p.nombre]
        if p.acceso == "lista" and p.nombre not in sin_lista:
            a = Arbol([(r, [items]) for r, items in a.ramas()])
        unidades.append(a)
    grupos = emparejar_ramas(unidades) if unidades else [(Ruta(0), [])]
    total = sum(cantidad_vueltas([len(x) for x in ramas], emparejado) for _r, ramas in grupos)
    if total > LIMITE_ITEMS:
        errores.append(f"El nodo daría {total} vueltas y el tope es {LIMITE_ITEMS}: revisá el emparejado («cruzada» "
                       "multiplica los largos) o el tamaño de las listas.")
        return salidas, ctx.avisos, errores
    for ruta, ramas in grupos:
        combos = emparejar(ramas, emparejado)
        varias = len(combos) > 1
        for k, combo in enumerate(combos):
            valores = _vuelta(d, combo, ctx, errores)
            for s, v in zip(d.salidas, valores, strict=True):
                if s.acceso == "lista":
                    salidas[s.nombre].extender(ruta.mas(k) if varias else ruta, list(v) if v is not None else [])
                else:
                    salidas[s.nombre].agregar(ruta, v)
    return salidas, ctx.avisos, errores


class Motor:
    """Evalúa un `Grafo` con caché por nodo. `ejecuciones` cuenta cuántas veces se calculó cada nodo."""

    def __init__(self, grafo):
        self.grafo = grafo
        self._cache = {}            # id → (huella, salidas, estado, mensajes, duración)
        self.ejecuciones = Counter()

    def evaluar(self, entradas=None, parametros=None):
        """Corre el grafo. `entradas`: {nombre o "nodo.entrada": valor} que reemplazan literales (ver
        `Grafo.destino`); `parametros`: valores de los parámetros del documento ({nombre: valor en mm/grados}) para
        las expresiones. Lanza ErrorGrafo si el grafo está mal formado; los errores de cada nodo quedan en el
        resultado."""
        g = self.grafo
        orden = g.orden()
        cambios = g.resolver_entradas(entradas)
        parametros = {} if parametros is None else parametros
        inicio = time.perf_counter()
        huellas, nodos = {}, {}
        for nid in orden:
            n = g.nodos[nid]
            d = definicion(n.tipo)
            # una entrada cambiada desde afuera reemplaza también a un cable
            cables = {k: v for k, v in g.fuentes(n).items() if (nid, k) not in cambios}
            literales, firma, error_literal = {}, {}, None
            for p in d.entradas:
                if p.nombre in cables:
                    lista, mod = cables[p.nombre]
                    firma[p.nombre] = ["de", [[huellas[o], s] for o, s in lista], mod]
                    continue
                valor = cambios[(nid, p.nombre)] if (nid, p.nombre) in cambios else n.entradas.get(p.nombre)
                _f, literal, mod = partes_entrada(valor)
                try:
                    arbol = aplicar_modificador(literal_a_arbol(literal, p, parametros), mod)
                except (ErrorTipo, ErrorExpresion, ErrorArbol) as e:
                    error_literal = error_literal or f"Entrada «{p.nombre}»: {e}"
                    firma[p.nombre] = ["error", repr(literal)]
                    continue
                literales[p.nombre] = arbol
                firma[p.nombre] = ["lit", _canon(arbol)]
            clave = [n.tipo, n.emparejado, firma, error_literal]
            if d.usa_contexto:
                clave.append(_lecturas(n, d, cambios, cables, parametros))
            huella = hashlib.sha1(json.dumps(clave, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            previo = self._cache.get(nid)
            if previo is not None and previo[0] == huella:
                _h, salidas, estado, mensajes, duracion = previo
                ejecutado = False
            else:
                t0 = time.perf_counter()
                if error_literal:
                    salidas, estado, mensajes = {s.nombre: Arbol() for s in d.salidas}, "error", [error_literal]
                else:
                    arboles = dict(literales)
                    for puerto, (lista, mod) in cables.items():
                        a = Arbol()
                        for o, s in lista:
                            a = a.fusionar(nodos[o].salidas[s])
                        arboles[puerto] = aplicar_modificador(a, mod)
                    salidas, avisos, errores = ejecutar_nodo(d, arboles, n.emparejado, parametros)
                    estado = "error" if errores else "aviso" if avisos else "ok"
                    mensajes = (errores or avisos)[:_MAX_MENSAJES]
                    resto = len(errores or avisos) - len(mensajes)
                    if resto > 0:
                        mensajes.append(f"… y {resto} mensaje(s) más.")
                duracion = time.perf_counter() - t0
                self._cache[nid] = (huella, salidas, estado, mensajes, duracion)
                self.ejecuciones[nid] += 1
                ejecutado = True
            huellas[nid] = huella
            nodos[nid] = InfoNodo(nid, n.tipo, n.nombre, estado, list(mensajes), duracion, ejecutado, salidas)
        for viejo in set(self._cache) - set(g.nodos):
            del self._cache[viejo]
        return Resultado(g, orden, nodos, time.perf_counter() - inicio)


_MOTORES = OrderedDict()


def motor_para(datos):
    """Motor (con su caché) para el grafo `datos` (dict JSON). Reusa el de una evaluación anterior del MISMO grafo,
    así cambiar una entrada recalcula solo lo que está aguas abajo; guarda los últimos `_MAX_MOTORES`. El grafo del
    motor es compartido: no se modifica (para editar, `Grafo.desde_json`)."""
    try:
        clave = json.dumps(datos, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        raise ErrorGrafo("El grafo tiene que ser datos JSON (objeto con la lista «nodos»).") from None
    motor = _MOTORES.get(clave)
    if motor is None:
        motor = Motor(Grafo.desde_json(datos))
        _MOTORES[clave] = motor
        while len(_MOTORES) > _MAX_MOTORES:
            _MOTORES.popitem(last=False)
    else:
        _MOTORES.move_to_end(clave)
    return motor
