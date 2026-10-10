# -*- coding: utf-8 -*-
"""
Lector del formato binario SAB (ACIS / ShapeManager de Autodesk), el que Fusion guarda dentro del .f3d en
`Breps.BlobParts/BREP.*.smbh`. Implementación propia a partir de la estructura pública del formato ACIS
(cabecera, valores con etiqueta de un byte, registros que terminan en «#», subtipos entre «{ }»). Para los números de
etiqueta y el orden de la cabecera se consultó, como referencia de formato, InventorLoader de Jens M. Plonka
(https://github.com/jmplonka/InventorLoader, GPL-2.0); no se copió código.

Un registro es una entidad (body, face, plane-surface…) con una lista de campos: punteros a otros registros
(`Puntero`), enteros, enumerados (`Enumerado`), reales, vectores (tuplas de 3), cadenas, lógicos (True/False) y
subtipos (`Subtipo`, datos anidados de curvas y superficies spline). Los subtipos se numeran en el orden en que
aparecen en el archivo y `{ ref N }` reutiliza el N-ésimo: `ArchivoSAB.resolver` lo sigue.

Solo se leen los registros anteriores a la sección de historia (`Begin-of-ASM-History`): la historia guarda
estados viejos del modelo, no el actual. Sin Qt y sin OCC.
"""
import struct

FORMATOS = ("ACIS BinaryFile", "ASM BinaryFile4", "ASM BinaryFile8")
MARCAS_FIN = ("Begin-of-", "End-of-")    # Begin-of-ASM-History-Data, End-of-ASM-data, End-of-ACIS-data…


class ErrorSAB(ValueError):
    """El bloque no es SAB válido o está truncado."""


class Puntero(int):
    """Referencia a otro registro por su índice (-1 = ninguno)."""
    __slots__ = ()


class Enumerado(int):
    """Valor de un enumerado de ACIS (cierre de una spline, convexidad…)."""
    __slots__ = ()


class Subtipo:
    """Datos anidados entre «{ }»: `nombre` (exact_int_cur, cyl_spl_sur, ref…) y `items` (valores y subtipos)."""
    __slots__ = ("nombre", "items", "indice")

    def __init__(self, nombre, indice):
        self.nombre, self.items, self.indice = nombre, [], indice

    def __repr__(self):
        return f"Subtipo({self.nombre}#{self.indice}, {len(self.items)} items)"


class Entidad:
    __slots__ = ("indice", "tipo", "campos")

    def __init__(self, indice, tipo, campos):
        self.indice, self.tipo, self.campos = indice, tipo, campos

    def __repr__(self):
        return f"Entidad({self.indice}, {self.tipo})"


class ArchivoSAB:
    """Resultado de `leer`: cabecera, entidades (índice = posición en el archivo) y tabla de subtipos."""

    def __init__(self, cabecera, entidades, subtipos):
        self.cabecera, self.entidades, self.subtipos = cabecera, entidades, subtipos

    def entidad(self, ptr):
        """La entidad apuntada por `ptr`, o None si es -1 o está fuera de la sección leída."""
        if ptr is None or ptr < 0 or ptr >= len(self.entidades):
            return None
        return self.entidades[ptr]

    def resolver(self, sub):
        """Sigue las referencias `{ ref N }` hasta el subtipo definido."""
        vistos = 0
        while sub is not None and sub.nombre == "ref":
            n = sub.items[0] if sub.items else -1
            sub = self.subtipos[n] if 0 <= n < len(self.subtipos) else None
            vistos += 1
            if vistos > 64:
                raise ErrorSAB("Referencia circular entre subtipos.")
        return sub

    def de_tipo(self, tipo):
        return [e for e in self.entidades if e is not None and e.tipo == tipo]


def es_sab(datos):
    return bytes(datos[:15]).decode("latin1") in FORMATOS


def leer(datos):
    """Lee un bloque SAB. Devuelve ArchivoSAB."""
    datos = bytes(datos)
    formato = datos[:15].decode("latin1")
    if formato not in FORMATOS:
        raise ErrorSAB("No es un bloque SAB de ACIS/ShapeManager.")
    ancho = 8 if formato.endswith("8") else 4
    entero = "<q" if ancho == 8 else "<i"
    p = 15
    version, _registros, _cuerpos, _banderas = struct.unpack_from("<4" + ("q" if ancho == 8 else "I"), datos, p)
    p += 4 * ancho
    lector = _Lector(datos, p, entero, ancho)
    cab = [lector.valor() for _ in range(6)]
    cabecera = {"formato": formato, "version": version, "producto": cab[0], "version_asm": cab[1], "fecha": cab[2],
                "escala": cab[3], "resabs": cab[4], "resnor": cab[5]}
    entidades = []
    while not lector.fin():
        ent = lector.registro(len(entidades))
        if ent is None:
            break
        if ent.tipo.startswith(MARCAS_FIN):
            break
        entidades.append(ent)
    return ArchivoSAB(cabecera, entidades, lector.subtipos)


