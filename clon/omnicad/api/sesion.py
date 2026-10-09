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

from ..io_archivos import proyecto
from ..timeline.documento import _LIMITE_DESHACER, Documento
from .errores import desde_mensaje, error


class Sesion:
    def __init__(self, documento=None):
        self.doc = documento if documento is not None else Documento()
        self.avisos = []

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

    def abrir(self, ruta):
        ruta = Path(ruta)
        if not ruta.is_file():
            raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
        self.doc = proyecto.abrir(ruta)
        return self.doc

    def guardar(self, ruta=None, sobrescribir=False):
        """Guarda el proyecto. No pisa un archivo existente distinto del actual salvo `sobrescribir`."""
        if ruta is None:
            if not self.doc.ruta:
                raise error("MISSING_PATH", "El documento todavía no se guardó: falta la ruta.")
            ruta = self.doc.ruta
        ruta = Path(ruta)
        if ruta.suffix.lower() not in proyecto.EXTENSIONES:   # igual que proyecto.guardar
            ruta = ruta.with_suffix(proyecto.EXTENSION)
        actual = Path(self.doc.ruta).resolve() if self.doc.ruta else None
        if ruta.exists() and ruta.resolve() != actual and not sobrescribir:
            raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
        if not ruta.parent.is_dir():
            raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
        # Como en Fusion, el documento toma el nombre del archivo. Se pone ANTES de escribir para que el manifiesto
        # guarde el mismo nombre que ve la sesión (si no, al reabrir con la API volvía el nombre viejo).
        nombre_anterior, self.doc.nombre = self.doc.nombre, ruta.stem
        try:
            final = proyecto.guardar(self.doc, ruta)
        except BaseException:
            self.doc.nombre = nombre_anterior
            raise
        self.doc.ruta = str(final)
        self.doc.modificado = False
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
            raise


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
