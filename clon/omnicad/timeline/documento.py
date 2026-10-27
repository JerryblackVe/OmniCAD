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
import uuid
from .. import registro_uso
from ..registro_uso.ganchos import calculo as registrar_calculo

from ..nucleo import consultas
from ..nucleo import motor
from ..nucleo.geometria import ErrorGeometria
from ..restricciones import ErrorBoceto
from .entidades import ErrorReferencia
from .operaciones import (HEREDABLES, TIPOS_OPERACION, TODAS, Contexto, Cuerpo, ErrorOperacion, EstadoModelo, OpBoceto,
                          operacion_desde_dict, propiedades_cuerpo)
from .parametros import (ANGULO, LONGITUD, LONGITUDES, MASAS, ErrorExpresion, TablaParametros, evaluar,
                         nombres_usados, validar_nombre)

log = logging.getLogger(__name__)

VERSION_RECETA = 1
UNIDADES_DEFECTO = {"longitud": "mm", "masa": "g"}      # con qué se MUESTRAN las medidas; el modelo siempre va en mm y g
TOPE_INSTRUCCIONES = 4000   # caracteres de las instrucciones del asistente (las generales y las de cada proyecto)
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
    None si cambió otra cosa (bocetos, planos, componentes…) o un cuerpo que no va en un BREP (malla, chapa). Las
    herramientas anotadas (`EstadoModelo.herramientas`) no cuentan: no se guardan, y el paso cuya herramienta repite
    un patrón de operaciones se recalcula al abrir (`_pasos_repetidos`)."""
    va, vd = vars(antes), vars(despues)
    if list(va) != list(vd) or not all(_igual(va[k], vd[k]) for k in va
                                       if k not in ("cuerpos", "contador_cuerpos", "herramientas")):
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
                or c.tipo == "malla" or not consultas.es_forma(c.forma)):
            return None
        lista.append([cid, datos])
        formas.append(c.forma)
    return lista, formas


_FALTA = object()      # parámetro que un paso consultó y no existía


def _mismo_valor(a, b):
    """Igualdad de un valor del estado entre dos cálculos: los cuerpos se copian en cada paso, así que se comparan sus
    atributos (la forma, por identidad); lo demás, como `_igual`."""
    if isinstance(a, Cuerpo) and type(a) is type(b):
        return _igual(vars(a), vars(b))
    return _igual(a, b)


def _receta(op):
    """La receta del paso como texto (para saber si cambió desde su último cálculo); None si no se puede escribir."""
    try:
        return json.dumps(op.a_dict(), sort_keys=True)
    except (TypeError, ValueError):
        return None


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
        self.token = uuid.uuid4().hex[:8]   # autoguardado de los «Sin título»: un archivo por documento (B-22)
        self.parametros = TablaParametros()
        self.operaciones = []
        self.marcador = 0
        self.resultados = []
        self._estados = []
        self._usados = []         # por paso: nombres de parámetros que leyó en el último cálculo
        self._valores = None      # valores de los parámetros con los que se hizo el último cálculo
        self._duraciones = []     # por paso: segundos que tardó su último cálculo (0 si no se ejecutó)
        self.al_calcular = None   # función(op) que la ventana pone para avisar «Calculando…» antes de un paso que se ejecuta
        self._cache = {}          # solo mientras `desde_dict` abre un proyecto: índice → (datos, formas) guardados
        self._memo = {}           # id de paso → su último cálculo (ver `_de_memo`)
        self._previa = None       # la última vista previa calculada (ver `previsualizar` y `_de_previa`)
        self.motor = motor.motor_activo()
        self._contador = 0
        self._contador_cotas = 0
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
        # Unidades de pantalla del documento (cm, m, in, ft; kg, lb): solo cambian cómo se muestran las medidas. Como los
        # comentarios, se guardan con el proyecto (solo si no son las de siempre) pero no entran en deshacer.
        self.unidades = dict(UNIDADES_DEFECTO)
        # Instrucciones de este proyecto para el Asistente IA (IA-12). Como los comentarios: se guardan con el proyecto
        # pero no entran en deshacer (son una nota para la IA, no el diseño). Un archivo ajeno las trae: son texto de otro.
        self.instrucciones = ""

    def fijar_instrucciones(self, texto):
        texto = str(texto).strip()
        if len(texto) > TOPE_INSTRUCCIONES:
            raise ErrorDocumento(f"Las instrucciones tienen {len(texto)} caracteres; el máximo es {TOPE_INSTRUCCIONES}.")
        if texto != self.instrucciones:
            self.instrucciones = texto
            self.modificado = True
            self._notificar()

    def fijar_unidades(self, longitud=None, masa=None):
        """Cambia las unidades con que se muestran longitudes (mm, cm, m, in, ft) y masas (g, kg, lb). No toca el
        modelo ni las expresiones: «2 in» sigue valiendo 50.8 mm en cualquier documento."""
        if longitud is not None and longitud not in LONGITUDES:
            raise ErrorDocumento(f"Unidad de longitud desconocida «{longitud}»: {', '.join(LONGITUDES)}.")
        if masa is not None and masa not in MASAS:
            raise ErrorDocumento(f"Unidad de masa desconocida «{masa}»: {', '.join(MASAS)}.")
        nuevas = {"longitud": longitud or self.unidades["longitud"], "masa": masa or self.unidades["masa"]}
        if nuevas != self.unidades:
            self.unidades = nuevas
            self.modificado = True
            self._notificar()

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
        if registro_uso.activo is not None:
            registro_uso.activo.emitir("deshacer")
        self._rehacer.append(self._instantanea())
        self._cargar(json.loads(self._deshacer.pop()))

    def rehacer(self):
        if not self._rehacer:
            return
        if registro_uso.activo is not None:
            registro_uso.activo.emitir("rehacer")
        self._deshacer.append(self._instantanea())
        self._cargar(json.loads(self._rehacer.pop()))

    def _cargar(self, datos):
        """Deshacer/rehacer: vuelve a la receta `datos` recalculando solo desde el primer paso que cambia (antes
        recalculaba desde el paso 0: con una rosca modelada de 30 s, cada deshacer tardaba ~35 s)."""
        antes_ops, antes_marcador, antes_props = self.operaciones, self.marcador, self.propiedades
        antes_valores = self._valores_o_nada()
        self.parametros = TablaParametros.desde_lista(datos.get("parametros"))
        self.propiedades = {k: dict(v) for k, v in (datos.get("propiedades") or {}).items()}
        self.analisis = {k: dict(v) for k, v in (datos.get("analisis") or {}).items()}
        self.configuraciones = dict(datos.get("configuraciones") or {})
        self.espacios = dict(datos.get("espacios", {}))    # deshacer/rehacer también revierten los espacios
        nuevas = [operacion_desde_dict(_migrar(d)) for d in datos.get("operaciones", [])]
        self._contador_cotas = datos.get("contador_cotas", 0)
        conocidos = {c.nombre for o in nuevas if isinstance(o, OpBoceto) for c in o.boceto.cotas.values() if c.nombre}
        self.parametros, self._contador_cotas = self._tabla_cotas(nuevas, conocidos)
        self.marcador = min(datos.get("marcador", len(nuevas)), len(nuevas))
        self._contador = datos.get("contador", len(nuevas))
        self.modificado = True
        despues_valores = self._valores_o_nada()
        a, d = antes_valores or {}, despues_valores or {}
        cambiados = {k for k in set(a) | set(d)
                     if a.get(k) != d.get(k)}
        desde = 0
        if self.propiedades == antes_props and antes_valores is not None and despues_valores is not None:
            tope = min(len(antes_ops), len(nuevas), antes_marcador, self.marcador, len(self._estados),
                       len(self._usados))
            while (desde < tope and nuevas[desde].a_dict() == antes_ops[desde].a_dict()
                   and not (self._usados[desde] & cambiados)):
                nuevas[desde] = antes_ops[desde]          # el mismo objeto: guarda lo que leyó al calcularse
                desde += 1
        viejas = {o.id: o for o in antes_ops}
        for k in range(desde, len(nuevas)):             # también los posteriores: la memoria por paso los reusa
            o = viejas.get(nuevas[k].id)
            if o is not None and type(o) is type(nuevas[k]) and o.a_dict() == nuevas[k].a_dict():
                nuevas[k] = o
        self.operaciones = nuevas
        self.recalcular(desde)

    def _valores_o_nada(self):
        try:
            return self.parametros.valores()
        except ErrorExpresion:
            return None

    # ------------------------------------------------------------ edición del timeline
    def agregar(self, op):
        """Inserta la operación en la posición del marcador (como Fusion) y la ejecuta."""
        tabla, contador = self._tabla_cotas(self.operaciones[:self.marcador] + [op] + self.operaciones[self.marcador:])
        desde = min(self.marcador, self._primer_afectado(tabla))
        self._guardar_para_deshacer()
        i = self.marcador
        self.operaciones.insert(i, op)
        self.parametros, self._contador_cotas = tabla, contador
        self.marcador += 1
        self.modificado = True
        self.recalcular(desde)
        return self.resultados[i]

    def reemplazar(self, op_id, nueva):
        """Edita un paso: la nueva versión conserva el id (las referencias siguen valiendo)."""
        i = self.indice(op_id)
        nueva.id = op_id
        tabla, contador = self._tabla_cotas(self.operaciones[:i] + [nueva] + self.operaciones[i + 1:])
        desde = min(i, self._primer_afectado(tabla))
        self._prevuelo_cambio({"tipo": "reemplazar", "indice": i, "operacion": nueva.a_dict()}, desde)
        self._guardar_para_deshacer()
        self.operaciones[i] = nueva
        self.parametros, self._contador_cotas = tabla, contador
        self.modificado = True
        self.recalcular(desde)
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

    def set_propiedades(self, cambios):
        """Varias propiedades de varios ids con UNA sola instantánea de deshacer (`set_propiedad` toma una por
        llamada y, con decenas de cuerpos y una imagen embebida, cada una cuesta): {id: {clave: valor | None}}.
        No sirve para «nombre» (renombrar recalcula): para eso, `set_propiedad`."""
        if any("nombre" in claves for claves in cambios.values()):
            raise ErrorDocumento("set_propiedades no cambia nombres: usá set_propiedad.")
        self._guardar_para_deshacer()
        for cid, claves in cambios.items():
            props = self.propiedades.setdefault(cid, {})
            for clave, valor in claves.items():
                if valor is None:
                    props.pop(clave, None)
                else:
                    props[clave] = valor
            if not props:
                del self.propiedades[cid]
        self.modificado = True
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
            for m in self._memo.values():      # los estados de la memoria son estos mismos: quedan al día
                m["nombres"] = nombres
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
        operaciones = self._cotas_desde_parametros(tabla)
        self._guardar_para_deshacer()
        self.configuraciones = dict(datos, activa=activa)
        desde = self._primer_afectado(tabla)
        self.operaciones = operaciones
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
        i = self.indice(op_id)
        self._prevuelo_cambio({"tipo": "suprimir", "indice": i, "suprimida": suprimida}, i)
        self._guardar_para_deshacer()
        self.operaciones[i].suprimida = suprimida
        self.modificado = True
        self.recalcular(i)

    def eliminar(self, op_id):
        i = self.indice(op_id)
        tabla, contador = self._tabla_cotas(self.operaciones[:i] + self.operaciones[i + 1:])
        desde = min(i, self._primer_afectado(tabla))
        deps = self.dependientes(op_id)
        if deps:
            raise ErrorDocumento("No se puede eliminar: la usan " + ", ".join(d.nombre for d in deps) + ".")
        self._prevuelo_cambio({"tipo": "eliminar", "indice": i}, desde)
        self._guardar_para_deshacer()
        del self.operaciones[i]
        self.parametros, self._contador_cotas = tabla, contador
        if i < self.marcador:
            self.marcador -= 1
        self.modificado = True
        self.recalcular(desde)

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
    def _tabla_cotas(self, operaciones, conocidos=None, parametros=None):
        """Prepara los parámetros de modelo (Fusion: d1, d2…) antes de editar el historial.

        La expresión vive en la cota; la tabla comparte su evaluador y detección de ciclos con los parámetros
        de usuario. Solo al validar todo se nombran las cotas nuevas de las operaciones entrantes.
        """
        if conocidos is None:
            conocidos = {c.nombre for o in self.operaciones if isinstance(o, OpBoceto)
                         for c in o.boceto.cotas.values() if c.nombre}
        fuente = self.parametros if parametros is None else parametros
        datos = [p.a_dict() for p in fuente if p.nombre not in conocidos]
        ocupados = {p["nombre"] for p in datos}
        cotas = [(o, c) for o in operaciones if isinstance(o, OpBoceto) for c in o.boceto.cotas.values()]
        reservados = ocupados | conocidos | {c.nombre for _, c in cotas if c.nombre}
        contador = self._contador_cotas
        asignaciones = []
        nombres = {}                 # (op, id de cota) → nombre, para las cotas ligadas (chaflán de distancias iguales)
        for op, cota in cotas:
            nombre = cota.nombre
            if not nombre:
                contador += 1
                while f"d{contador}" in reservados:
                    contador += 1
                nombre = f"d{contador}"
                reservados.add(nombre)
            validar_nombre(nombre)
            if nombre.startswith("d") and nombre[1:].isascii() and nombre[1:].isdigit():
                contador = max(contador, int(nombre[1:]))
            if nombre in ocupados:
                raise ErrorExpresion(f"Ya existe el parámetro '{nombre}': dos cotas no pueden compartir nombre.")
            ocupados.add(nombre)
            comentario = fuente.obtener(nombre).comentario if nombre in fuente else ""
            nombres[(id(op), cota.id)] = nombre
            ligada = None if cota.referencia else nombres.get((id(op), cota.datos.get("igual_a")))
            expresion = repr(op.boceto.medir(cota)) if cota.referencia else ligada or cota.expresion
            datos.append({"nombre": nombre, "expresion": expresion,
                          "tipo": ANGULO if cota.tipo == "angulo" else LONGITUD, "comentario": comentario})
            asignaciones.append((cota, nombre, ligada))
        quitados = conocidos - {nombre for _, nombre, _l in asignaciones}
        for nombre in sorted(quitados):
            usuarios = {p["nombre"] for p in datos if nombre in nombres_usados(p["expresion"])}
            usuarios.update(o.nombre for o in operaciones if any(nombre in nombres_usados(e) for e in o.expresiones()))
            if usuarios:
                raise ErrorExpresion(f"No se puede borrar '{nombre}': lo usan {', '.join(sorted(usuarios))}.")
        tabla = TablaParametros.desde_lista(datos)
        for cota, nombre, ligada in asignaciones:
            cota.nombre = nombre
            if "igual_a" in cota.datos:          # se liga una sola vez, al nombrarse: después es una expresión más
                del cota.datos["igual_a"]
                if ligada:
                    cota.expresion = ligada
        self._medir_referencias(tabla, cotas)
        return tabla, contador

    @staticmethod
    def _medir_referencias(tabla, cotas):
        """Resuelve los dN de referencia en orden de dependencia geométrica, sin alterar las recetas.

        Una medida depende de las cotas driving de sus grupos del solver. Esto permite citarla en
        otros grupos/bocetos y detecta el ciclo si intenta gobernar la misma geometría que mide.
        """
        referencias = {c.nombre: (o.boceto, c) for o, c in cotas if c.referencia}
        if not referencias:
            return
        from ..restricciones.solver import _grupos, resolver

        grupos = {id(b): _grupos(b) for b, _ in referencias.values()}
        resueltos, en_curso = {}, set()

        def valor(nombre):
            if nombre in resueltos:
                return resueltos[nombre]
            if nombre in en_curso:
                raise ErrorExpresion(f"Referencia circular en el parámetro '{nombre}' (cota de referencia).")
            en_curso.add(nombre)
            if nombre in referencias:
                b, c = referencias[nombre]
                puntos = set(b.puntos_de(c.entidades))
                necesarias = {k.id: k for g in grupos[id(b)]
                              if puntos & g["p"] or set(c.entidades) & g["r"] for k in g["cotas"]}
                valores = {i: valor(k.nombre) for i, k in necesarias.items()}
                copia = b.copia()
                copia.cotas = {i: copia.cotas[i] for i in necesarias}
                resolver(copia, valores)
                resultado = copia.medir(c)
            else:
                p = tabla.obtener(nombre)
                deps = {n: valor(n) for n in nombres_usados(p.expresion) if n in tabla}
                resultado = evaluar(p.expresion, p.tipo, deps)
            en_curso.remove(nombre)
            resueltos[nombre] = resultado
            return resultado

        for nombre in referencias:
            valor(nombre)
        for nombre in referencias:
            tabla.obtener(nombre).expresion = repr(resueltos[nombre])
        tabla.valores()

    def _cotas_desde_parametros(self, tabla):
        """Copias de los bocetos cuyas cotas se editaron desde la tabla, sin tocar la receta anterior."""
        operaciones = list(self.operaciones)
        for i, op in enumerate(operaciones):
            if not isinstance(op, OpBoceto):
                continue
            cambios = {}
            for cota in op.boceto.cotas.values():
                if cota.nombre not in tabla:
                    raise ErrorExpresion(f"No se puede borrar '{cota.nombre}': lo usa su cota de boceto. "
                                         "Borrá la cota con delete_sketch_entities.")
                expresion = tabla.obtener(cota.nombre).expresion
                if cota.referencia:
                    if expresion != self.parametros.obtener(cota.nombre).expresion:
                        raise ErrorBoceto("Una cota de referencia mide la geometría: su valor no se puede editar.")
                    continue
                if expresion != cota.expresion:
                    cambios[cota.id] = expresion
            if cambios:
                nueva = op.copia()
                for cid, expresion in cambios.items():
                    nueva.boceto.cotas[cid].expresion = expresion
                operaciones[i] = nueva
        return operaciones

    def parametros_usados(self):
        """{nombre de parámetro: [pasos que lo usan]} recorriendo todas las expresiones del timeline."""
        usos = {}
        for op in self.operaciones:
            for expr in op.expresiones():
                for nombre in nombres_usados(expr):
                    usos.setdefault(nombre, set()).add(op.nombre)
        return usos

    def aplicar_parametros(self, tabla):
        """Aplica la tabla (UserParameters de Fusion). En documentos grandes con OpenCascade ensaya primero en un
        hijo: cuesta reconstruir la receta y recalcular allí, además del recálculo real. Es una defensa frente a
        caídas nativas, no su curación: que el hijo termine no garantiza que el kernel no caiga luego en el padre.
        """
        tabla.valores()  # valida antes de tocar el documento
        operaciones = self._cotas_desde_parametros(tabla)
        tabla, _ = self._tabla_cotas(operaciones, parametros=tabla)
        faltan = {n: pasos for n, pasos in self.parametros_usados().items() if n in self.parametros and n not in tabla}
        if faltan:
            detalle = "; ".join(f"«{n}» (lo usa {', '.join(sorted(p))})" for n, p in sorted(faltan.items()))
            raise ErrorDocumento(f"No se puede quitar ni renombrar un parámetro en uso: {detalle}.")
        desde = self._primer_afectado(tabla)
        self._prevuelo_parametros(tabla, desde)
        self._guardar_para_deshacer()
        self.operaciones = operaciones
        self.parametros = tabla
        self.modificado = True
        self.recalcular(desde)

    def _prevuelo_corresponde(self):
        """True si un cambio del historial tiene que ensayarse antes en un proceso aparte (B-48)."""
        from ..nucleo import aislado

        return (not aislado.EN_HIJO and motor.motor_activo() == "opencascade"
                and sum(not op.suprimida for op in self.operaciones[:self.marcador])
                >= aislado.UMBRAL_PREVUELO_PARAMETROS)

    def _prevuelo_parametros(self, tabla, desde):
        """Ensaya sin modificar el documento ni deshacer; omite documentos chicos, OmniKernel y el propio hijo."""
        from ..nucleo import aislado

        if not self._prevuelo_corresponde():
            return
        try:
            aislado.correr_json("prevuelo_parametros", {"receta": self.a_dict(), "parametros": tabla.a_lista(),
                                                      "desde": desde}, aislado.TOPE_PREVUELO_PARAMETROS)
        except aislado.TareaAislada as e:
            raise ErrorDocumento(f"El prevuelo de parámetros falló: {e}. No se aplicó el cambio y el documento quedó "
                                 "como estaba. Guardá una copia y probá valores distintos.") from e

    def _prevuelo_cambio(self, cambio, desde):
        """Ensaya editar, suprimir o eliminar un paso en un hijo (B-48): el recálculo del historial también puede
        caer en una excepción nativa del kernel. Si el hijo cae, el documento no se toca."""
        from ..nucleo import aislado

        if not self._prevuelo_corresponde():
            return
        try:
            aislado.correr_json("prevuelo_cambio", {"receta": self.a_dict(), "cambio": cambio, "desde": desde},
                                aislado.TOPE_PREVUELO_PARAMETROS)
        except aislado.TareaAislada as e:
            raise ErrorDocumento(f"El ensayo del cambio falló: {e}. No se aplicó y el documento quedó como estaba. "
                                 "Guardá una copia y probá otro cambio.") from e

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
        entrada = self.estado_en(indice)
        tabla = self.parametros
        if isinstance(op, OpBoceto):
            operaciones = [op if o.id == op.id else o for o in self.operaciones]
            if not any(o.id == op.id for o in self.operaciones):
                operaciones.insert(indice, op)
            tabla, _ = self._tabla_cotas(operaciones)
        try:
            valores = tabla.valores()
        except ErrorExpresion:
            valores = {}
        receta, m = _receta(op), self._previa
        # La misma previa otra vez (el temporizador del diálogo con los mismos valores): no se vuelve a calcular.
        if (m is not None and receta is not None and op.MEMORIZABLE and m["receta"] == receta and m["entrada"] is entrada
                and m["motor"] == self.motor and all(valores.get(n, _FALTA) == v for n, v in m["valores"].items())):
            op._usados = set(m["op_usados"])
            return m["salida"], list(m["resultado"])
        estado = entrada.copia()
        estado.anotar_lecturas()
        ctx = Contexto(valores)
        if self.al_calcular is not None:
            self.al_calcular(op)
        inicio = time.perf_counter()
        try:
            op.calcular(estado, ctx)
        finally:
            lecturas = estado.cerrar_lecturas()
        if op.TIPO == "derivacion" and op.p["parametros"]:
            op.copiar_parametros(self.parametros)
        if receta is not None:      # para la próxima previa igual y para el recálculo al aceptar (`_de_previa`)
            self._previa = {"receta": receta, "motor": self.motor, "entrada": entrada, "salida": estado,
                            "lecturas": lecturas, "resultado": list(ctx.avisos), "usados": frozenset(ctx.usados),
                            "valores": {n: valores.get(n, _FALTA) for n in ctx.usados},
                            "duracion": time.perf_counter() - inicio, "op_usados": set(op._usados)}
        return estado, ctx.avisos

    def _de_previa(self, op, estado, valores):
        """El paso tal como lo calculó la última vista previa, si es la misma operación sobre el mismo estado: al
        aceptar un comando no se vuelve a calcular la booleana o el empalme que ya mostró la previa."""
        m, self._previa = self._previa, None
        if (m is None or not op.MEMORIZABLE or m["entrada"] is not estado or m["motor"] != self.motor
                or _receta(op) != m["receta"] or any(valores.get(n, _FALTA) != v for n, v in m["valores"].items())):
            return None
        op._usados = set(m["op_usados"])
        resultado = ResultadoPaso("aviso", " ".join(m["resultado"])) if m["resultado"] else ResultadoPaso("ok")
        self._memo[op.id] = dict(m, op=op, resultado=resultado, nombres=self._nombres_cuerpos())
        return m["salida"], resultado, m["usados"], m["duracion"]

    @motor.recalculo
    @registrar_calculo
    def recalcular(self, desde=0):
        registro = registro_uso.activo
        if registro is not None:
            inicio_registro, tiempos_registro = time.perf_counter(), []
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
        repetidos = self._pasos_repetidos() if self._cache else set()
        for i in range(desde, len(self.operaciones)):
            op = self.operaciones[i]
            if registro is not None:
                antes_registro = [(c.tipo, c.forma) for c in estado.cuerpos.values()]
                inicio_paso = time.perf_counter()
            usados = frozenset()
            duracion = 0.0
            guardado = self._de_cache(i, op, estado) if (i < self.marcador and not op.suprimida
                                                          and op.id not in repetidos) else None
            if i >= self.marcador:
                self.resultados.append(ResultadoPaso("retrocedida"))
            elif op.suprimida:
                self.resultados.append(ResultadoPaso("suprimida"))
            elif guardado is not None:
                estado, resultado, usados, duracion = guardado
                self.resultados.append(resultado)
            elif (memo := self._de_memo(op, estado, valores) or self._de_previa(op, estado, valores)) is not None:
                estado, resultado, usados, duracion = memo
                self.resultados.append(resultado)
            else:
                entrada, receta = estado, _receta(op)
                nuevo = estado.copia()
                nuevo.anotar_lecturas()
                ctx = Contexto(valores)
                usados = ctx.usados
                if self.al_calcular is not None:
                    self.al_calcular(op)
                inicio = time.perf_counter()
                try:
                    op.calcular(nuevo, ctx)
                    if op.TIPO == "derivacion" and op.p["parametros"]:
                        tabla = op.copiar_parametros(self.parametros)
                        nuevos_valores = tabla.valores()
                        self.parametros = tabla
                        valores.clear()
                        valores.update(nuevos_valores)
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
                finally:
                    lecturas = nuevo.cerrar_lecturas()
                duracion = time.perf_counter() - inicio
                if receta is not None:
                    self._memo[op.id] = {"op": op, "receta": receta, "motor": self.motor, "entrada": entrada,
                                         "salida": estado if estado is nuevo else None, "lecturas": lecturas,
                                         "resultado": self.resultados[-1], "usados": frozenset(usados),
                                         "valores": {n: valores.get(n, _FALTA) for n in usados},
                                         "duracion": duracion, "op_usados": set(op._usados), "nombres": nombres}
            self._poner_nombres(estado, nombres)   # antes del paso siguiente: la copia de «Placa» sale «Placa (copia)»
            self._estados.append(estado)
            self._usados.append(usados)
            self._duraciones.append(duracion)
            if registro is not None and i < self.marcador and not op.suprimida:
                ms = (time.perf_counter() - inicio_paso) * 1000
                datos_uso = {"paso": op.id, "tipo_op": op.TIPO, "duracion_ms": ms,
                             "exito": self.resultados[-1].estado != "error",
                             "mensaje": self.resultados[-1].mensaje}
                registro.emitir("op_ejecutada", datos_uso, medidas=(antes_registro,
                    [(c.tipo, c.forma) for c in estado.cuerpos.values()]))
                tiempos_registro.append({"paso": op.id, "duracion_ms": ms})
                if self.resultados[-1].estado in ("error", "aviso"):
                    registro.emitir("error", {"origen": "operacion", "paso": op.id,
                        "tipo_op": op.TIPO, "categoria": self.resultados[-1].estado,
                        "mensaje": self.resultados[-1].mensaje})
        vigentes = {id(op) for op in self.operaciones}
        self._memo = {k: m for k, m in self._memo.items() if id(m["op"]) in vigentes}
        self._previa = None
        self._notificar()

        if registro is not None:
            registro.emitir("recalculo", {"duracion_ms": (time.perf_counter() - inicio_registro) * 1000,
                "lentos": sorted(tiempos_registro, key=lambda d: d["duracion_ms"], reverse=True)[:5]})

    # ------------------------------------------------------------ memoria por paso (P7 de docs/plan_rust.md)
    def olvidar_memoria(self):
        """El próximo `recalcular` ejecuta todos los pasos («Calcular todo» de Fusion: Compute All)."""
        self._memo.clear()

    def _de_memo(self, op, estado, valores):
        """El último resultado del paso, si con `estado` y `valores` daría lo mismo: misma operación (mismo objeto y
        receta), mismo motor, mismos parámetros leídos y lo que leyó del estado sin cambios. Así, editar un paso no
        recalcula los posteriores que no dependen de él. (estado, resultado, parámetros leídos, duración) o None."""
        m = self._memo.get(op.id)
        if (m is None or m["op"] is not op or m["motor"] != self.motor or not op.MEMORIZABLE
                or m.get("nombres") != self._nombres_cuerpos()):     # los renombres viven en los estados guardados
            return None
        if any(valores.get(n, _FALTA) != v for n, v in m["valores"].items()) or _receta(op) != m["receta"]:
            return None
        viejo = m["entrada"]
        if set(vars(viejo)) != set(vars(estado)):
            return None
        for nombre, antes in vars(viejo).items():
            ahora = getattr(estado, nombre)
            if nombre not in m["lecturas"]:     # contador de cuerpos, grupos rígidos: tienen que ser iguales
                if not _igual(ahora, antes):
                    return None
                continue
            leidas = m["lecturas"][nombre]
            if leidas is TODAS and list(ahora) != list(antes):
                return None
            for k in (antes if leidas is TODAS else leidas):
                if (k in ahora) != (k in antes) or (k in antes and not _mismo_valor(ahora[k], antes[k])):
                    return None
        op._usados = set(m["op_usados"])
        nuevo = self._aplicar_memo(m, estado)
        # La entrada y la salida de ahora valen igual (mismas lecturas, mismo cambio) y así la memoria no retiene los
        # estados viejos (con sus formas) de cálculos anteriores.
        m["entrada"], m["salida"] = estado, (nuevo if m["salida"] is not None else None)
        return nuevo, m["resultado"], m["usados"], m["duracion"]

    @staticmethod
    def _aplicar_memo(m, estado):
        """`estado` con lo que el paso cambió en su último cálculo (de su entrada a su salida)."""
        viejo, salida = m["entrada"], m["salida"]
        if salida is None:                      # terminó en error: no tocó el estado
            return estado
        nuevo = estado.copia()
        for nombre, antes in vars(viejo).items():
            despues = getattr(salida, nombre)
            if nombre not in m["lecturas"]:
                setattr(nuevo, nombre, despues)
                continue
            d = getattr(nuevo, nombre)
            for k in antes:
                if k not in despues:
                    d.pop(k, None)
            for k, v in despues.items():
                if k not in antes or not _mismo_valor(v, antes[k]):
                    d[k] = v.copia() if isinstance(v, Cuerpo) else dict(v) if nombre == "componentes" else v
        return nuevo

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

    def _pasos_repetidos(self):
        """Pasos cuya herramienta repite un patrón de operaciones (`pasos_repetidos()` de OpPatron y
        OpMultitransformar): se calculan aunque estén en la caché, que guarda los cuerpos y no la herramienta."""
        salida = set()
        for op in self.operaciones:
            pasos = getattr(op, "pasos_repetidos", None)
            if pasos is not None and not op.suprimida:
                salida |= set(pasos())
        # Un origen externo puede cambiar aunque la receta local conserve la misma huella.
        for i, op in enumerate(self.operaciones):
            if op.TIPO == "derivacion" and not op.suprimida:
                salida.update(o.id for o in self.operaciones[i:])
                break
        return salida

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
                **({"contador_cotas": self._contador_cotas} if self._contador_cotas else {}),
                "vistas": self.vistas, "propiedades": self.propiedades, "analisis": self.analisis,
                "configuraciones": self.configuraciones,
                "espacios": self.espacios, "comentarios": self.comentarios,
                **({"unidades": self.unidades} if self.unidades != UNIDADES_DEFECTO else {}),
                **({"instrucciones": self.instrucciones} if self.instrucciones else {})}

    @staticmethod
    def unidades_de(datos):
        """Las unidades de pantalla de una receta; un archivo viejo o ajeno: lo que no sirve se ignora (puede venir
        una lista, un número…) y queda mm/g."""
        unidades = dict(UNIDADES_DEFECTO)
        guardadas = datos.get("unidades")
        guardadas = guardadas if isinstance(guardadas, dict) else {}
        for magnitud, validas in (("longitud", LONGITUDES), ("masa", MASAS)):
            valor = guardadas.get(magnitud)
            if isinstance(valor, str) and valor in validas:
                unidades[magnitud] = valor
        return unidades

    @staticmethod
    def instrucciones_de(datos):
        """Las instrucciones de una receta: texto de un archivo ajeno, así que lo que no es texto se ignora y se corta
        al tope (un .omnicad con un megabyte ahí no infla el prompt)."""
        texto = datos.get("instrucciones")
        return texto.strip()[:TOPE_INSTRUCCIONES] if isinstance(texto, str) else ""

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
        doc.unidades = cls.unidades_de(datos)
        doc.instrucciones = cls.instrucciones_de(datos)
        doc._cache = cache or {}
        try:
            doc._cargar(datos)
        finally:
            doc._cache = {}
        doc.modificado = False
        return doc
