"""Registro local optativo. Sin Qt, red, contenido de archivos ni texto de campos."""
import atexit
import json
import math
import os
import platform
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Full, Queue

from .. import VERSION, carpeta_datos
from .reporte import url_issue as url_issue
from . import sistema

# Valores de fábrica de las opciones del registro (el usuario las cambia en Preferencias › Registro de uso).
# `tope_archivo` es interno (la rotación de un JSONL); lo demás tiene rango editable y su clave de QSettings.
FABRICA = {"retencion_dias": 7, "tope_total_mb": 150, "tope_capturas_mb": 50, "tope_archivo_mb": 5,
           "disco_libre_min_gb": 2.0, "memoria_cada_s": 30, "detallado": False, "captura_error": False}
RANGOS = {"retencion_dias": (1, 90), "tope_total_mb": (20, 2000), "tope_capturas_mb": (0, 500),
          "disco_libre_min_gb": (0.5, 50.0), "memoria_cada_s": (5, 300), "tope_archivo_mb": (1, 20)}
CLAVES_PREFS = {"retencion_dias": "registro/retencion_dias", "tope_total_mb": "registro/tope_total_mb",
                "tope_capturas_mb": "registro/tope_capturas_mb", "disco_libre_min_gb": "registro/disco_libre_min_gb",
                "memoria_cada_s": "registro/memoria_cada_s", "detallado": "registro/detallado",
                "captura_error": "registro/captura_error"}
VALORES = dict(FABRICA)
_cerrojo_valores = threading.Lock()
ULTIMO_PODA = time.monotonic()
activo = None
ultimo = None
_CLAVE = re.compile(r"[A-Za-z_][A-Za-z_0-9.-]{0,95}\Z")
_IDENTIFICADORES = {"comando", "tipo_op", "accion", "origen", "formato", "excepcion", "categoria", "paso", "label",
                    "tipo", "herramienta", "estado", "funcion", "archivo", "clase", "objetivo", "resultado",
                    "valor", "nombre"}
# Texto útil que se guarda completo (saneado: «~», 500 caracteres) según el tipo de evento; `detallado` abre
# los valores escritos en los diálogos. Nada de esto es texto libre del usuario salvo que él lo pida.
_ABIERTOS = {"error": {"error.mensaje"},
             "op_ejecutada": {"op_ejecutada.paso", "op_ejecutada.tipo_op", "op_ejecutada.mensaje",
                              "op_ejecutada.nombre", "op_ejecutada.cuerpos"},
             "comando_resultado": {"comando_resultado.comando"},
             "boceto_cota": {"boceto_cota.tipo", "boceto_cota.valor"}}
# Orígenes cuyo mensaje no escribe la app: se guarda solo la longitud.
_ORIGENES_AJENOS = {"qt"}
# Clave de API: UNA palabra de 20+ con dígito y símbolo (los lookaheads no salen de ella); no oculta rutas del código.
_TOKEN = re.compile(r"(?<!\S)(?!(?:omnicad|tests)/)(?=\S{20,})(?=\S*\d)(?=\S*[+/_.-])\S+")
_RUTA_WINDOWS = re.compile(r"[A-Za-z]:[\\/]\S+")
_NUMERO = re.compile(r"-?\d+(?:\.\d+)?\Z")
_ENTEROS = ("retencion_dias", "tope_total_mb", "tope_capturas_mb", "memoria_cada_s")
_TOQUES = ("retencion_dias", "tope_total_mb", "tope_capturas_mb")


def carpeta():
    """Carpeta privada del registro; la variable solo permite aislar pruebas."""
    return Path(os.environ.get("OMNICAD_REGISTRO_DIR") or carpeta_datos() / "registro")


def parse_numero(texto):
    """«7», «7 días», «2,5», «150 MB» → número; texto, vacío, negativo o mal formado → None."""
    si = str(texto).strip().lower().replace(",", ".")
    for sufijo in ("días", "dias", "mb", "gb", "s", "seg", "segundos"):
        if si.endswith(" " + sufijo):
            si = si[: -len(sufijo) - 1].strip()
    return float(si) if _NUMERO.fullmatch(si) and si[0] != "-" and "." not in si[:1] and not si.endswith(".") else None


