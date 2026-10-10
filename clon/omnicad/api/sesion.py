# -*- coding: utf-8 -*-
"""
Sesión de trabajo de la API: el documento activo y cómo se modifica.

`Sesion(documento=None)` crea un documento nuevo o envuelve uno existente (el de la ventana, en el modo
en vivo). Las herramientas con `modifica=True` corren dentro de `transaccion()`:
  - son UN paso de deshacer aunque por dentro toquen el documento varias veces;
  - son atómicas: si fallan, o si algún paso del timeline queda en "error" que antes no lo estaba, el
    documento vuelve exactamente a como estaba (operaciones, parámetros, deshacer y rehacer);
  - los pasos que quedan con "aviso" nuevo se informan en `avisos` sin deshacer nada.
"""
import difflib
import json
from contextlib import contextmanager
from pathlib import Path

from ..io_archivos import abrir_externo, proyecto
from ..timeline.documento import _LIMITE_DESHACER, Documento
from .errores import desde_mensaje, error


class Sesion:
    def __init__(self, documento=None):
        self.doc = documento if documento is not None else Documento()
        self.avisos = []
        self._llamadas = 0       # llamadas en curso de registro.llamar (más de una: anidadas, p. ej. execute_code)

    @property
    def ruta(self):
        return self.doc.ruta

    def avisar(self, texto):
        self.avisos.append(str(texto))

    # ------------------------------------------------------------ archivo
    def nuevo(self, nombre="Sin título"):
        self.doc = Documento()
        self.doc.nombre = nombre
        return self.doc

    def abrir(self, ruta, unidades="mm"):
        """Proyecto .omnicad/.fclone, o un archivo de otro programa (STEP, IGES, mallas, DXF, .f3d/.f3z: ver
        `io_archivos.abrir_externo`) como documento nuevo sin ruta; sus avisos van a `avisos`."""
        ruta = Path(ruta)
        if not ruta.is_file():
            raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
        if abrir_externo.es_externo(ruta):
            self.doc, avisos = abrir_externo.documento_desde_archivo(ruta, unidades)
            for aviso in avisos:
                self.avisar(aviso)
        elif ruta.suffix.lower() not in proyecto.EXTENSIONES:
            raise error("UNSUPPORTED_FILE_TYPE", f"Formato no soportado: {ruta.suffix or '(sin extensión)'}.")
        else:
            self.doc = proyecto.abrir(ruta)
        return self.doc

    def guardar(self, ruta=None, sobrescribir=False, crear_carpetas=False):
        """Guarda el proyecto. Sin ruta (o vacía), en su archivo actual. No pisa un archivo existente distinto del
        actual salvo `sobrescribir`. Con `crear_carpetas` crea las carpetas que falten (y las borra si al final no se
        pudo guardar); sin él, una carpeta inexistente es FILE_NOT_FOUND."""
        if ruta is None or not str(ruta).strip():
            if not self.doc.ruta:
                raise error("MISSING_PATH", "El documento todavía no se guardó: falta la ruta.")
            ruta = self.doc.ruta
        ruta = Path(ruta)
        if ruta.name in ("", ".."):                           # «.», «..», «C:/»: sin nombre de archivo
            raise error("INVALID_ARGUMENTS", f"La ruta «{ruta}» no tiene nombre de archivo.",
                        "Pasá la ruta completa del proyecto, p. ej. C:/piezas/soporte.omnicad.")
        if ruta.suffix.lower() not in proyecto.EXTENSIONES:   # igual que proyecto.guardar
            ruta = ruta.with_suffix(proyecto.EXTENSION)
        actual = Path(self.doc.ruta).resolve() if self.doc.ruta else None
        if ruta.exists() and ruta.resolve() != actual and not sobrescribir:
            raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
        nuevas = crear_carpeta(ruta.parent) if crear_carpetas else []
        if not ruta.parent.is_dir():
            raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}",
                        "save_document crea las carpetas que faltan con create_folders=true.")
        # Como en Fusion, el documento toma el nombre del archivo. Se pone ANTES de escribir para que el manifiesto
        # guarde el mismo nombre que ve la sesión (si no, al reabrir con la API volvía el nombre viejo).
        nombre_anterior, self.doc.nombre = self.doc.nombre, ruta.stem
        try:
            final = proyecto.guardar(self.doc, ruta)
        except BaseException:
            self.doc.nombre = nombre_anterior
            borrar_carpetas(nuevas)
            raise
        self.doc.ruta = str(final)
        self.doc.modificado = False
        if nuevas:
            self.avisar(f"Se creó la carpeta {ruta.parent}.")
        return final

    # ------------------------------------------------------------ búsqueda por id o nombre
    def paso(self, ref):
        """Operación del timeline por id o por nombre (sin distinguir mayúsculas)."""
        ops = self.doc.operaciones
        return _buscar(ref, ops, lambda o: o.id, lambda o: o.nombre, "paso", "FEATURE_NOT_FOUND")

    def nombre_cuerpo(self, cuerpo):
        """Nombre visible: el renombrado en el navegador o el que le dio la operación."""
        return self.doc.propiedad(cuerpo.id, "nombre") or cuerpo.nombre

    def cuerpo(self, ref):
        """Cuerpo al final del timeline por id o por nombre (sin distinguir mayúsculas)."""
        cuerpos = list(self.doc.estado_final.cuerpos.values())
        return _buscar(ref, cuerpos, lambda c: c.id, self.nombre_cuerpo, "cuerpo", "BODY_NOT_FOUND")

    # ------------------------------------------------------------ transacción
    def _estados_pasos(self):
        return {o.id: (r.estado, r.mensaje) for o, r in zip(self.doc.operaciones, self.doc.resultados, strict=False)}

    @contextmanager
    def transaccion(self):
        doc = self.doc
        antes = json.dumps(doc.a_dict())
        pila, pila_rehacer, modificado = list(doc._deshacer), list(doc._rehacer), doc.modificado
        contador = doc._contador         # una llamada que falla no gasta números de id (la receta queda idéntica)
        previos = self._estados_pasos()
        try:
            yield
            if self.doc is not doc:          # la herramienta cambió de documento (nuevo / abrir)
                return
            nuevos = [(o, r) for o, r in zip(doc.operaciones, doc.resultados, strict=False)
                      if previos.get(o.id) != (r.estado, r.mensaje)]
            rotos = [(o, r) for o, r in nuevos if r.estado == "error" and previos.get(o.id, ("",))[0] != "error"]
            if rotos:
                o, r = rotos[0]
                otros = f" También quedaron con error: {', '.join(x.nombre for x, _ in rotos[1:])}." if rotos[1:] else ""
                e = desde_mensaje(r.mensaje, f"El paso «{o.nombre}» ({o.id}) quedó con error: ")
                e.mensaje += otros
                raise e
            for o, r in nuevos:
                if r.estado == "aviso":
                    self.avisar(f"{o.nombre} ({o.id}): {r.mensaje}")
            if doc._deshacer != pila:        # varios cambios internos → un solo paso de deshacer
                doc._deshacer[:] = (pila + [antes])[-_LIMITE_DESHACER:]
        except BaseException:
            if self.doc is doc and doc._deshacer != pila:
                doc._cargar(json.loads(antes))
                doc._deshacer[:], doc._rehacer[:] = pila, pila_rehacer
                doc.modificado = modificado
            if self.doc is doc:
                doc._contador = contador
            raise


