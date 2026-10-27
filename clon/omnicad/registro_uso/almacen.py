"""Lectura de las sesiones del registro local, también desde otro proceso (CLI o MCP en vivo).

El escritor hace flush de cada línea completa: el lector nunca necesita cerrar la app.
"""
import json
import re
import time

from . import carpeta

_PATRON = re.compile(r"sesion_(?P<id>.+)_(?P<parte>\d{4})\.jsonl\Z")
_SESION = re.compile(r"[A-Za-z0-9_.-]{1,200}\Z")


def sesiones():
    """IDs de sesión con al menos un archivo, del más nuevo al más viejo."""
    vistas = {}
    for ruta in carpeta().glob("sesion_*.jsonl"):
        m = _PATRON.fullmatch(ruta.name)
        if m:
            try:
                fecha = ruta.stat().st_mtime
            except OSError:
                continue
            vistas[m.group("id")] = max(vistas.get(m.group("id"), 0), fecha)
    return [s for s, _ in sorted(vistas.items(), key=lambda x: x[1], reverse=True)]


def ultima_sesion():
    lista = sesiones()
    return lista[0] if lista else None


def rutas(sesion):
    """Partes de una sesión, en orden. Una sesión inexistente o con un id raro devuelve []."""
    if not isinstance(sesion, str) or not _SESION.fullmatch(sesion):
        return []
    resultado = []
    for ruta in carpeta().glob(f"sesion_{sesion}_*.jsonl"):
        if _PATRON.fullmatch(ruta.name):
            resultado.append(ruta)
    return sorted(resultado, key=lambda p: p.name)


def _linea(cruda):
    try:
        evento = json.loads(cruda)
    except (ValueError, UnicodeDecodeError):
        return None
    return evento if isinstance(evento, dict) and isinstance(evento.get("seq"), int) else None


def eventos(sesion=None, desde=0, tipos=None, limite=None):
    """Eventos con seq > desde de una sesión (por defecto la última), filtrados y acotados."""
    sesion = sesion or ultima_sesion()
    if not sesion:
        return []
    desde, limite = int(desde or 0), None if limite is None else max(0, int(limite))
    tipos = set(tipos) if tipos else None
    salida = []
    for ruta in rutas(sesion):
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                for cruda in f:
                    evento = _linea(cruda)
                    if (evento is not None and evento["seq"] > desde
                            and (tipos is None or evento.get("tipo") in tipos)):
                        salida.append(evento)
        except OSError:
            continue
    return salida[-limite:] if limite else salida


def activa(sesion=None):
    """Verdadero si la sesión se escribió hace menos de 10 s (la app la tiene abierta)."""
    sesion = sesion or ultima_sesion()
    if not sesion:
        return False
    archivos = rutas(sesion)
    try:
        fecha = max(p.stat().st_mtime for p in archivos)
    except (OSError, ValueError):
        return False
    return bool(archivos) and time.time() - fecha < 10


class Lector:
    """Tail incremental: recuerda el byte de cada parte y entrega solo líneas completas nuevas."""

    def __init__(self, sesion=None, desde=0):
        self.sesion = sesion or ultima_sesion()
        self.ultimo_seq = int(desde or 0)
        self.offsets = {}

    def al_final(self):
        """Salta lo ya escrito: el siguiente `nuevos()` entrega solo lo que venga después."""
        if not self.sesion:
            return self
        for ruta in rutas(self.sesion):
            try:
                self.offsets[str(ruta)] = ruta.stat().st_size
            except OSError:
                continue
        return self

    def nuevos(self):
        """Lista de eventos nuevos en orden. Una línea a medio escribir queda para la próxima vuelta."""
        if not self.sesion:
            return []
        salida = []
        for ruta in rutas(self.sesion):
            clave = str(ruta)
            offset = self.offsets.setdefault(clave, 0)
            try:
                with open(ruta, "rb") as f:
                    f.seek(offset)
                    datos = f.read()
            except OSError:
                continue
            if not datos:
                continue
            partes = datos.split(b"\n")
            resto = partes.pop()
            for cruda in partes:
                evento = _linea(cruda.decode("utf-8", "replace"))
                if evento is not None and evento["seq"] > self.ultimo_seq:
                    self.ultimo_seq = evento["seq"]
                    salida.append(evento)
            self.offsets[clave] = offset + len(datos) - len(resto)
        return sorted(salida, key=lambda e: e["seq"])
