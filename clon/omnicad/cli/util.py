# -*- coding: utf-8 -*-
"""Piezas comunes de la CLI: salida, argumentos y sesión. Todo import pesado (`omnicad.api`) es perezoso."""
import difflib
import json
import os
import sys
import tempfile
from pathlib import Path

LIMITE_TEXTO = 1500   # el texto humano de un resultado se recorta acá (con --json sale entero)


class UsoError(Exception):
    """Error de uso de la CLI (argumentos, archivo inexistente): código de salida 2."""

    def __init__(self, mensaje, pistas=()):
        super().__init__(mensaje)
        self.mensaje, self.pistas = mensaje, list(pistas)


def api():
    """El paquete `omnicad.api` (tarda ~2 s en importarse por OCP/scipy: solo se carga si hace falta)."""
    from .. import api as modulo
    return modulo


def usar_utf8():
    """En Windows la consola puede no ser UTF-8: los textos con tildes no tienen que romper la salida."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def a_json(objeto):
    return json.dumps(objeto, ensure_ascii=False, separators=(",", ":"), default=str)


def decir(texto="", error=False):
    print(texto, file=sys.stderr if error else sys.stdout)


# ---------------------------------------------------------------- catálogo
def indice_catalogo():
    return {h["nombre"]: h for h in api().catalogo()}


def exigir_herramienta(nombre, indice):
    if nombre not in indice:
        parecidas = difflib.get_close_matches(nombre, list(indice), n=3)
        raise UsoError(f"No existe la herramienta '{nombre}'.",
                       [f"¿Quisiste decir: {', '.join(parecidas)}?"] if parecidas
                       else ["`omnicad tools` lista las herramientas."])
    return indice[nombre]


# ---------------------------------------------------------------- argumentos de una herramienta
def _valor(texto, propiedad):
    """`clave=valor`: JSON si se puede (números, listas, true/false), si no texto. Si el esquema pide solo
    texto, se respeta tal cual ('name=123' es el texto "123")."""
    if propiedad.get("type") == "string":
        return texto
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def _leer_json(texto, origen):
    try:
        valor = json.loads(texto)
    except ValueError as e:
        raise UsoError(f"{origen} no es JSON válido: {e}") from None
    if not isinstance(valor, dict):
        raise UsoError(f"{origen} tiene que ser un objeto JSON {{...}}.")
    return valor


def construir_args(ns, herramienta):
    """Une --args / --args-file con los pares clave=valor (estos ganan)."""
    args = {}
    if getattr(ns, "args", None) is not None:
        args = _leer_json(ns.args, "--args")
    elif getattr(ns, "args_file", None) is not None:
        if ns.args_file == "-":
            texto = sys.stdin.read()
        else:
            ruta = Path(ns.args_file)
            if not ruta.is_file():
                raise UsoError(f"No existe el archivo de argumentos: {ruta}")
            texto = ruta.read_text(encoding="utf-8-sig")
        args = _leer_json(texto, f"El archivo {ns.args_file}")
    props = herramienta["esquema"]["properties"]
    for par in getattr(ns, "pares", None) or []:
        clave, _, texto = par.partition("=")
        args[clave] = _valor(texto, props.get(clave, {}))
    return args


# ---------------------------------------------------------------- sesión y archivos
def abrir_sesion(doc):
    """(sesion, documento_abierto, avisos_de_apertura, error). Sin `doc`: sesión con documento vacío."""
    sesion = api().Sesion()
    if not doc:
        return sesion, None, [], None
    ruta = Path(doc)
    if not ruta.is_file():
        raise UsoError(f"No existe el archivo: {ruta}", ["Para crearlo: omnicad new <archivo.omnicad>"])
    r = api().llamar(sesion, "open_document", {"path": str(ruta)})
    if not r["ok"]:
        return sesion, None, [], r
    return sesion, sesion.doc, r["avisos"], None


def guardar(sesion):
    """Guarda el documento abierto de vuelta (atómico, lo hace `proyecto.guardar`). Devuelve (error, ruta):
    si guardar falla, `error` es el dict de esa falla: la herramienta salió bien pero el archivo NO cambió."""
    g = api().llamar(sesion, "save_document", {})
    if g["ok"]:
        return None, g["result"]["path"]
    g["mensaje"] = "La herramienta salió bien pero NO se pudo guardar el archivo: " + g["mensaje"]
    return g, None


def puede_guardar(sesion, abierto):
    """Solo se guarda si hay --doc y la herramienta no cambió de documento (new_document / open_document)."""
    return abierto is not None and sesion.doc is abierto


def escribir_png(imagen, ruta=None):
    """Escribe un `Imagen` en `ruta` (o en un temporal). Devuelve su descripción JSON."""
    if ruta is None:
        fd, nombre = tempfile.mkstemp(prefix="omnicad_", suffix=".png")
        os.close(fd)
        ruta = Path(nombre)
    else:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(imagen.png)
    return {"path": str(ruta.resolve()), "format": "png", "width": imagen.ancho, "height": imagen.alto,
            "size_bytes": len(imagen.png)}


def sacar_imagenes(objeto, ruta=None):
    """Reemplaza cada `Imagen` del resultado por la ruta de su PNG (nunca base64 por consola). La primera va a
    `ruta` si se pidió; las demás, a archivos con sufijo _2, _3…; sin `ruta`, todas a temporales."""
    contador = [0]
    clase = api().Imagen

    def recorrer(x):
        if isinstance(x, clase):
            contador[0] += 1
            destino = ruta
            if ruta is not None and contador[0] > 1:
                destino = Path(ruta).with_name(f"{Path(ruta).stem}_{contador[0]}{Path(ruta).suffix}")
            try:
                return escribir_png(x, destino)
            except OSError as e:
                raise UsoError(f"No se pudo escribir la imagen en {destino}: {e}") from None
        if isinstance(x, dict):
            return {k: recorrer(v) for k, v in x.items()}
        if isinstance(x, list):
            return [recorrer(v) for v in x]
        return x

    return recorrer(objeto)


# ---------------------------------------------------------------- salida
def _resumen_escena(r):
    cuerpos, params = r.get("bodies", []), r.get("parameters", [])
    lineas = [f"{r['name']}  ({r['path'] or 'sin guardar'})",
              f"{len(cuerpos)} cuerpo(s), {len(r.get('sketches', []))} boceto(s), {r['timeline_steps']} paso(s), "
              f"{len(params)} parámetro(s)"]
    for c in cuerpos:
        caja = (c.get("bounding_box") or {}).get("size")
        lineas.append(f"  cuerpo {c['id']} «{c['name']}» {c['type']}  vol={c['volume']} mm³"
                      + (f"  caja={' x '.join(str(v) for v in caja)} mm" if caja else ""))
    for p in params:
        lineas.append(f"  param {p['name']} = {p['expression']}  ({p['value']} {p['unit']})".rstrip())
    return "\n".join(lineas)


_FORMATEADORES = {"get_scene_info": _resumen_escena}


def texto_resultado(nombre, resultado):
    if nombre in _FORMATEADORES and isinstance(resultado, dict):
        try:
            return _FORMATEADORES[nombre](resultado)
        except (KeyError, TypeError):
            pass
    if resultado is None:
        return ""
    if isinstance(resultado, dict) and "stdout" in resultado and set(resultado) <= {"stdout", "stdout_truncated", "result"}:
        partes = [resultado["stdout"].rstrip("\n")] if resultado["stdout"] else []
        if "result" in resultado:
            partes.append(f"result = {a_json(resultado['result'])}")
        if resultado.get("stdout_truncated"):
            partes.append("(stdout recortado)")
        return "\n".join(partes)
    texto = a_json(resultado)
    if len(texto) > LIMITE_TEXTO:
        texto = texto[:LIMITE_TEXTO] + "… (recortado; --json da el resultado entero)"
    return texto


def mostrar(nombre, r, como_json, previos=(), guardado=None):
    """Imprime UN resultado de `llamar`. JSON: exactamente el dict (avisos de apertura sumados a `avisos`)."""
    if como_json:
        if r["ok"] and previos:
            r = dict(r, avisos=list(previos) + list(r.get("avisos", [])))
        print(a_json(r))
        return
    for a in previos:
        decir(f"aviso: {a}", error=True)
    if r["ok"]:
        texto = texto_resultado(nombre, r["result"])
        decir(f"OK {nombre}" + (f"\n{texto}" if texto else ""))
        for a in r.get("avisos", []):
            decir(f"aviso: {a}")
        if guardado:
            decir(f"guardado: {guardado}")
    else:
        decir(f"ERROR [{r['error_kind']}] {r['mensaje']}", error=True)
        for p in r.get("pistas", []):
            decir(f"  pista: {p}", error=True)


def codigo(r):
    return 0 if r["ok"] else 1