class _Lector:
    def __init__(self, d, p, entero, ancho):
        self.d, self.p, self.entero, self.ancho = d, p, entero, ancho
        self.subtipos = []

    def fin(self):
        return self.p >= len(self.d)

    def _token(self):
        d, p = self.d, self.p
        if p >= len(d):
            raise ErrorSAB("Bloque SAB truncado.")
        t = d[p]
        p += 1
        if t == 0x06:
            v = struct.unpack_from("<d", d, p)[0]
            p += 8
        elif t == 0x0C:
            v = Puntero(struct.unpack_from(self.entero, d, p)[0])
            p += self.ancho
        elif t in (0x13, 0x14):
            v = struct.unpack_from("<3d", d, p)
            p += 24
        elif t == 0x04:
            v = struct.unpack_from(self.entero, d, p)[0]
            p += self.ancho
        elif t == 0x15:
            v = Enumerado(struct.unpack_from(self.entero, d, p)[0])
            p += self.ancho
        elif t in (0x07, 0x0D, 0x0E):
            n = d[p]
            v = d[p + 1:p + 1 + n].decode("latin1")
            p += 1 + n
        elif t == 0x0A:
            v = True
        elif t == 0x0B:
            v = False
        elif t in (0x0F, 0x10, 0x11):
            v = None
        elif t == 0x08:
            n = struct.unpack_from("<H", d, p)[0]
            v = d[p + 2:p + 2 + n].decode("latin1")
            p += 2 + n
        elif t in (0x09, 0x12):
            n = struct.unpack_from("<I", d, p)[0]
            v = d[p + 4:p + 4 + n].decode("latin1")
            p += 4 + n
        elif t == 0x02:
            v = d[p]
            p += 1
        elif t == 0x03:
            v = struct.unpack_from("<h", d, p)[0]
            p += 2
        elif t == 0x05:
            v = struct.unpack_from("<f", d, p)[0]
            p += 4
        elif t == 0x16:
            v = struct.unpack_from("<2d", d, p)
            p += 16
        elif t == 0x17:
            v = struct.unpack_from("<q", d, p)[0]
            p += 8
        else:
            raise ErrorSAB(f"Etiqueta SAB desconocida 0x{t:02X} en el byte {self.p}.")
        self.p = p
        return t, v

    def valor(self):
        return self._token()[1]

    def registro(self, indice):
        nombre = []
        while True:
            t, v = self._token()
            if t in (0x0D, 0x0E):
                nombre.append(v)
                if t == 0x0D:
                    break
            elif t == 0x11 and not nombre:
                continue
            else:
                raise ErrorSAB(f"Registro SAB sin nombre en el byte {self.p}.")
        tipo = "-".join(nombre)
        if tipo.startswith(MARCAS_FIN):            # la marca final puede no tener «#»: no se leen sus campos
            return Entidad(indice, tipo, [])
        campos = []
        pila = [campos]
        while True:
            t, v = self._token()
            if t == 0x11:
                if len(pila) != 1:
                    raise ErrorSAB(f"Subtipo sin cerrar en el registro {indice} ({tipo}).")
                return Entidad(indice, tipo, campos)
            if t == 0x0F:
                t2, v2 = self._token()
                if t2 not in (0x07, 0x0D, 0x0E):
                    raise ErrorSAB(f"Subtipo sin nombre en el registro {indice} ({tipo}).")
                if v2 == "ref":
                    sub = Subtipo("ref", -1)
                else:
                    sub = Subtipo(v2, len(self.subtipos))
                    self.subtipos.append(sub)
                pila[-1].append(sub)
                pila.append(sub.items)
            elif t == 0x10:
                if len(pila) == 1:
                    raise ErrorSAB(f"Cierre de subtipo sobrante en el registro {indice} ({tipo}).")
                pila.pop()
            else:
                pila[-1].append(v)
