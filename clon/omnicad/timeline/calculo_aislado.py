# -*- coding: utf-8 -*-
"""B-48: transportar el cálculo del hijo como datos y BREP, sin ejecutar otra vez las operaciones.

El grafo conserva las formas y objetos compartidos entre pasos: no copia una forma por cada estado.
Solo se reconstruyen clases conocidas del modelo. No admite pickle, nombres de módulos ni código recibido.
"""
import base64
import math
import os
import time
import zlib

import numpy as np

from ..nucleo import aislado, consultas, geometria as geo, intercambio
from ..restricciones.boceto import Boceto
from ..restricciones.boceto3d import Resultado3D
from ..restricciones.solver import ResultadoSolver
from .operaciones import BocetoResuelto, Cuerpo, EstadoModelo, OpBoceto

_TOPE_BYTES = 512 * 1024 * 1024


def _clases():
    from ..nucleo.perfiles import Perfil
    from .ops_chapa import CuerpoChapa

    return {c.__name__: c for c in (EstadoModelo, Cuerpo, CuerpoChapa, BocetoResuelto,
                                   geo.Plano, Perfil, ResultadoSolver, Resultado3D)}


def _codificar(raiz, conservar=(), transporte=True):
    """Grafo JSON de `raiz`. En el trabajador (RS-X1), lo que el padre ya tiene viaja por su número: una forma con el
    mismo contenido no se vuelve a escribir y en el padre sigue siendo el mismo objeto (el visor no la vuelve a mallar);
    lo mismo las mallas, los bocetos resueltos y los planos, que los pasos comparten. Las dos puntas se quedan con lo de
    este envío y lo de los estados `conservar` (los que no viajaron porque no cambiaron): las tablas no crecen.
    Sin `transporte` (una previa, que no le deja nada al padre) esas tablas no se tocan."""
    from .documento import _igual

    clases = _clases()
    nodos, indices, retenidos, formas = [], {}, [], []
    enviadas, huellas = aislado.formas_enviadas if transporte else None, aislado.huellas_enviadas
    vigentes, cuerpos = {}, {}

    def compartir(v, nodo_nuevo):
        if enviadas is None:
            return nodo_nuevo()
        numero, huella, _ = enviadas.get(id(v), (None, None, None))
        if numero is None and consultas.es_forma(v):
            huella = intercambio.huella_visual(v)
            numero = huellas.get(huella)
        if numero is not None:
            vigentes[id(v)] = numero, huella, v
            return ["vieja", numero]
        numero = aislado.proxima_forma
        aislado.proxima_forma += 1
        vigentes[id(v)] = numero, huella, v
        return ["nueva", [numero, nodo_nuevo()]]

    def brep(v):
        formas.append(v)
        return ["brep", len(formas) - 1]

    def guardar(v):
        if isinstance(v, np.generic):
            v = v.item()
        if isinstance(v, float):         # también `parametros.Magnitud`: del otro lado alcanza con el número
            return float(v)
        if v is None or type(v) in (bool, int, str):
            return v
        if id(v) in indices:
            return {"ref": indices[id(v)]}
        i = indices[id(v)] = len(nodos)
        retenidos.append(v)              # impide reciclar ids de los diccionarios temporales de a_dict()
        nodos.append(None)
        if type(v) is dict:
            nodo = ["dict", [[guardar(k), guardar(x)] for k, x in v.items()]]
        elif type(v) in (list, tuple, set, frozenset):
            nodo = [type(v).__name__, [guardar(x) for x in v]]
        elif isinstance(v, np.ndarray):
            if v.dtype.hasobject or v.dtype.kind not in "biuf" or v.nbytes > _TOPE_BYTES:
                raise ValueError("El cálculo contiene un array no numérico o demasiado grande.")
            contenido = base64.b64encode(zlib.compress(v.tobytes(), 1)).decode("ascii")
            nodo = ["array", [v.dtype.str, list(v.shape), contenido]]
        elif consultas.es_forma(v):
            nodo = compartir(v, lambda: brep(v))
        elif isinstance(v, Boceto):
            nodo = ["boceto", guardar(v.a_dict())]
        elif type(v).__module__ == "omnicad.nucleo.malla" and type(v).__name__ == "Malla":
            nodo = compartir(v, lambda: ["malla", guardar(v.a_dict())])
        elif type(v) in (BocetoResuelto, geo.Plano):
            nodo = compartir(v, lambda: [type(v).__name__, guardar(vars(v))])
        elif type(v) is Cuerpo and (igual := next((c for c in cuerpos.get(id(v.forma), ())
                                                   if _igual(vars(c), vars(v))), None)) is not None:
            nodo = ["copia", guardar(igual)]     # cada estado tiene su copia del cuerpo: el mismo dato no viaja mil veces
        elif clases.get(type(v).__name__) is type(v):
            if type(v).__name__ == "Perfil":
                _ = v.cara               # materializar la fábrica de geometría también dentro del hijo
            elif type(v) is Cuerpo:
                cuerpos.setdefault(id(v.forma), []).append(v)
            nodo = [type(v).__name__, guardar(vars(v))]
        else:
            raise ValueError(f"El resultado aislado contiene un tipo no admitido: {type(v).__name__}.")
        nodos[i] = nodo
        return {"ref": i}

    inicio = guardar(raiz)
    grafo = {"version": 1, "raiz": inicio, "nodos": nodos,
             "brep": intercambio.brep_a_texto(geo.compuesto(formas), 1) if formas else None}
    if enviadas is not None:
        for estado in conservar:
            for o in (*(c.forma for c in estado.cuerpos.values()), *estado.bocetos.values(), *estado.planos.values()):
                if id(o) in enviadas:
                    vigentes.setdefault(id(o), enviadas[id(o)])
        retiradas = {n for n, _, _ in enviadas.values()} - {n for n, _, _ in vigentes.values()}
        aislado.formas_enviadas = vigentes
        aislado.huellas_enviadas = {h: n for n, h, _ in vigentes.values() if h is not None}
        aislado.marca_enviada = f"{os.getpid()}.{aislado.proxima_forma}"
        grafo.update(marca=aislado.marca_enviada, parcial=bool(enviadas), retiradas=sorted(retiradas))
    return grafo


