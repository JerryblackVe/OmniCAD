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

TOPE_TOTAL = 50 * 1024 * 1024
TOPE_ARCHIVO = 5 * 1024 * 1024
RETENCION = 14 * 86400
activo = None
ultimo = None
_CLAVE = re.compile(r"[A-Za-z_][A-Za-z_0-9.-]{0,95}\Z")
_IDENTIFICADORES = {"comando", "tipo_op", "accion", "origen", "formato", "excepcion", "categoria", "paso"}


def carpeta():
    """Carpeta privada del registro; la variable solo permite aislar pruebas."""
    return Path(os.environ.get("OMNICAD_REGISTRO_DIR") or carpeta_datos() / "registro")


def _privado(valor, clave="", nivel=0, identificadores=True):
    if nivel > 4:
        return None
    if valor is None or isinstance(valor, bool):
        return valor
    if isinstance(valor, (float, int)):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, str):
        if identificadores and clave in _IDENTIFICADORES and _CLAVE.fullmatch(valor):
            return valor
        return {"longitud": len(valor)}
    if isinstance(valor, dict):
        return {k: _privado(v, k, nivel + 1, identificadores and k != "valores") for k, v in list(valor.items())[:64]
                if isinstance(k, str) and _CLAVE.fullmatch(k)}
    if isinstance(valor, (tuple, list)):
        return [_privado(v, clave, nivel + 1, identificadores) for v in valor[:64]]
    return None


class Registro:
    """Un productor rápido y un único escritor; cola acotada y fallos visibles en estado()."""

    def __init__(self, datos=None, destino=None, tope_total=TOPE_TOTAL, tope_archivo=TOPE_ARCHIVO,
                 retencion=RETENCION):
        self.carpeta = Path(destino) if destino else carpeta()
        self.tope_total, self.tope_archivo, self.retencion = tope_total, min(tope_archivo, tope_total), retencion
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
        self.carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.hilo = threading.Thread(target=self._escribir, name="registro_uso", daemon=True)
        self.emitir("sesion_inicio", {"version": VERSION, "so": platform.system(), **(datos or {})}, cabecera=True)
        self.hilo.start()

    def emitir(self, tipo, datos=None, *, cabecera=False, medidas=None):
        """Encola sin E/S. Devuelve seq o None si la cola está llena o el escritor falló."""
        if self._cerrado or self.fallo or not _CLAVE.fullmatch(tipo):
            return None
        seguros = _privado(datos or {})
        if cabecera:
            for k in ("version", "so", "gpu", "opengl", "proyecto"):
                v = (datos or {}).get(k)
                if isinstance(v, str):
                    seguros[k] = v.replace("\\", "/").rsplit("/", 1)[-1][:160]
        with self._cerrojo:
            if self._cerrado:
                return None
            self.seq += 1
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
        archivos = []
        for patron in ("sesion_*.jsonl", "informe_sesion_*.md", "marca_*.png"):
            for p in self.carpeta.glob(patron):
                if p.is_symlink():
                    continue
                s = p.stat()
                archivos.append((s.st_mtime, p, s.st_size))
        total = sum(s for _, _, s in archivos)
        for fecha, p, tamano in sorted(archivos):
            if p == actual:
                continue
            if time.time() - fecha > self.retencion or total + reserva > self.tope_total:
                p.unlink()
                total -= tamano
        if total + reserva > self.tope_total:
            raise OSError("El registro alcanzó su tope de tamaño.")

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
                        evento["datos"]["antes"], evento["datos"]["despues"] = (medir(cs) for cs in medidas)
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
        except OSError as e:
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
                "error": self.fallo, "dropped": self.descartados}


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
