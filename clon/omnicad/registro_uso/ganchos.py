"""Instrumentación compartida: sin Qt y sin alterar resultados ni excepciones."""
import inspect
import time
import traceback
from functools import wraps
from pathlib import Path

from .. import registro_uso as registro


def calculo(funcion):
    """Difiere el enriquecimiento geométrico hasta terminar el recálculo (OCP retiene el GIL)."""
    @wraps(funcion)
    def ejecutar(*args, **kwargs):
        r = registro.activo
        if r is None:
            return funcion(*args, **kwargs)
        with r._cerrojo:
            r._calculos += 1
            r._calculo_libre.clear()
        try:
            return funcion(*args, **kwargs)
        finally:
            with r._cerrojo:
                r._calculos -= 1
                if not r._calculos:
                    r._calculo_libre.set()
    return ejecutar


def error(excepcion=None, *, origen="operacion", comando="", mensaje=""):
    """Categoría y traza sin mensajes, código fuente, rutas ni variables locales."""
    if registro.activo is None:
        return
    traza = []
    if excepcion is not None:
        for marco in traceback.extract_tb(excepcion.__traceback__)[-5:]:
            if "/omnicad/" in marco.filename.replace("\\", "/"):
                traza.append({"linea": marco.lineno, "categoria": marco.name})
    registro.activo.emitir("error", {"origen": origen, "comando": comando,
        "excepcion": type(excepcion).__name__ if excepcion is not None else "AvisoOperacion",
        "mensaje": str(excepcion) if excepcion is not None else mensaje, "traza": traza})


def archivo(tipo):
    """Decora un punto de E/S con argumento `ruta`; solo mide si el registro está activo."""
    def decorar(funcion):
        firma = inspect.signature(funcion)

        @wraps(funcion)
        def medir(*args, **kwargs):
            r = registro.activo
            if r is None:
                return funcion(*args, **kwargs)
            ruta = Path(firma.bind(*args, **kwargs).arguments["ruta"])
            inicio, exito = time.perf_counter(), False
            try:
                resultado = funcion(*args, **kwargs)
                exito = True
                if isinstance(resultado, Path):
                    ruta = resultado
                return resultado
            except Exception as e:
                error(e, origen=tipo)
                raise
            finally:
                try:
                    tamano = ruta.stat().st_size
                except OSError:
                    tamano = None
                r.emitir(tipo, {"formato": ruta.suffix.lower().lstrip("."), "tamano": tamano,
                               "duracion_ms": (time.perf_counter() - inicio) * 1000, "exito": exito})
        return medir
    return decorar


def medidas(cuerpos, cache=None):
    """Mide las formas en el escritor, sin volver a recorrer el documento de la UI."""
    from ..nucleo import geometria as geo
    volumen = 0.0
    for tipo, forma in cuerpos:
        if tipo != "solido":
            continue
        clave = id(forma)
        if cache is not None and clave in cache:
            valor = cache[clave]
        else:
            try:
                valor = geo.volumen_exacto(forma)
            except Exception:
                valor = None
            if cache is not None:
                cache[clave] = valor
        if valor is None:
            return {"cuerpos": len(cuerpos), "volumen": None}
        volumen += valor
    return {"cuerpos": len(cuerpos), "volumen": volumen}
