# -*- coding: utf-8 -*-
"""
Paso «Grafo» del timeline (GH5 de `docs/brechas_grasshopper.md`): «Hornear» un grafo de programación visual.

El paso guarda el grafo entero (su JSON, ver `grafo/motor.py`) y los valores de sus entradas en sus parámetros, y lo
vuelve a evaluar en cada recálculo: el resultado sigue siendo paramétrico. Las entradas pueden ser expresiones con los
parámetros del documento («ancho / 2»), y el grafo puede leer parámetros con el nodo «parametro»: al cambiar uno,
el documento recalcula este paso (el paso declara esos nombres en `expresiones()`, así tampoco se pueden borrar).

Los cuerpos salen de los nodos «salida» (todas o las de `salidas`) y se aplican con `operacion` como cualquier
operación de cuerpo de Fusion: cuerpo nuevo, unir, cortar o intersecar sobre `objetivo`. La evaluación usa el motor
con caché de `grafo.motor_para`: editar una entrada recalcula solo los nodos que cuelgan de ella.

Fusion no tiene programación visual; lo más cercano son los parámetros y «Crear operación base» (cuerpos fijos, que
es `fixed=True` en la herramienta bake_graph).
"""
from ..nucleo import geometria as geo
from ..grafo import ErrorGrafo, Grafo, motor_para
from .operaciones import (OPERACIONES_CUERPO, ErrorOperacion, Operacion, _deps_objetivo, aplicar_resultado,
                          registrar_operacion)
from .parametros import nombres_usados

_MAX_MENSAJES = 3


def cuerpos_de_salida(resultado, salidas=None):
    """[(nombre, forma, tipo)] de los cuerpos que llegan a las salidas: cada sólido suelto por separado ("solido"),
    o la forma entera como "superficie" si no tiene sólidos."""
    piezas = []
    for nombre, forma in resultado.cuerpos(salidas or None):
        if geo.esta_vacia(forma):
            continue
        solidos = geo.solidos(forma)
        piezas += [(nombre, s, "solido") for s in solidos] if solidos else [(nombre, forma, "superficie")]
    return piezas


def nombres_de_cuerpos(piezas):
    """Nombre de cada pieza: el de su salida, numerado si la salida da varias («pieza 1», «pieza 2»…)."""
    cuantos = {}
    for nombre, *_ in piezas:
        cuantos[nombre] = cuantos.get(nombre, 0) + 1
    vistos, salida = {}, []
    for nombre, *_ in piezas:
        vistos[nombre] = vistos.get(nombre, 0) + 1
        salida.append(nombre if cuantos[nombre] == 1 else f"{nombre} {vistos[nombre]}")
    return salida


def mensajes_de_nodos(lista):
    """«nodo: mensaje; …» de los primeros mensajes (y cuántos más hay)."""
    textos = [f"«{nid}»: {m}" for nid, m in lista[:_MAX_MENSAJES]]
    if len(lista) > _MAX_MENSAJES:
        textos.append(f"y {len(lista) - _MAX_MENSAJES} más")
    return "; ".join(textos)


class OpGrafo(Operacion):
    """Grafo de programación visual horneado (como una definición de Grasshopper pasada a la historia): guarda el grafo
    y sus entradas y lo reevalúa en cada recálculo. `grafo`: el JSON del grafo («formato» omnicad.grafo, lista
    «nodos»). `entradas`: {nombre de entrada o "nodo.entrada": valor o expresión con parámetros}. `salidas`: nombres de
    los nodos «salida» que se hornean (vacío = todas). `operacion`: nuevo, unir, cortar o intersecar; `objetivo`: los
    cuerpos para unir, cortar o intersecar (vacío = los que toca)."""
    TIPO, ETIQUETA, ICONO = "grafo", "Grafo", "⌗"
    PARAMS = {"grafo": {}, "entradas": {}, "salidas": [], "operacion": "nuevo", "objetivo": ""}
    OPCIONES = {"operacion": OPERACIONES_CUERPO}

    def dependencias(self):
        return super().dependencias() | _deps_objetivo(self.p.get("objetivo"))

    def expresiones(self):
        """Expresiones de las entradas y de los literales del grafo, y los nombres de los parámetros que lee: el
        documento las usa para saber qué parámetros usa este paso."""
        entradas = self.p.get("entradas") if isinstance(self.p.get("entradas"), dict) else {}
        try:
            return Grafo.desde_json(self.p.get("grafo")).expresiones(entradas)
        except (ErrorGrafo, TypeError, ValueError):
            return [v for v in entradas.values() if isinstance(v, str)]

    def ejecutar(self, estado, ctx):
        datos = self.p.get("grafo")
        if not isinstance(datos, dict) or not datos.get("nodos"):
            raise ErrorOperacion("El grafo está vacío: «grafo» lleva el JSON del grafo con su lista «nodos» "
                                 "(list_graph_nodes muestra el formato).")
        try:
            resultado = motor_para(datos).evaluar(self.p.get("entradas") or {}, ctx.valores)
        except ErrorGrafo as e:
            raise ErrorOperacion(f"Grafo inválido: {e}") from e
        for expr in self.expresiones():          # también cuando los nodos salieron de la caché sin leerlos
            for nombre in nombres_usados(expr):
                _ = nombre in ctx.valores
        if resultado.errores:
            raise ErrorOperacion(f"El grafo tiene nodos con error: {mensajes_de_nodos(resultado.errores)}.")
        if resultado.avisos:
            ctx.aviso(f"Avisos del grafo: {mensajes_de_nodos(resultado.avisos)}.")
        try:
            piezas = cuerpos_de_salida(resultado, self.p.get("salidas") or None)
        except ErrorGrafo as e:
            raise ErrorOperacion(str(e)) from e
        if not piezas:
            salidas = ", ".join(resultado.salidas) or "(ninguna)"
            raise ErrorOperacion(f"El grafo no dio cuerpos: ninguna salida tiene un cuerpo (salidas: {salidas}). "
                                 "Conectá un nodo de sólidos a un nodo «salida».")
        operacion = self.p.get("operacion", "nuevo")
        if operacion == "nuevo":
            for (_n, forma, tipo), nombre in zip(piezas, nombres_de_cuerpos(piezas), strict=True):
                estado.nuevo_cuerpo(self.id, forma, tipo, nombre=nombre)
            return
        afectados = []
        for _n, forma, _t in piezas:
            afectados += aplicar_resultado(estado, ctx, self.id, forma, operacion, self.p.get("objetivo") or "")
        self._registrar_usados(afectados)


registrar_operacion(OpGrafo)