def normalizar(valores):
    """Pisa solo claves conocidas, validadas por su rango; devuelve el dict completo resultante.
    ValueError con el rango en español (la ventana y la API muestran el mismo mensaje)."""
    salida = dict(VALORES)
    for clave, valor in (valores or {}).items():
        es_booleana = clave in salida and isinstance(salida[clave], bool)
        if es_booleana and isinstance(valor, bool):
            salida[clave] = valor
            continue
        if clave not in RANGOS or isinstance(valor, bool) or valor is None:
            raise ValueError(f"La opción «{clave}» no existe o no es un número en el registro de uso.")
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            raise ValueError(f"«{clave}» tiene que ser un número.") from None
        minimo, maximo = RANGOS[clave]
        if not minimo <= numero <= maximo:
            raise ValueError(f"«{clave}» está fuera de rango: tiene que estar entre {minimo} y {maximo}.")
        if clave in _ENTEROS and numero != int(numero):
            raise ValueError(f"«{clave}» tiene que ser un número entero.")
        salida[clave] = int(numero) if clave in _ENTEROS else numero
    salida["tope_capturas_mb"] = min(salida["tope_capturas_mb"], salida["tope_total_mb"])
    return salida


def aplicar(nuevos=None):
    """Valores activos de las opciones (los numéricos los recibe la ventana desde sus preferencias).
    Si un tope o la retención cambiaron, se poda en ese momento."""
    global ULTIMO_PODA
    cambios = normalizar(nuevos or {})
    with _cerrojo_valores:
        topes_antes = tuple(VALORES[k] for k in _TOQUES)
        VALORES.update(cambios)
        copia = dict(VALORES)
    if any(cambios[k] != v for k, v in zip(_TOQUES, topes_antes, strict=True)):   # achicó un tope o los días: poda ya
        podar()
        ULTIMO_PODA = time.monotonic()
    return copia


def valores():
    with _cerrojo_valores:
        return dict(VALORES)


_PRIVADOS = {"ruta", "contenido", "chat", "valor_parametro_texto", "base_url", "token",
             "ruta_claude_code", "ruta_codex", "ruta_opencode"}   # "direccion" NO va acá: es una opción de Extruir
_TEXTO_MAXIMO = 500


_RUTAS_PROPIAS = None


def _rutas_propias():
    """Las rutas de la PC que no deben aparecer en el texto guardado (se calculan una vez)."""
    global _RUTAS_PROPIAS
    if _RUTAS_PROPIAS is None:
        _RUTAS_PROPIAS = (str(carpeta_datos()), str(Path.home()))
    return _RUTAS_PROPIAS


def _sano(texto):
    """Texto acotado: sin saltos de línea ni tokenes largos, rutas de la PC reemplazadas por «~», 500 caracteres."""
    limpio = re.sub(r"\s+", " ", str(texto)).strip()
    for ruta in _rutas_propias():
        limpio = re.sub(re.escape(ruta.replace("\\", "/")), "~", limpio, flags=re.IGNORECASE)
        limpio = limpio.replace(ruta, "~")
    limpio = _RUTA_WINDOWS.sub(lambda m: "~/" + re.split(r"[\\/]", m.group(0))[-1], limpio)
    limpio = _TOKEN.sub("[token]", limpio)
    return limpio[:_TEXTO_MAXIMO]


def _se_fija(valor):
    """Valor de una lista fija (los «Opciones»/«Casilla» de un diálogo): palabra corta y limpia, no ruta ni token.
    shortcut: distingue por forma (minúsculas o Título Con Mayúsculas), no por diccionario; un texto escrito por la
    persona con esa misma forma se guarda también. Se vuelve a revisar si aparece un caso real de fuga."""
    if not valor or len(valor) > 64 or _TOKEN.fullmatch(valor):
        return False
    if not valor[0].isalpha():
        return False
    permitido = set(" abcdefghijklmnopqrstuvwxyz0123456789áéíóúüñ._()°+-")
    if any(c not in permitido for c in valor.lower()):
        return False
    return valor.islower() or valor.istitle()