def _decodificar(grafo):
    if not isinstance(grafo, dict) or grafo.get("version") != 1 or not isinstance(grafo.get("nodos"), list):
        raise ValueError("El hijo no entregó un resultado de cálculo válido.")
    clases, nodos, hechos, pendientes = _clases(), grafo["nodos"], {}, set()
    if len(nodos) > 1_000_000:
        raise ValueError("El resultado del cálculo tiene demasiados objetos.")
    formas = ([intercambio.convertir_forma(f) for f in consultas.hijos_compuesto(intercambio.forma_de_texto(grafo["brep"]))]
              if grafo.get("brep") else [])
    vigentes = {}

    def leer(v):
        if v is None or type(v) in (bool, int, float, str):
            return v
        if not isinstance(v, dict) or set(v) != {"ref"}:
            raise ValueError("Referencia inválida en el resultado del cálculo.")
        i = v["ref"]
        if type(i) is not int or not 0 <= i < len(nodos) or i in pendientes:
            raise ValueError("Referencia circular o fuera del resultado del cálculo.")
        if i in hechos:
            return hechos[i]
        pendientes.add(i)
        salida = construir(*nodos[i])
        hechos[i] = salida
        pendientes.remove(i)
        return salida

    def construir(tipo, datos):
        if tipo == "dict":
            salida = {leer(k): leer(x) for k, x in datos}
        elif tipo in ("list", "tuple", "set", "frozenset"):
            salida = {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[tipo](leer(x) for x in datos)
        elif tipo == "array":
            nombre, forma, contenido = datos
            dtype = np.dtype(nombre)
            if (dtype.hasobject or dtype.kind not in "biuf" or len(forma) > 32
                    or any(type(n) is not int or n < 0 for n in forma)):
                raise ValueError("Array inválido en el resultado del cálculo.")
            cantidad = math.prod(forma) * dtype.itemsize
            if cantidad > _TOPE_BYTES:
                raise ValueError("El array del cálculo supera el límite de memoria.")
            descompresor = zlib.decompressobj()
            bruto = descompresor.decompress(base64.b64decode(contenido, validate=True), cantidad + 1)
            if len(bruto) != cantidad or not descompresor.eof:
                raise ValueError("El array del cálculo está incompleto o supera el tamaño declarado.")
            salida = np.frombuffer(bruto, dtype).copy().reshape(forma)
        elif tipo == "brep":
            if type(datos) is not int or not 0 <= datos < len(formas):
                raise ValueError("Forma fuera del BREP del cálculo.")
            salida = formas[datos]
        elif tipo == "vieja":
            if datos not in aislado.formas_recibidas:
                raise ValueError("El resultado del cálculo nombra un objeto que este proceso no tiene.")
            salida = vigentes[datos] = aislado.formas_recibidas[datos]
        elif tipo == "nueva":
            salida = vigentes[datos[0]] = construir(*datos[1])
        elif tipo == "copia":
            salida = leer(datos).copia()
        elif tipo == "boceto":
            salida = Boceto.desde_dict(leer(datos))
        elif tipo == "malla":
            from ..nucleo.malla import Malla
            salida = Malla.desde_dict(leer(datos))
        elif tipo in clases:
            salida = clases[tipo].__new__(clases[tipo])
            vars(salida).update(leer(datos))
        else:
            raise ValueError(f"Tipo no admitido en el resultado del cálculo: {tipo}.")
        return salida

    raiz = leer(grafo["raiz"])
    if "marca" in grafo:
        tabla = dict(aislado.formas_recibidas) if grafo["parcial"] else {}
        for numero in grafo["retiradas"]:
            tabla.pop(numero, None)
        tabla.update(vigentes)
        aislado.formas_recibidas, aislado.marca_recibida = tabla, grafo["marca"]
    return raiz


def _empaquetar(doc, previa=None, mallar=None):
    """El cálculo de `doc` para el padre. En el trabajador no viajan los estados del principio que no cambiaron desde
    la respuesta anterior: una edición cuesta por los pasos que siguen, no por todo el historial. `mallar` ((deflexión,
    ángulo) del visor, ver `aislado.MALLAR`): también la malla de los cuerpos finales que el padre todavía no tiene."""
    estados, iguales = doc._estados, 0
    if aislado.formas_enviadas:                  # vacía: el padre no tiene la respuesta anterior
        previos = aislado.estados_enviados
        while iguales < min(len(previos), len(estados)) and previos[iguales] is estados[iguales]:
            iguales += 1
    datos = {"estados": estados[iguales:], "iguales": iguales,
             "resultados": [(r.estado, r.mensaje) for r in doc.resultados], "usados": doc._usados,
             "valores": doc._valores, "duraciones": doc._duraciones,
             "efectos_boceto": [(o.rehechas, o.perdidas, o._textos_parametricos) if isinstance(o, OpBoceto) else None
                                for o in doc.operaciones],
             "dependencias": [o._usados for o in doc.operaciones], "previa": previa}
    if mallar is not None and previa is None:   # B-337: OCC no suelta el GIL; mallar un cuerpo de un STEP trababa 28 s
        from ..nucleo.render_cpu import es_malla
        tiene = aislado.formas_enviadas or {}
        datos["mallas"] = {cid: _malla(c.forma, *mallar) for cid, c in doc.estado_final.cuerpos.items()
                           if id(c.forma) not in tiene and not es_malla(c.forma)}
    salida = {"errores": sum(r.estado == "error" for r in doc.resultados), "pasos": len(doc.operaciones),
              "cuerpos": len(doc.estado_final.cuerpos), "receta": doc.a_dict(), "calculo": _codificar(datos, estados[:iguales])}
    if aislado.formas_enviadas is not None:
        aislado.estados_enviados = list(estados)
    return salida


def _malla(forma, deflexion, angular):
    """(vértices, normales, aristas) de un cuerpo como los arma el visor (`Visor3D.datos_cuerpo`), hechos en el hijo."""
    from ..nucleo import render_cpu
    # FL-9: con el detalle «Automático» (None) malla como el visor; 0,05 mm fijos tardaban 5 s en un barrido con guía
    d = render_cpu.deflexion_automatica(forma) if deflexion is None else deflexion
    v, n = render_cpu.malla_suave(forma, d, angular)
    # B-432: un cuerpo de malla no tiene aristas OCC (el visor dibuja las suyas al aceptar)
    pares = [] if render_cpu.es_malla(forma) else [np.repeat(p, 2, axis=0)[1:-1] for p in geo.polilineas_aristas(forma) if len(p) >= 2]
    return v, n, np.concatenate(pares).astype(np.float32) if pares else np.zeros((0, 3), np.float32)


def previa_visual(receta, operacion, indice, deflexion, angular, formas=False):
    """Previa exacta y su malla dentro del hijo; al padre viajan solo arrays de los cuerpos cambiados. `formas`: también
    su B-Rep, para el comando que resalta caras sobre la previa (P-78 con P-145: las crestas de la rosca)."""
    from .operaciones import operacion_desde_dict

    doc = aislado._documento(receta)
    entrada = doc.estado_en(doc.marcador if indice is None else indice)
    op = operacion_desde_dict(operacion)
    inicio = time.perf_counter()
    estado, avisos = doc.previsualizar(op, indice, en_vivo=True)
    mallas, nuevos, enviar = {}, {}, {}
    for cid, c in estado.cuerpos.items():
        anterior = entrada.cuerpos.get(cid)
        if anterior is not None and c.forma is anterior.forma:
            continue
        if anterior is None:       # un patrón o una copia: el padre arma el cuerpo con sus datos y esta malla
            nuevos[cid] = [c.nombre, c.op_id, c.tipo, c.apariencia, c.material, c.componente, list(c.origen)]
        mallas[cid] = _malla(c.forma, deflexion, angular)
        if formas:
            enviar[cid] = c.forma
    # FL-1: lo que costaría en la ventana (kernel y malla), sin rehacer el documento. FL-1b: mallar un barrido tarda 0,4 s
    ms = (time.perf_counter() - inicio) * 1000
    return _codificar({"mallas": mallas, "nuevos": nuevos, "avisos": list(avisos), "cuerpos": list(estado.cuerpos),
                       "formas": enviar, "ms": ms}, transporte=False)


def solape_herramienta(receta, operacion, indice, cuerpos):
    """¿El cuerpo nuevo de `operacion` comparte volumen con alguno de `cuerpos`? Para cuerpos pesados (B-117)."""
    from ..nucleo import geometria as geo
    from .operaciones import operacion_desde_dict

    doc = aislado._documento(receta)
    entrada = doc.estado_en(doc.marcador if indice is None else indice)
    estado, _ = doc.previsualizar(operacion_desde_dict(operacion), indice, en_vivo=True)
    formas = [c.forma for k, c in estado.cuerpos.items() if k not in entrada.cuerpos]
    return {"solapa": any(geo.solapan(f, entrada.cuerpos[c].forma) for f in formas for c in cuerpos)}


def leer_previa_visual(salida, entrada):
    """Estado efímero de dibujo: ninguna malla entra en el timeline ni en la memoria de aceptación."""
    from ..nucleo.malla import Malla
    datos = _decodificar(salida)
    estado = entrada.copia()
    for cid, (nombre, op_id, tipo, apariencia, material, componente, origen) in datos["nuevos"].items():
        estado.cuerpos[cid] = Cuerpo(cid, nombre, None, op_id, tipo, apariencia, material, componente, origen)
    estado.cuerpos = {cid: estado.cuerpos[cid] for cid in datos["cuerpos"]}
    preparadas, formas = {}, datos.get("formas") or {}
    for cid, (v, n, seg) in datos["mallas"].items():
        c = estado.cuerpos[cid]
        c.forma = formas[cid] if cid in formas else Malla(v, np.arange(len(v)).reshape(-1, 3))
        preparadas[cid] = v, n, seg
    estado._mallas_previa = preparadas
    estado._origen_previa = entrada
    estado._ms_previa = datos.get("ms", math.inf)
    return estado, datos["avisos"]


def _leer_calculo(salida):
    try:
        datos = _decodificar(salida["calculo"])
        datos["receta"], datos["parcial"] = salida["receta"], salida["calculo"].get("parcial", False)
        datos["estados"] = aislado.estados_recibidos[:datos["iguales"]] + datos["estados"]
        if "marca" in salida["calculo"]:
            aislado.estados_recibidos = list(datos["estados"])    # B-503: el documento adopta esa lista y la recorta al recalcular
        n = len(datos["receta"]["operaciones"])
        if any(len(datos[k]) != n for k in ("estados", "resultados", "usados", "duraciones", "dependencias", "efectos_boceto")):
            raise ValueError("El cálculo recibido tiene pasos incompletos.")
        for op, efectos in zip(datos["receta"]["operaciones"], datos["efectos_boceto"], strict=True):
            if op["tipo"] == OpBoceto.TIPO and (not isinstance(efectos, tuple)
                                              or tuple(type(v) for v in efectos) != (dict, list, dict)
                                              or not all(isinstance(k, int) and isinstance(v, tuple) and len(v) == 2
                                                         for k, v in efectos[0].items())):
                raise ValueError("El cálculo recibido tiene atributos de boceto inválidos.")
        if not all(isinstance(e, EstadoModelo) for e in datos["estados"]):
            raise ValueError("El cálculo recibido tiene estados inválidos.")
        if any(r[0] not in ("ok", "aviso", "error", "suprimida", "retrocedida") for r in datos["resultados"]):
            raise ValueError("El cálculo recibido tiene resultados inválidos.")
        marcador = datos["receta"].get("marcador", n)
        if datos.get("mallas") and marcador:     # B-337: las hizo el hijo; la ventana no malla (`Visor3D.datos_cuerpo`)
            datos["estados"][marcador - 1]._mallas_hijo = datos["mallas"]
        return datos
    except (KeyError, IndexError, TypeError, AttributeError, zlib.error, RecursionError) as e:
        raise ValueError(f"El hijo no entregó un resultado de cálculo completo ({e}).") from e