def crear_carpeta(carpeta):
    """Crea `carpeta` y las que falten arriba. Devuelve las que creó, de la de más arriba a la de más abajo (para
    borrarlas si después la escritura falla). Un archivo en el camino o sin permiso: FILE_ERROR o PERMISSION_DENIED."""
    carpeta, faltan = Path(carpeta), []
    p = carpeta
    while not p.exists() and p.parent != p:
        faltan.append(p)
        p = p.parent
    faltan.reverse()
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        borrar_carpetas([f for f in faltan if f.is_dir()])
        raise error("PERMISSION_DENIED" if isinstance(e, PermissionError) else "FILE_ERROR",
                    f"No se pudo crear la carpeta {carpeta}: {e.strerror or e}") from None
    return faltan


def borrar_carpetas(carpetas):
    """Borra (de la más profunda a la de más arriba) las carpetas que creó `crear_carpeta`, si quedaron vacías."""
    for c in reversed(carpetas):
        try:
            c.rmdir()
        except OSError:
            pass


def _buscar(ref, elementos, id_de, nombre_de, que, error_kind):
    ref = str(ref).strip()
    for x in elementos:
        if id_de(x) == ref:
            return x
    clave = ref.casefold()
    hallados = [x for x in elementos if str(nombre_de(x)).casefold() == clave]
    if len(hallados) == 1:
        return hallados[0]
    if hallados:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} {que}s llamados «{ref}»: "
                    + ", ".join(id_de(x) for x in hallados) + ".")
    opciones = [id_de(x) for x in elementos] + [nombre_de(x) for x in elementos]
    parecidos = difflib.get_close_matches(ref, opciones, n=3, cutoff=0.5)
    raise error(error_kind, f"No existe el {que} '{ref}'.",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))
