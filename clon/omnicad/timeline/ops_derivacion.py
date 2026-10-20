# -*- coding: utf-8 -*-
"""INSERTAR › Insertar derivación de Fusion [ASM-DERIVE]: traer de OTRO proyecto .omnicad los cuerpos,
bocetos y parámetros elegidos, como UN paso del timeline ASOCIADO al archivo de origen.

A diferencia de «Insertar componente» (OpInsertarDiseno, que guarda la receta del otro diseño adentro y
queda independiente), la derivación guarda SOLO la ruta del origen y qué se derivó: cada recálculo
vuelve a leerlo, así que si el origen cambió, el derivado se actualiza; si el archivo no está, el paso
da un error claro. El origen es un archivo de OTRO: se lee con `io_archivos.proyecto.abrir`, que valida
el ZIP con sus topes de tamaño por miembro.
"""
from pathlib import Path

from .operaciones import BocetoResuelto, ErrorOperacion, Operacion, registrar_operacion
from .parametros import TablaParametros

_ORIGENES_EN_CURSO = set()


def _abrir_origen(ruta):
    """Documento del proyecto de origen (el lector de proyectos se ocupa de los archivos ajenos)."""
    from ..io_archivos import proyecto
    ruta = Path(str(ruta).strip()).expanduser().resolve()
    if ruta in _ORIGENES_EN_CURSO:
        raise ErrorOperacion(f"Referencia circular entre proyectos de derivación: «{ruta}».")
    _ORIGENES_EN_CURSO.add(ruta)
    try:
        otro = proyecto.abrir(ruta)
        errores = [r.mensaje for r in otro.resultados[:otro.marcador] if r.estado == "error"]
        if errores:
            raise ErrorOperacion(f"El proyecto de origen «{ruta}» tiene errores: {errores[0]}")
        return otro
    except proyecto.ErrorProyecto as e:
        raise ErrorOperacion(f"No se pudo leer el proyecto de origen «{ruta}»: {e}") from None
    except OSError as e:
        detalle = f" ({e.strerror})" if getattr(e, "strerror", None) else ""
        raise ErrorOperacion(f"No encuentro el proyecto de origen de la derivación «{ruta}»{detalle}. "
                             "Traé de vuelta el archivo o borrá este paso del timeline.") from None
    finally:
        _ORIGENES_EN_CURSO.discard(ruta)


def cuerpo_origen(estado, ref):
    """Cuerpo del estado de origen que nombra `ref` (id exacto o nombre único, sin mayúsculas); None si no está."""
    if isinstance(ref, str) and ref in estado.cuerpos:
        return estado.cuerpos[ref]
    hallados = [c for c in estado.cuerpos.values() if isinstance(ref, str)
                and str(c.nombre).casefold() == ref.casefold()]
    return hallados[0] if len(hallados) == 1 else None


def boceto_origen(estado, ref):
    """Boceto resuelto del estado de origen que nombra `ref` (id exacto o nombre único); None si no está."""
    if isinstance(ref, str) and ref in estado.bocetos:
        return estado.bocetos[ref]
    hallados = [b for b in estado.bocetos.values() if isinstance(ref, str)
                and str(b.nombre).casefold() == ref.casefold()]
    return hallados[0] if len(hallados) == 1 else None


class OpDerivacion(Operacion):
    """INSERTAR › Insertar derivación de Fusion [ASM-DERIVE]: los cuerpos, bocetos y parámetros elegidos
    de otro proyecto .omnicad entran como UN paso del timeline ASOCIADO al archivo de origen: cada
    recálculo vuelve a leerlo, así que si el origen cambió, el derivado se actualiza (lo que el origen ya
    no tiene se salta con un aviso). Los parámetros se importan por su valor resuelto, sin exigir traer
    también sus dependencias; el documento los actualiza antes de calcular los pasos siguientes.

    «archivo»: ruta del proyecto de origen. «cuerpos» y «bocetos»: ids o nombres de los del origen.
    «parametros»: nombres de los parámetros del origen."""
    TIPO, ETIQUETA, ICONO = "derivacion", "Derivación", "⇊"
    PARAMS = {"archivo": "", "cuerpos": [], "bocetos": [], "parametros": []}
    MEMORIZABLE = False     # el origen es otro archivo: la receta igual no garantiza el mismo resultado

    def ejecutar(self, estado, ctx):
        if not str(self.p["archivo"] or "").strip():
            raise ErrorOperacion("La derivación no tiene el archivo de origen.")
        if not any(self.p[k] for k in ("cuerpos", "bocetos", "parametros")):
            raise ErrorOperacion("Elegí al menos un cuerpo, boceto o parámetro del origen.")
        for clave in ("cuerpos", "bocetos", "parametros"):
            if any(not isinstance(ref, str) or not ref.strip() for ref in self.p[clave]):
                raise ErrorOperacion(f"«{clave}» debe contener nombres o ids de texto no vacíos.")
        otro = _abrir_origen(self.p["archivo"])
        origen, valores = otro.estado_final, otro.parametros.valores()
        self._parametros_derivados = []
        for nombre in self.p["parametros"]:
            if nombre in valores:
                p = otro.parametros.obtener(nombre)
                self._parametros_derivados.append(dict(p.a_dict(), expresion=repr(valores[nombre])))
            else:
                ctx.aviso(f"El parámetro «{nombre}» ya no está en el origen: no se derivó.")
        for ref in self.p["cuerpos"]:
            c = cuerpo_origen(origen, ref)
            if c is None:
                ctx.aviso(f"El cuerpo «{ref}» ya no está en el origen: no se derivó.")
                continue
            estado.nuevo_cuerpo(self.id, c.forma, getattr(c, "tipo", "solido"), nombre=c.nombre,
                                apariencia=c.apariencia, material=c.material)
        for ref in self.p["bocetos"]:
            br = boceto_origen(origen, ref)
            if br is None:
                ctx.aviso(f"El boceto «{ref}» ya no está en el origen: no se derivó.")
                continue
            bid = f"{self.id}.{br.op_id}"
            estado.bocetos[bid] = BocetoResuelto(bid, br.nombre, br.boceto, br.plano, br.perfiles, br.solver)

    def copiar_parametros(self, tabla):
        """Tabla con los valores derivados de la última ejecución; no altera la tabla ni la receta."""
        nueva = TablaParametros.desde_lista(tabla.a_lista())
        marca = f"Derivado de «{Path(self.p['archivo']).expanduser().resolve()}»."
        for datos in self._parametros_derivados:
            nombre = datos["nombre"]
            comentario = f"{datos['comentario']}\n{marca}".strip()
            if nombre in nueva:
                if not nueva.obtener(nombre).comentario.endswith(marca):
                    raise ErrorOperacion(f"El parámetro «{nombre}» ya existe en este documento; renombralo "
                                         "antes de derivarlo para no sobrescribirlo.")
                nueva.modificar(nombre, datos["expresion"], comentario)
                nueva.obtener(nombre).tipo = datos["tipo"]
            else:
                nueva.agregar(nombre, datos["expresion"], datos["tipo"], comentario)
        return nueva


registrar_operacion(OpDerivacion)
