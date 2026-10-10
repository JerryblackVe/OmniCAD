# -*- coding: utf-8 -*-
"""
Documento paramétrico con timeline.

Equivalencias con Fusion 360 (informe_analisis.md §3.3):
  - Timeline.markerPosition      →  Documento.marcador (pasos activos = operaciones[:marcador])
  - TimelineObject.rollTo        →  Documento.mover_marcador(indice)
  - TimelineObject.isSuppressed  →  Documento.suprimir(id, True/False)
  - TimelineObject.reorder       →  Documento.mover(id, nuevo_indice) (valida dependencias, como canReorder)
  - TimelineObject.healthState   →  ResultadoPaso.estado: ok / aviso / error / suprimida / retrocedida
                                    (FeatureHealthStates: Healthy, Warning, Error, Suppressed, RolledBack)
  - Design.computeAll            →  Documento.recalcular()

Recalcular reutiliza el estado guardado de cada paso: si se edita el paso i, solo se
recalculan los pasos desde i en adelante. Al cambiar parámetros, se recalcula desde el primer paso
que LEYÓ un parámetro cuyo valor cambió (cada paso anota lo que lee al ejecutarse).

Abrir un proyecto no recalcula los pasos lentos (como Fusion, que abre con la geometría guardada): el proyecto
guarda el resultado de los pasos que tardaron al menos `_SEGUNDOS_CACHE` (`pasos_para_cache`) y `desde_dict(datos,
cache)` los toma de ahí en vez de ejecutarlos. Los demás pasos se calculan como siempre, y editar recalcula normal.
"""
import json
import logging
import time
import traceback

from OCP.TopoDS import TopoDS_Shape

from ..nucleo.geometria import ErrorGeometria
from ..restricciones import ErrorBoceto
from .entidades import ErrorReferencia
from .operaciones import (HEREDABLES, TIPOS_OPERACION, Contexto, Cuerpo, ErrorOperacion, EstadoModelo,
                          operacion_desde_dict, propiedades_cuerpo)
from .parametros import ErrorExpresion, TablaParametros, nombres_usados

log = logging.getLogger(__name__)

VERSION_RECETA = 1
_LIMITE_DESHACER = 50
_LIMITE_BYTES_DESHACER = 150_000_000   # un STEP importado viaja en cada instantánea: se acota la memoria
# Un paso que tarda al menos esto guarda su resultado con el proyecto: al abrirlo no se recalcula. Los más rápidos
# se recalculan (guardarlos agrandaría el archivo sin ganar casi nada de tiempo).
_SEGUNDOS_CACHE = 0.1
_CAMPOS_CUERPO = ("nombre", "op_id", "tipo", "apariencia", "material", "componente")


class ErrorDocumento(ValueError):
    pass


