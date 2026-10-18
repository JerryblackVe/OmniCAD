# -*- coding: utf-8 -*-
"""Elección de los dos motores y despacho geométrico, sin importar Qt ni OCP."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache, wraps
from importlib import import_module
from importlib.util import find_spec
import inspect
import os
import sys
from types import CodeType


MOTORES = ("opencascade", "omnikernel")
_fijo = ContextVar("motor_geometrico", default=None)
_preferencias = None


def configurar_preferencias(preferencias):
    """La interfaz entrega su lector; el núcleo no conoce QSettings ni Qt."""
    global _preferencias
    _preferencias = preferencias


def motor_activo():
    elegido = _fijo.get()
    if elegido is None:
        elegido = os.environ.get("OMNICAD_MOTOR")
        if not elegido:
            elegido = _preferencias["geometria/motor"] if _preferencias is not None else "opencascade"
            if elegido == "omnikernel" and version_omnikernel() is None:
                elegido = "opencascade"     # preferencia guardada en otra instalación, sin el módulo nativo
    if elegido not in MOTORES:
        raise ValueError(f"Motor geométrico desconocido: {elegido!r}.")
    return elegido


@cache
def version_omnikernel():
    """Versión del módulo nativo instalado, o None. No cambia mientras corre la app."""
    if find_spec("omnikernel") is None:
        return None
    try:
        return import_module("omnikernel").__version__
    except (ImportError, OSError):
        return None


def elegir_motor(nombre):
    """Cambia el motor de esta sesión: la preferencia si la interfaz la entregó (y no hay OMNICAD_MOTOR), si no la
    variable de entorno del proceso. No recalcula: el recálculo siguiente lo fija y descarta la caché del otro."""
    if nombre not in MOTORES:
        raise ValueError(f"Motor geométrico desconocido: {nombre!r}.")
    if nombre == "omnikernel" and version_omnikernel() is None:
        raise ValueError("OmniKernel no está instalado en este Python.")
    if _preferencias is not None and not os.environ.get("OMNICAD_MOTOR"):
        _preferencias["geometria/motor"] = nombre
    else:
        os.environ["OMNICAD_MOTOR"] = nombre


@contextmanager
def fijar_motor(nombre=None):
    nombre = motor_activo() if nombre is None else nombre
    if nombre not in MOTORES:
        raise ValueError(f"Motor geométrico desconocido: {nombre!r}.")
    token = _fijo.set(nombre)
    try:
        yield nombre
    finally:
        _fijo.reset(token)


def sin_soporte(operacion):
    from .geometria import ErrorGeometria
    e = ErrorGeometria(f"OmniKernel todavía no hace {operacion}. Podés elegir OpenCascade en Preferencias.")
    e.error_kind = "MOTOR_SIN_SOPORTE"
    raise e


def _comprobar_formas(valor, elegido):
    modulo = type(valor).__module__
    nativo = sys.modules.get("omnikernel")
    es_nativo = nativo is not None and isinstance(valor, nativo.Cuerpo)
    if (elegido == "omnikernel" and modulo.startswith("OCP")) or (elegido == "opencascade" and es_nativo):
        from .geometria import ErrorGeometria
        e = ErrorGeometria("La forma pertenece al otro motor geométrico; recalculá el documento completo.")
        e.error_kind = "MOTOR_INCOMPATIBLE"
        raise e
    if isinstance(valor, dict):
        valor = valor.values()
    elif not isinstance(valor, (list, tuple)):
        return
    for item in valor:
        _comprobar_formas(item, elegido)


def _usa_opencascade(codigo, nombres_occ):
    """¿El código (o una función anidada) nombra algo de OCP? Los nombres los declara `_iniciar_opencascade`."""
    return (any(n in nombres_occ or n.startswith("OCP") for n in codigo.co_names)
            or any(_usa_opencascade(c, nombres_occ) for c in codigo.co_consts if isinstance(c, CodeType)))


def registrar(espacio, iniciar, nombres=None):
    """Conserva las firmas públicas; las implementaciones de OCC se cargan solo al elegirlo.

    Una función que no nombra nada de OCP (validaciones, búsquedas, política de la app) es común a los dos
    motores: corre tal cual, salvo que `omnikernel/<modulo>.py` traiga la suya."""
    modulo = espacio["__name__"].rsplit(".", 1)[-1]
    cargado = motor_activo() == "opencascade"
    nombres_occ = set(iniciar.__code__.co_names)

    def envolver(funcion):
        comun = not _usa_opencascade(funcion.__code__, nombres_occ)

        @wraps(funcion)
        def ejecutar(*args, **kwargs):
            nonlocal cargado
            elegido = motor_activo()
            _comprobar_formas(args, elegido)
            _comprobar_formas(kwargs, elegido)
            if comun and (elegido == "opencascade" or _alternativa(modulo, funcion.__name__) is None):
                return funcion(*args, **kwargs)
            if elegido == "opencascade":
                if not cargado:
                    iniciar()
                    cargado = True
                return funcion(*args, **kwargs)
            ruta = f"{__package__}.omnikernel.{modulo}"
            try:
                alternativa = import_module(ruta)
            except ModuleNotFoundError as e:
                if e.name == ruta:
                    sin_soporte(f"{modulo}.{funcion.__name__}")
                raise
            implementacion = getattr(alternativa, funcion.__name__, None)
            if implementacion is None:
                sin_soporte(f"{modulo}.{funcion.__name__}")
            try:
                return implementacion(*args, **kwargs)
            except import_module("omnikernel").ErrorOmniKernel as e:
                if e.codigo in ("UnsupportedGeometry", "UnsupportedMode"):
                    sin_soporte(f"{modulo}.{funcion.__name__} ({e.mensaje})")
                from .geometria import ErrorGeometria
                raise ErrorGeometria(e.mensaje) from e
        return ejecutar

    def guardar(clase, metodo):
        """Un método de clase que nombra OCP (p. ej. `Plano.ax2`) es de OpenCascade: con el otro motor no corre."""
        @wraps(metodo)
        def ejecutar(*args, **kwargs):
            nonlocal cargado
            if motor_activo() != "opencascade":
                sin_soporte(f"{modulo}.{clase}.{metodo.__name__}")
            if not cargado:
                iniciar()
                cargado = True
            return metodo(*args, **kwargs)
        return ejecutar

    for nombre, funcion in tuple(espacio.items()):
        if (inspect.isfunction(funcion) and funcion.__module__ == espacio["__name__"]
                and nombre != iniciar.__name__ and (nombres is None or nombre in nombres)):
            espacio[nombre] = envolver(funcion)
        elif inspect.isclass(funcion) and funcion.__module__ == espacio["__name__"] and nombres is None:
            for atributo, valor in tuple(vars(funcion).items()):
                envoltura = type(valor) if isinstance(valor, (staticmethod, classmethod)) else None
                metodo = valor.__func__ if envoltura else valor
                if inspect.isfunction(metodo) and _usa_opencascade(metodo.__code__, nombres_occ):
                    nuevo = guardar(nombre, metodo)
                    setattr(funcion, atributo, envoltura(nuevo) if envoltura else nuevo)


def _alternativa(modulo, nombre):
    try:
        return getattr(import_module(f"{__package__}.omnikernel.{modulo}"), nombre, None)
    except ModuleNotFoundError as e:
        if e.name == f"{__package__}.omnikernel.{modulo}":
            return None
        raise


def recalculo(funcion):
    """Fija un motor durante todo el recálculo y descarta la caché de un motor diferente."""
    @wraps(funcion)
    def ejecutar(doc, desde=0):
        elegido = motor_activo()
        if getattr(doc, "motor", None) != elegido:
            doc._cache.clear()
            desde = 0
        with fijar_motor(elegido):
            doc.motor = elegido
            return funcion(doc, desde)
    return ejecutar
