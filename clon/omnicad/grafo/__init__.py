# -*- coding: utf-8 -*-
"""
Programación visual sin ventana (tipo Grasshopper, ver `docs/brechas_grasshopper.md` y `docs/grafo.md`).

Un grafo de nodos se evalúa como flujo de datos puro y produce valores y cuerpos; «Hornear» lo pasa al timeline
(`timeline/ops_grafo.py`, operación «grafo»). Piezas:
  - `arbol`: el modelo de datos (Arbol, Ruta, emparejado de listas, aplanar / injertar / simplificar / invertir);
  - `tipos`: tipos de puerto y su conversión (número, entero, booleano, texto, punto, vector, plano, curva, cuerpo);
  - `nodos` y `nodos_*`: el catálogo de nodos (entradas, matemática, listas, árboles, vectores, curvas, sólidos);
  - `motor`: Grafo (JSON, validación, ciclos, orden topológico) y Motor (caché por nodo, tiempos).

Sin Qt. Importar el paquete no carga OpenCascade: los nodos de geometría se cargan con el primer `catalogo()`.

    from omnicad.grafo import Grafo
    g = Grafo()
    g.agregar("numero", "lado", {"valor": 10})
    g.agregar("caja", "c", {"ancho": {"de": "lado"}})
    g.agregar("salida", "pieza", {"valor": {"de": "c"}})
    r = g.evaluar()
    r.cuerpos()   → [("pieza", <forma OCC>)]
"""
from .arbol import MODIFICADORES, MODOS_EMPAREJADO, Arbol, ErrorArbol, Ruta, emparejar, emparejar_ramas
from .motor import (FORMATO, VERSION, ErrorGrafo, Grafo, Motor, Resultado, a_json, desde_json, ejecutar_nodo,
                    motor_para)
from .nodos import CATEGORIAS, ErrorNodo, catalogo, definicion
from .tipos import Curva, ErrorTipo, Plano

__all__ = ["Arbol", "Ruta", "ErrorArbol", "emparejar", "emparejar_ramas", "MODOS_EMPAREJADO", "MODIFICADORES",
           "Grafo", "Motor", "Resultado", "ErrorGrafo", "a_json", "desde_json", "ejecutar_nodo", "motor_para",
           "FORMATO", "VERSION", "CATEGORIAS", "ErrorNodo", "catalogo", "definicion", "Curva", "Plano", "ErrorTipo"]