def _igual(a, b):
    """¿Dos valores de estados del modelo son iguales sin recalcular nada? Los objetos (formas, bocetos resueltos,
    planos) solo si son el MISMO; los dicts, listas, tuplas y valores simples, por contenido."""
    if a is b:
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(_igual(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and type(a) is type(b):
        return len(a) == len(b) and all(_igual(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (str, int, float, bool)) and type(a) is type(b):
        return a == b
    return False


def _cambios_de_cuerpos(antes, despues):
    """Lo que hizo un paso (de `antes` a `despues`) si solo cambió cuerpos que la caché del proyecto puede guardar:
    ([[id, None si es el mismo de antes | sus datos]] en el orden del estado, formas de los cuerpos cambiados).
    None si cambió otra cosa (bocetos, planos, componentes…) o un cuerpo que no va en un BREP (malla, chapa)."""
    va, vd = vars(antes), vars(despues)
    if list(va) != list(vd) or not all(_igual(va[k], vd[k]) for k in va if k not in ("cuerpos", "contador_cuerpos")):
        return None
    lista, formas = [], []
    for cid, c in despues.cuerpos.items():
        previo = antes.cuerpos.get(cid)
        if previo is not None and type(c) is type(previo) and _igual(vars(c), vars(previo)):
            lista.append([cid, None])
            continue
        datos = {k: getattr(c, k) for k in _CAMPOS_CUERPO}
        try:
            se_guarda = json.loads(json.dumps(datos)) == datos
        except (TypeError, ValueError):
            se_guarda = False
        if (not se_guarda or type(c) is not Cuerpo or set(vars(c)) != {"id", "forma", "origen", *_CAMPOS_CUERPO}
                or c.tipo == "malla" or not isinstance(c.forma, TopoDS_Shape) or c.forma.IsNull()):
            return None
        lista.append([cid, datos])
        formas.append(c.forma)
    return lista, formas


def _migrar(d):
    """Un paso de una receta leída (archivo, receta aplicada o diseño insertado): si su operación cambió de
    cálculo, `migrar_receta` le completa lo que le falta para que se calcule como antes (p. ej. las uniones
    sin «version_marco»)."""
    tipo = d.get("tipo") if isinstance(d, dict) else None
    migrar = getattr(TIPOS_OPERACION.get(tipo) if isinstance(tipo, str) else None, "migrar_receta", None)
    return migrar(d) if migrar else d


class ResultadoPaso:
    def __init__(self, estado, mensaje=""):
        self.estado, self.mensaje = estado, mensaje

    def __repr__(self):
        return f"ResultadoPaso({self.estado!r}, {self.mensaje!r})"


class Documento:
    def __init__(self):
        self.nombre = "Sin título"
        self.ruta = None
        self.parametros = TablaParametros()
        self.operaciones = []
        self.marcador = 0
        self.resultados = []
        self._estados = []
        self._usados = []         # por paso: nombres de parámetros que leyó en el último cálculo
        self._valores = None      # valores de los parámetros con los que se hizo el último cálculo
        self._duraciones = []     # por paso: segundos que tardó su último cálculo (0 si no se ejecutó)
        self._cache = {}          # solo mientras `desde_dict` abre un proyecto: índice → (datos, formas) guardados
        self._contador = 0
        self.modificado = False
        self._oyentes = []
        self._deshacer, self._rehacer = [], []
        # Vistas guardadas (navegador › Vistas guardadas): nombre → cámara. Son datos del documento
        # (se guardan en el proyecto) pero no pasos del timeline: no entran en deshacer.
        self.vistas = {}
        # Datos de los otros espacios de trabajo (dibujo, render, animación): clave → dict de su ventana.
        # Como las vistas guardadas, se guardan con el proyecto pero no son pasos del timeline.
        self.espacios = {}
        # Comentarios del diseño (panel COMENTARIOS de Fusion): [{"texto", "fecha"}]. Se guardan con el proyecto.
        self.comentarios = []
        # Propiedades de cuerpos que en Fusion no son pasos del timeline (aspecto, material físico,
        # nombre, opacidad): id de cuerpo → {"apariencia": [r, g, b], "material": nombre, …}. Entran en
        # deshacer y se guardan con el proyecto.
        self.propiedades = {}
        # Análisis guardados en el navegador (sección, cebra, curvatura…): nombre → {"tipo", "params",
        # "visible"}. Como en Fusion, no son pasos del timeline pero se guardan con el diseño.
        self.analisis = {}
        # Tabla de configuraciones (CONFIGURAR): {"columnas": [{"tipo": "parametro", "nombre"} |
        # {"tipo": "suprimir", "op"}], "filas": [{"nombre", "valores"}], "activa": nombre}.
        self.configuraciones = {}

    # ------------------------------------------------------------ notificación
    def suscribir(self, funcion):
        self._oyentes.append(funcion)

    def _notificar(self):
        for f in list(self._oyentes):
            f()

    # ------------------------------------------------------------ consultas
    def nuevo_id(self):
        self._contador += 1
        ids = {o.id for o in self.operaciones}
        while f"op{self._contador}" in ids:
            self._contador += 1
        return f"op{self._contador}"

    def indice(self, op_id):
        for i, o in enumerate(self.operaciones):
            if o.id == op_id:
                return i
        raise ErrorDocumento(f"No existe la operación '{op_id}'.")

    def operacion(self, op_id):
        return self.operaciones[self.indice(op_id)]

    def estado_en(self, indice):
        """Estado del modelo DESPUÉS de los primeros `indice` pasos (0 = vacío)."""
        indice = max(0, min(indice, len(self._estados)))
        return self._estados[indice - 1] if indice > 0 else EstadoModelo()

    @property
    def estado_final(self):
        return self.estado_en(self.marcador)

    def resultado(self, op_id):
        return self.resultados[self.indice(op_id)]

    def dependientes(self, op_id):
        return [o for o in self.operaciones if op_id in o.dependencias()]

    # ------------------------------------------------------------ deshacer / rehacer
    def _instantanea(self):
        return json.dumps(self.a_dict())

    def _guardar_para_deshacer(self):
        self._deshacer.append(self._instantanea())
        del self._deshacer[:-_LIMITE_DESHACER]
        while len(self._deshacer) > 1 and sum(len(s) for s in self._deshacer) > _LIMITE_BYTES_DESHACER:
            del self._deshacer[0]
        self._rehacer.clear()

    def puede_deshacer(self):
        return bool(self._deshacer)

    def puede_rehacer(self):
        return bool(self._rehacer)

    def deshacer(self):
        if not self._deshacer:
            return
        self._rehacer.append(self._instantanea())
        self._cargar(json.loads(self._deshacer.pop()))

    def rehacer(self):
        if not self._rehacer:
            return
        self._deshacer.append(self._instantanea())
        self._cargar(json.loads(self._rehacer.pop()))

    def _cargar(self, datos):
        self.parametros = TablaParametros.desde_lista(datos.get("parametros"))
        self.propiedades = {k: dict(v) for k, v in (datos.get("propiedades") or {}).items()}
        self.analisis = {k: dict(v) for k, v in (datos.get("analisis") or {}).items()}
        self.configuraciones = dict(datos.get("configuraciones") or {})
        self.operaciones = [operacion_desde_dict(_migrar(d)) for d in datos.get("operaciones", [])]
        self.marcador = min(datos.get("marcador", len(self.operaciones)), len(self.operaciones))
        self._contador = datos.get("contador", len(self.operaciones))
        self.modificado = True
        self.recalcular(0)

    # ------------------------------------------------------------ edición del timeline
    def agregar(self, op):
        """Inserta la operación en la posición del marcador (como Fusion) y la ejecuta."""
        self._guardar_para_deshacer()
        i = self.marcador
        self.operaciones.insert(i, op)
        self.marcador += 1
        self.modificado = True
        self.recalcular(i)
        return self.resultados[i]

    def reemplazar(self, op_id, nueva):
        """Edita un paso: la nueva versión conserva el id (las referencias siguen valiendo)."""
        self._guardar_para_deshacer()
        i = self.indice(op_id)
        nueva.id = op_id
        self.operaciones[i] = nueva
        self.modificado = True
        self.recalcular(i)
        return self.resultados[i]

    def set_propiedad(self, ids_cuerpos, clave, valor):
        """Aspecto, material, nombre u opacidad de uno o más cuerpos (None borra la sustitución)."""
        self._guardar_para_deshacer()
        for cid in ids_cuerpos:
            props = self.propiedades.setdefault(cid, {})
            if valor is None:
                props.pop(clave, None)
            else:
                props[clave] = valor
            if not props:
                del self.propiedades[cid]
        self.modificado = True
        if clave == "nombre":
            self._renombrar_cuerpos(ids_cuerpos, valor)
        self._notificar()

    def _nombres_cuerpos(self):
        """{id de cuerpo: nombre} de los cuerpos renombrados en el navegador."""
        return {cid: p["nombre"] for cid, p in self.propiedades.items() if p.get("nombre")}

    def _poner_nombres(self, estado, nombres):
        """Una sola fuente de verdad para el nombre: `Cuerpo.nombre` refleja el renombre (como en Fusion, donde el
        nombre del navegador ES el del cuerpo). El nombre sigue guardado en `propiedades`: la receta no cambia."""
        for cid, nombre in nombres.items():
            c = estado.cuerpos.get(cid)
            if c is not None:
                c.nombre = nombre

    def _renombrar_cuerpos(self, ids_cuerpos, valor):
        if valor:                   # el nombre nuevo va a todos los estados ya calculados, sin recalcular geometría
            nombres = self._nombres_cuerpos()
            for estado in self._estados:
                self._poner_nombres(estado, nombres)
            return
        # Se quitó el renombre: el nombre original lo pone la operación que creó el cuerpo (op3.c1 → op3).
        indices = [i for i, o in enumerate(self.operaciones) for cid in ids_cuerpos if cid.split(".c")[0] == o.id]
        self.recalcular(min(indices, default=0))

    def propiedad(self, cid, clave, defecto=None):
        """Propiedad `clave` del cuerpo `cid`; el aspecto, el acabado y el material se heredan del original si
        el cuerpo es una copia sin valor propio (`operaciones.propiedades_cuerpo`)."""
        if clave in HEREDABLES:
            cuerpo = self.estado_final.cuerpos.get(cid)
            if cuerpo is not None:
                return propiedades_cuerpo(self.propiedades, cuerpo).get(clave, defecto)
        return self.propiedades.get(cid, {}).get(clave, defecto)

    def agregar_analisis(self, tipo, params, nombre=None):
        """Guarda un análisis en el navegador (Sección1, Cebra1…). Devuelve su nombre."""
        self._guardar_para_deshacer()
        if nombre is None:
            base = {"seccion": "Sección", "cebra": "Cebra", "mapa_entorno": "Mapa de entorno",
                    "desmoldeo": "Desmoldeo", "curvatura": "Curvatura", "peine": "Peine de curvatura",
                    "isocurva": "Isocurva", "accesibilidad": "Accesibilidad",
                    "radio_minimo": "Radio mínimo"}.get(tipo, tipo)
            n = 1
            while f"{base}{n}" in self.analisis:
                n += 1
            nombre = f"{base}{n}"
        self.analisis[nombre] = {"tipo": tipo, "params": params, "visible": True}
        self.modificado = True
        self._notificar()
        return nombre

    def aplicar_configuracion(self, datos, activa=None):
        """Guarda la tabla de configuraciones y activa una fila: sus parámetros y supresiones se aplican de
        una vez (un solo deshacer y un solo recálculo)."""
        datos = dict(datos)
        activa = activa if activa is not None else datos.get("activa", "")
        fila = next((f for f in datos.get("filas", []) if f["nombre"] == activa), None)
        tabla = TablaParametros.desde_lista(self.parametros.a_lista())
        supresiones = {}
        if fila is not None:
            for col, valor in zip(datos.get("columnas", []), fila["valores"], strict=False):
                if col["tipo"] == "parametro" and col["nombre"] in tabla and str(valor).strip():
                    tabla.modificar(col["nombre"], str(valor).strip())
                elif col["tipo"] == "suprimir":
                    supresiones[col["op"]] = str(valor).strip().lower() in ("sí", "si", "1", "true", "x", "s")
        tabla.valores()                                # valida antes de tocar el documento
        self._guardar_para_deshacer()
        self.configuraciones = dict(datos, activa=activa)
        desde = self._primer_afectado(tabla)
        self.parametros = tabla
        for i, op in enumerate(self.operaciones):
            if op.id in supresiones and op.suprimida != supresiones[op.id]:
                op.suprimida = supresiones[op.id]
                desde = min(desde, i)
        self.modificado = True
        self.recalcular(desde)

    def quitar_analisis(self, nombre):
        if nombre in self.analisis:
            self._guardar_para_deshacer()
            del self.analisis[nombre]
            self.modificado = True
            self._notificar()

    def alternar_analisis(self, nombre):
        if nombre in self.analisis:
            self.analisis[nombre]["visible"] = not self.analisis[nombre].get("visible", True)
            self.modificado = True
            self._notificar()

    def renombrar(self, op_id, nombre):
        self._guardar_para_deshacer()
        self.operacion(op_id).nombre = nombre
        self.modificado = True
        self._notificar()

    def suprimir(self, op_id, suprimida=True):
        self._guardar_para_deshacer()
        i = self.indice(op_id)
        self.operaciones[i].suprimida = suprimida
        self.modificado = True
        self.recalcular(i)

    def eliminar(self, op_id):
        i = self.indice(op_id)
        deps = self.dependientes(op_id)
        if deps:
            raise ErrorDocumento("No se puede eliminar: la usan " + ", ".join(d.nombre for d in deps) + ".")
        self._guardar_para_deshacer()
        del self.operaciones[i]
        if i < self.marcador:
            self.marcador -= 1
        self.modificado = True
        self.recalcular(i)

    def puede_mover(self, op_id, nuevo_indice):
        """Como TimelineObject.canReorder: un paso no puede quedar antes de lo que usa ni después de quien lo usa."""
        i = self.indice(op_id)
        nuevo_indice = max(0, min(nuevo_indice, len(self.operaciones) - 1))
        op = self.operaciones[i]
        resto = self.operaciones[:i] + self.operaciones[i + 1:]
        antes = {o.id for o in resto[:nuevo_indice]}
        if not op.dependencias() <= antes:
            return False, "Quedaría antes de una operación que necesita."
        if any(op.id in o.dependencias() for o in resto[:nuevo_indice]):
            return False, "Quedaría después de una operación que depende de ella."
        return True, ""

    def mover(self, op_id, nuevo_indice):
        ok, motivo = self.puede_mover(op_id, nuevo_indice)
        if not ok:
            raise ErrorDocumento(motivo)
        self._guardar_para_deshacer()
        i = self.indice(op_id)
        nuevo_indice = max(0, min(nuevo_indice, len(self.operaciones) - 1))
        en_fin = self.marcador == len(self.operaciones)
        op = self.operaciones.pop(i)
        self.operaciones.insert(nuevo_indice, op)
        if en_fin:
            self.marcador = len(self.operaciones)
        self.modificado = True
        self.recalcular(min(i, nuevo_indice))

    def mover_marcador(self, posicion):
        posicion = max(0, min(posicion, len(self.operaciones)))
        if posicion == self.marcador:
            return
        anterior = self.marcador
        self.marcador = posicion
        self.recalcular(min(anterior, posicion))

    # ------------------------------------------------------------ parámetros
    def parametros_usados(self):
        """{nombre de parámetro: [pasos que lo usan]} recorriendo todas las expresiones del timeline."""
        usos = {}
        for op in self.operaciones:
            for expr in op.expresiones():
                for nombre in nombres_usados(expr):
                    usos.setdefault(nombre, set()).add(op.nombre)
        return usos

    def aplicar_parametros(self, tabla):
        tabla.valores()  # valida antes de tocar el documento
        faltan = {n: pasos for n, pasos in self.parametros_usados().items() if n in self.parametros and n not in tabla}
        if faltan:
            detalle = "; ".join(f"«{n}» (lo usa {', '.join(sorted(p))})" for n, p in sorted(faltan.items()))
            raise ErrorDocumento(f"No se puede quitar ni renombrar un parámetro en uso: {detalle}.")
        self._guardar_para_deshacer()
        desde = self._primer_afectado(tabla)
        self.parametros = tabla
        self.modificado = True
        self.recalcular(desde)

    def _primer_afectado(self, tabla):
        """Índice del primer paso que leyó un parámetro cuyo valor cambia con `tabla` (Fusion también
        recalcula solo lo que depende del cambio). Si ningún paso lo leyó, len(operaciones): nada que rehacer."""
        if self._valores is None:
            return 0
        try:
            nuevos = tabla.valores()
        except ErrorExpresion:
            nuevos = {}
        viejos = self._valores
        cambiados = {n for n in viejos.keys() | nuevos.keys() if viejos.get(n) != nuevos.get(n)}
        for i, usados in enumerate(self._usados):
            if usados & cambiados:
                return i
        return len(self._usados)

    # ------------------------------------------------------------ cálculo
    def previsualizar(self, op, indice=None):
        """Ejecuta `op` sobre una COPIA del estado en `indice` (por defecto, el marcador) sin tocar el
        documento: es la vista previa de los diálogos de comando. Devuelve (estado, avisos); los errores
        de la operación se propagan para que el diálogo los muestre."""
        indice = self.marcador if indice is None else indice
        estado = self.estado_en(indice).copia()
        try:
            valores = self.parametros.valores()
        except ErrorExpresion:
            valores = {}
        ctx = Contexto(valores)
        op.calcular(estado, ctx)
        return estado, ctx.avisos

    def recalcular(self, desde=0):
        desde = max(0, min(desde, len(self._estados), len(self.resultados)))
        desde = min(desde, len(self._usados), len(self._duraciones))
        del self._estados[desde:]
        del self.resultados[desde:]
        del self._usados[desde:]
        del self._duraciones[desde:]
        try:
            valores = self.parametros.valores()
        except ErrorExpresion as e:
            valores = {}
            log.warning("Parámetros inválidos: %s", e)
        self._valores = valores
        nombres = self._nombres_cuerpos()
        estado = self.estado_en(desde)
        for i in range(desde, len(self.operaciones)):
            op = self.operaciones[i]
            usados = frozenset()
            duracion = 0.0
            guardado = self._de_cache(i, op, estado) if i < self.marcador and not op.suprimida else None
            if i >= self.marcador:
                self.resultados.append(ResultadoPaso("retrocedida"))
            elif op.suprimida:
                self.resultados.append(ResultadoPaso("suprimida"))
            elif guardado is not None:
                estado, resultado, usados, duracion = guardado
                self.resultados.append(resultado)
            else:
                nuevo = estado.copia()
                ctx = Contexto(valores)
                usados = ctx.usados
                inicio = time.perf_counter()
                try:
                    op.calcular(nuevo, ctx)
                    estado = nuevo
                    if ctx.avisos:
                        self.resultados.append(ResultadoPaso("aviso", " ".join(ctx.avisos)))
                    else:
                        self.resultados.append(ResultadoPaso("ok"))
                except (ErrorOperacion, ErrorGeometria, ErrorExpresion, ErrorBoceto, ErrorReferencia) as e:
                    self.resultados.append(ResultadoPaso("error", str(e)))
                except Exception as e:  # noqa: BLE001 — un fallo del kernel no debe tumbar la app
                    log.error("Error inesperado en %s:\n%s", op.id, traceback.format_exc())
                    self.resultados.append(ResultadoPaso("error", f"Error inesperado: {e}"))
                duracion = time.perf_counter() - inicio
            self._poner_nombres(estado, nombres)   # antes del paso siguiente: la copia de «Placa» sale «Placa (copia)»
            self._estados.append(estado)
            self._usados.append(usados)
            self._duraciones.append(duracion)
        self._notificar()

    # ------------------------------------------------------------ caché de pasos lentos (abrir sin recalcular)
    def pasos_para_cache(self, minimo=None):
        """Lo que el proyecto guarda para abrir sin recalcular (`proyecto.guardar`): [(datos, formas)] de los pasos
        activos que tardaron al menos `minimo` segundos (por defecto `_SEGUNDOS_CACHE`), terminaron bien (ok o
        aviso) y solo cambiaron cuerpos sólidos o superficies. `datos` es JSON; `formas`, las formas de los cuerpos
        que el paso creó o cambió, en el orden de `datos["cuerpos"]`."""
        minimo = _SEGUNDOS_CACHE if minimo is None else minimo
        pasos = []
        for i in range(min(self.marcador, len(self._estados), len(self._duraciones))):
            op, resultado = self.operaciones[i], self.resultados[i]
            if op.suprimida or resultado.estado not in ("ok", "aviso") or self._duraciones[i] < minimo:
                continue
            despues = self.estado_en(i + 1)
            cambios = _cambios_de_cuerpos(self.estado_en(i), despues)
            if cambios is None:
                continue
            cuerpos, formas = cambios
            pasos.append(({"indice": i, "op": op.id, "estado": resultado.estado, "mensaje": resultado.mensaje,
                           "usados": sorted(self._usados[i]), "dependencias": sorted(op._usados),
                           "contador": despues.contador_cuerpos, "duracion": self._duraciones[i],
                           "cuerpos": cuerpos}, formas))
        return pasos

    def _de_cache(self, i, op, estado):
        """El paso i tomado de la caché del proyecto que se está abriendo, sin ejecutarlo: (estado, resultado,
        parámetros que leyó, duración). None si no está guardado o no cuadra con `estado` (entonces se ejecuta)."""
        guardado = self._cache.get(i)
        if guardado is None:
            return None
        datos, formas = guardado
        try:
            if datos["op"] != op.id or datos["estado"] not in ("ok", "aviso"):
                return None
            nuevo = estado.copia()
            cuerpos, propias = {}, iter(formas)
            for cid, m in datos["cuerpos"]:
                if m is None:
                    cuerpos[cid] = nuevo.cuerpos[cid]
                else:
                    cuerpos[cid] = Cuerpo(cid, m["nombre"], next(propias), m["op_id"], m["tipo"], m["apariencia"],
                                          m["material"], m["componente"])
            if next(propias, None) is not None:
                return None
            nuevo.cuerpos = cuerpos
            nuevo.contador_cuerpos = int(datos["contador"])
            resultado = ResultadoPaso(datos["estado"], str(datos["mensaje"]))
            usados, duracion, dependencias = set(datos["usados"]), float(datos["duracion"]), set(datos["dependencias"])
        except (KeyError, TypeError, ValueError, StopIteration):
            return None
        op._usados = dependencias       # lo que fija `ejecutar`: sin esto se podría mover o borrar lo que usa el paso
        return nuevo, resultado, usados, duracion

    # ------------------------------------------------------------ comentarios (panel COMENTARIOS)
    def agregar_comentario(self, texto):
        from datetime import datetime
        self.comentarios.append({"texto": str(texto), "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")})
        self.modificado = True
        self._notificar()

    def borrar_comentario(self, indice):
        if 0 <= indice < len(self.comentarios):
            del self.comentarios[indice]
            self.modificado = True
            self._notificar()

    # ------------------------------------------------------------ serialización (receta)
    def a_dict(self):
        return {"version_receta": VERSION_RECETA, "nombre": self.nombre,
                "parametros": self.parametros.a_lista(), "marcador": self.marcador,
                "contador": self._contador, "operaciones": [o.a_dict() for o in self.operaciones],
                "vistas": self.vistas, "propiedades": self.propiedades, "analisis": self.analisis,
                "configuraciones": self.configuraciones,
                "espacios": self.espacios, "comentarios": self.comentarios}

    @classmethod
    def desde_dict(cls, datos, cache=None):
        """Documento desde una receta. `cache` ({índice de paso: (datos, formas)}, lo que guardó `pasos_para_cache`
        con ESTA misma receta) evita recalcular esos pasos; se usa solo para esta carga: después, editar recalcula."""
        version = datos.get("version_receta", 1)
        if version > VERSION_RECETA:
            raise ErrorDocumento(f"La receta es de una versión más nueva ({version}) que la soportada ({VERSION_RECETA}).")
        doc = cls()
        doc.nombre = datos.get("nombre", "Sin título")
        doc.vistas = dict(datos.get("vistas", {}))
        doc.espacios = dict(datos.get("espacios", {}))
        doc.comentarios = [dict(c) for c in datos.get("comentarios", [])]
        doc._cache = cache or {}
        try:
            doc._cargar(datos)
        finally:
            doc._cache = {}
        doc.modificado = False
        return doc