def _privado(valor, clave="", nivel=0, identificadores=True, abiertos=(), detallado=False, rama="", libres=()):
    if nivel > 4:
        return None
    if valor is None or isinstance(valor, bool):
        return valor
    if isinstance(valor, (float, int)):
        try:
            return valor if math.isfinite(valor) else None
        except (OverflowError, TypeError):
            return None
    if isinstance(valor, str):
        if not valor.strip():
            return ""                                   # un vacío se guarda vacío, no como {"longitud": 0}
        if rama in abiertos:
            return _sano(valor)
        if identificadores and clave in _IDENTIFICADORES and _CLAVE.fullmatch(valor):
            return valor
        if rama.rpartition(".")[2] == "valores" and rama.count(".") <= 2:
            if clave in _PRIVADOS or clave == "ruta":
                return {"longitud": len(valor)}
            if clave in libres:                     # texto libre del diálogo: largo, salvo modo detallado
                return _sano(valor) if detallado else {"longitud": len(valor)}
            return valor if detallado or _se_fija(valor) else {"longitud": len(valor)}
        return {"longitud": len(valor)}
    if isinstance(valor, dict):
        if clave == "traza" or rama == "error.traza":
            return {k: valor[k] for k in ("archivo", "linea", "funcion") if k in valor}
        return {k: _privado(v, k, nivel + 1, identificadores and k != "valores", abiertos, detallado,
                            f"{rama}.{k}" if nivel == 0 else (f"{rama}.{k}" if isinstance(v, dict) else rama), libres)
                for k, v in list(valor.items())[:64] if isinstance(k, str) and _CLAVE.fullmatch(k)}
    if isinstance(valor, (tuple, list)):
        return [_privado(v, clave, nivel + 1, identificadores, abiertos, detallado, rama, libres)
                for v in valor[:64]]
    return None


