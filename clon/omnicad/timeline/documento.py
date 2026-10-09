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
"""
import json
import logging
import traceback

from ..nucleo.geometria import ErrorGeometria
from ..restricciones import ErrorBoceto
from .operaciones import Contexto, ErrorOperacion, EstadoModelo, operacion_desde_dict
from .parametros import ErrorExpresion, TablaParametros, nombres_usados

log = logging.getLogger(__name__)

VERSION_RECETA = 1
_LIMITE_DESHACER = 50
_LIMITE_BYTES_DESHACER = 150_000_000   # un STEP importado viaja en cada instantánea: se acota la memoria


class ErrorDocumento(ValueError):
    pass


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
        self.operaciones = [operacion_desde_dict(d) for d in datos.get("operaciones", [])]
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
        self._notificar()

    def propiedad(self, cid, clave, defecto=None):
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
        op.ejecutar(estado, ctx)
        return estado, ctx.avisos

    def recalcular(self, desde=0):
        desde = max(0, min(desde, len(self._estados), len(self.resultados)))
        desde = min(desde, len(self._usados))
        del self._estados[desde:]
        del self.resultados[desde:]
        del self._usados[desde:]
        try:
            valores = self.parametros.valores()
        except ErrorExpresion as e:
            valores = {}
            log.warning("Parámetros inválidos: %s", e)
        self._valores = valores
        estado = self.estado_en(desde)
        for i in range(desde, len(self.operaciones)):
            op = self.operaciones[i]
            usados = frozenset()
            if i >= self.marcador:
                self.resultados.append(ResultadoPaso("retrocedida"))
            elif op.suprimida:
                self.resultados.append(ResultadoPaso("suprimida"))
            else:
                nuevo = estado.copia()
                ctx = Contexto(valores)
                usados = ctx.usados
                try:
                    op.ejecutar(nuevo, ctx)
                    estado = nuevo
                    if ctx.avisos:
                        self.resultados.append(ResultadoPaso("aviso", " ".join(ctx.avisos)))
                    else:
                        self.resultados.append(ResultadoPaso("ok"))
                except (ErrorOperacion, ErrorGeometria, ErrorExpresion, ErrorBoceto) as e:
                    self.resultados.append(ResultadoPaso("error", str(e)))
                except Exception as e:  # noqa: BLE001 — un fallo del kernel no debe tumbar la app
                    log.error("Error inesperado en %s:\n%s", op.id, traceback.format_exc())
                    self.resultados.append(ResultadoPaso("error", f"Error inesperado: {e}"))
            self._estados.append(estado)
            self._usados.append(usados)
        self._notificar()

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
    def desde_dict(cls, datos):
        version = datos.get("version_receta", 1)
        if version > VERSION_RECETA:
            raise ErrorDocumento(f"La receta es de una versión más nueva ({version}) que la soportada ({VERSION_RECETA}).")
        doc = cls()
        doc.nombre = datos.get("nombre", "Sin título")
        doc.vistas = dict(datos.get("vistas", {}))
        doc.espacios = dict(datos.get("espacios", {}))
        doc.comentarios = [dict(c) for c in datos.get("comentarios", [])]
        doc._cargar(datos)
        doc.modificado = False
        return doc