class Registro:
    """Un productor rápido y un único escritor; cola acotada y fallos visibles en estado()."""

    def __init__(self, datos=None, destino=None, tope_total=None, tope_archivo=None, retencion=None,
                 tope_capturas=None):
        v = valores()
        self.carpeta = Path(destino) if destino else carpeta()
        self.tope_total = int(tope_total if tope_total is not None else v["tope_total_mb"] * 2**20)
        self.retencion = int(retencion if retencion is not None else v["retencion_dias"] * 86400)
        self.tope_capturas = int(tope_capturas if tope_capturas is not None
                                 else min(v["tope_capturas_mb"], v["tope_total_mb"]) * 2**20)
        self.tope_archivo = int(tope_archivo if tope_archivo is not None
                                else min(v["tope_archivo_mb"] * 2**20, self.tope_total))
        self.tope_archivo = min(self.tope_archivo, self.tope_total)
        self.id = datetime.now().strftime("%Y-%m-%d_%H%M%S_") + uuid.uuid4().hex[:12]
        self.inicio = time.perf_counter()
        self.cola = Queue(maxsize=8192)
        self._cerrojo = threading.Lock()
        self._calculos = 0
        self._calculo_libre = threading.Event()
        self._calculo_libre.set()
        self._cerrado = False
        self.seq = self.descartados = 0
        self.fallo = None
        self.archivos = []
        self._volumenes = {}
        self._libre = None
        self._libre_lectura = 0.0
        self._captura_pendiente = None   # seq del último error al que le falta su captura
        self.carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
        podar(sesion_id=self.id)                            # arranque: se borra lo viejo antes de escribir
        self.hilo = threading.Thread(target=self._escribir, name="registro_uso", daemon=True)
        self.emitir("sesion_inicio", {"version": VERSION, "so": platform.system(), **(datos or {})}, cabecera=True)
        self.hilo.start()

    def disco_bajo(self):
        """Queda menos espacio libre que el mínimo: el registro se pausa (se reactiva solo al liberar disco)."""
        ahora = time.monotonic()
        if self._libre is None or ahora - self._libre_lectura > 30:
            self._libre_lectura = ahora
            with self._cerrojo:
                self._libre = sistema.disco_libre(self.carpeta)
        minimo = valores()["disco_libre_min_gb"] * 10**9
        return self._libre is not None and self._libre < minimo

    def emitir(self, tipo, datos=None, *, cabecera=False, medidas=None, libres=()):
        """Encola sin E/S. Devuelve seq o None si la cola está llena, el escritor falló o hay poco disco."""
        if self._cerrado or self.fallo or not _CLAVE.fullmatch(tipo) or self.disco_bajo():
            return None
        v = valores()
        abiertos = set(_ABIERTOS.get(tipo, ()))
        if tipo == "error" and (datos or {}).get("origen") in _ORIGENES_AJENOS:
            abiertos.discard("error.mensaje")      # lo que dice Qt (no la app) puede traer datos del usuario
        seguros = _privado(datos or {}, rama=tipo, abiertos=abiertos, detallado=v["detallado"],
                           libres=set(libres or ()))
        if cabecera:
            for k in ("version", "so", "gpu", "opengl", "proyecto"):
                v = (datos or {}).get(k)
                if isinstance(v, str):
                    seguros[k] = v.replace("\\", "/").rsplit("/", 1)[-1][:160]
        if tipo == "marca":
            for clave in ("nota", "titulo"):
                if isinstance((datos or {}).get(clave), str):
                    seguros[clave] = datos[clave][:2000]  # texto que la persona eligió guardar explícitamente
            if (datos or {}).get("tipo") in ("Problema", "Sugerencia"):
                seguros["tipo"] = datos["tipo"]
        with self._cerrojo:
            if self._cerrado:
                return None
            self.seq += 1
            if tipo == "error" and v["detallado"] and v["captura_error"]:
                self._captura_pendiente = self.seq      # la ventana toma la foto en el próximo latido
            evento = {"t": round(time.perf_counter() - self.inicio, 3),
                      "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                      "tipo": tipo, "datos": seguros, "seq": self.seq}
            try:
                self.cola.put_nowait((evento, medidas))
            except Full:
                self.descartados += 1
                return None
        return evento["seq"]

    def _podar(self, reserva, actual=None):
        vivos = _vivos(self.carpeta)
        curso = [str(p) for _f, p, _t in vivos if p.name.startswith(f"sesion_{self.id}_")]
        total = _recortar(vivos, self.retencion, self.tope_total, self.tope_capturas,
                          str(actual) if actual else (sorted(curso)[-1] if curso else ""),
                          reserva, hasta=max(0, self.tope_total - reserva))
        if total > self.tope_total:
            raise OSError("El registro alcanzó su tope de tamaño.")

    def escribir_captura(self, nombre, png):
        """Guarda un PNG del registro (marca o error) podando primero; la sesión en curso nunca se toca."""
        if self.disco_bajo():
            raise OSError("Hay menos espacio libre del mínimo: el registro está pausado.")
        self._podar(len(png))
        ruta = self.carpeta / nombre
        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as f:
            f.write(png)
        return ruta

    def reajustar(self, nuevos):
        """Cambios del usuario sobre la sesión en curso: topes, días y poda inmediata si achicó."""
        self.tope_total = nuevos["tope_total_mb"] * 2**20
        self.retencion = nuevos["retencion_dias"] * 86400
        self.tope_capturas = min(nuevos["tope_capturas_mb"], nuevos["tope_total_mb"]) * 2**20
        self.podar()

    def podar(self):
        """Poda manual con los topes de esta sesión (el botón de Preferencias)."""
        vivos = _vivos(self.carpeta)
        curso = [str(p) for _f, p, _t in vivos if p.name.startswith(f"sesion_{self.id}_")]
        return _recortar(vivos, self.retencion, self.tope_total, self.tope_capturas, sorted(curso)[-1] if curso else "")

    def _escribir(self):
        archivo = None
        tamano = parte = 0
        try:
            while True:
                pendiente = self.cola.get()
                try:
                    if pendiente is None:
                        break
                    evento, medidas = pendiente
                    if medidas is not None:
                        self._calculo_libre.wait()
                        from .ganchos import medidas as medir
                        evento["datos"]["antes"], evento["datos"]["despues"] = (
                            medir(cs, self._volumenes) for cs in medidas)
                    linea = (json.dumps(evento, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
                    if len(linea) > self.tope_archivo:
                        self.descartados += 1
                        continue
                    if archivo is None or tamano + len(linea) > self.tope_archivo:
                        if archivo:
                            archivo.close()
                        self._podar(self.tope_archivo)
                        parte += 1
                        ruta = self.carpeta / f"sesion_{self.id}_{parte:04d}.jsonl"
                        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        archivo = os.fdopen(descriptor, "wb", buffering=0)
                        self.archivos.append(ruta)
                        tamano = 0
                    if archivo.write(linea) != len(linea):
                        raise OSError("Escritura incompleta del registro.")
                    archivo.flush()
                    tamano += len(linea)
                finally:
                    self.cola.task_done()
        except Exception as e:  # noqa: BLE001 — un escritor caído se informa y no frena el productor
            self.fallo = type(e).__name__
        finally:
            if archivo:
                archivo.close()
            while True:
                try:
                    self.cola.get_nowait()
                    self.cola.task_done()
                except Empty:
                    break

    def cerrar(self):
        """Drena lo pendiente antes de cerrar; no acepta eventos nuevos."""
        with self._cerrojo:
            if self._cerrado:
                return
            self._cerrado = True
        if self.hilo.is_alive():
            self.cola.put(None)
            self.hilo.join(timeout=5)

    def estado(self):
        return {"session": self.id, "enabled": not self._cerrado and self.fallo is None,
                "error": self.fallo, "dropped": self.descartados, "paused_low_disk": self.disco_bajo()}


def _recortar(vivos, retencion, tope_total, tope_capturas, actual="", reserva=0, hasta=None):
    """Borra lo más viejo del registro: primero lo que pasó de los días de retención, después hasta el tope
    (el umbral bajo es 80 % del total; el escritor lo pasa al tope duro). `actual` —la parte abierta de la
    sesión en curso— y `reserva` se salvan siempre. `vivos` es la lista (fecha, ruta, tamaño).
    Devuelve el total restante en bytes."""
    objetivo = tope_total * 0.8 if hasta is None else hasta
    ahora = time.time()
    lista = sorted(vivos)
    total = sum(t for _f, _p, t in lista) + reserva
    en_curso = next((str(p) for _f, p, _t in reversed(lista) if str(p) == actual), "")
    capturas = [(t, str(p), _f) for _f, p, t in lista if p.name.startswith(("marca_", "error_"))]
    falta_capturas = sum(t for t, _s, _f in capturas) - tope_capturas

    def borrar(tamano, ruta):
        nonlocal total, falta_capturas
        try:
            ruta.unlink()
        except OSError:
            return
        total -= tamano
        if str(ruta) == en_curso or ruta.name.startswith(("marca_", "error_")):
            falta_capturas -= tamano

    for fecha, ruta, tamano in list(lista):                 # 1) todo lo que pasó de la retención; si pasó la meta,
        if str(ruta) == en_curso:                          # también lo más viejo hasta volver al umbral bajo
            continue
        if ahora - fecha > retencion or total > objetivo:
            borrar(tamano, ruta)
    for tamano, ruta, _fecha in sorted(capturas):          # 2) el tope propio de las capturas
        if falta_capturas <= 0:
            break
        if ruta != en_curso:
            borrar(tamano, Path(ruta))
    if total > objetivo:                                   # 3) sigue pasado: se poda también la sesión en curso,
        for fecha, ruta, tamano in list(lista):            # salvo la parte que se está escribiendo
            if total <= objetivo:
                break
            if str(ruta) != en_curso:
                borrar(tamano, ruta)
    return total


def _vivos(ruta_carpeta):
    """(fecha, ruta, tamaño) de todo lo del registro: acotado a su carpeta y sin seguir enlaces."""
    ruta = Path(ruta_carpeta)
    vivos = []
    for patron in ("sesion_*.jsonl", "informe_sesion_*.md", "marca_*.png", "error_*.png"):
        for p in ruta.glob(patron):
            try:
                if p.is_symlink():
                    continue
                s = p.stat()
            except OSError:
                continue
            vivos.append((s.st_mtime, p, s.st_size))
    return vivos


def podar(ruta_carpeta=None, sesion_id=None):
    """Poda global con los valores activos (arranque, cada hora, el botón y el cambio de un tope).
    Se salva la parte más nueva de la sesión en curso, si la hay."""
    v = valores()
    curso = sesion_id or (activo.id if activo else None)
    vivos = _vivos(ruta_carpeta or carpeta())
    abiertas = [(f, p) for f, p, _t in vivos if p.name.startswith("sesion_")]
    if curso:
        partes = sorted(str(p) for _f, p, _t in vivos if p.name.startswith(f"sesion_{curso}_"))
        # Si esa sesión todavía no escribió acá, lo más nuevo lo está escribiendo otro proceso: se salva igual.
        actual = partes[-1] if partes else (str(max(abiertas)[1]) if abiertas else "")
    else:
        actual = str(max(abiertas)[1]) if abiertas else ""
    return _recortar(vivos, v["retencion_dias"] * 86400, v["tope_total_mb"] * 2**20,
                     min(v["tope_capturas_mb"], v["tope_total_mb"]) * 2**20, actual)


def inventario(ruta_carpeta=None):
    """(bytes usados, nº de sesiones) de la carpeta del registro, para la línea de estado y la API."""
    from .almacen import sesiones
    vivos = _vivos(ruta_carpeta or carpeta())
    return sum(t for _f, _p, t in vivos), len(sesiones())


def toca_podar():
    global ULTIMO_PODA
    return time.monotonic() - ULTIMO_PODA > 3600


def marcar_podar():
    global ULTIMO_PODA
    ULTIMO_PODA = time.monotonic()


def configurar(encendido, datos=None):
    """Activa una sesión o la drena y apaga; apagado de fábrica no crea ni consulta archivos."""
    global activo, ultimo
    if encendido and activo is None:
        activo = ultimo = Registro(datos)
    elif not encendido and activo is not None:
        registro, activo = activo, None
        registro.emitir("sesion_fin")
        registro.cerrar()
    return ultimo.estado() if ultimo else {"enabled": False, "session": None, "error": None, "dropped": 0}


atexit.register(lambda: configurar(False))
