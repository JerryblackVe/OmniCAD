"""Agrupa errores y bloqueos de sesiones JSONL, sin importar OmniCAD ni modificar los registros.

Uso: clon/.venv/bin/python scripts/registro_bugs.py [carpeta] [--salida informe.md]
Sin argumentos lee el registro local de la app (OMNICAD_REGISTRO_DIR, o la carpeta de datos del sistema) y
escribe en evidencias/ del repo.
Los conteos son eventos registrados, no necesariamente bugs distintos ni fallos sin controlar.
"""

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path
import re


# Misma regla que omnicad.carpeta_datos(); no se importa OmniCAD para que el script siga siendo independiente.
_DATOS = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "OmniCAD"
REGISTROS = Path(os.environ.get("OMNICAD_REGISTRO_DIR") or _DATOS / "registro")
EVIDENCIAS = Path(__file__).resolve().parents[1] / "evidencias"
_ARCHIVO = re.compile(r"sesion_(.+)_\d{4}\.jsonl\Z")
_RUTA = re.compile(
    r"[\"'](?:[A-Za-z]:[\\/]|[\\/]{2}|/|~[\\/]|\.\.?[\\/])[^\"'\n]+[\"']"
    r"|(?<![\w])(?:[A-Za-z]:[\\/]|[\\/]{2}|/|~[\\/]|\.\.?[\\/])[^\s\"'<>|)]+"
    r"|\b(?:[\w.-]+[\\/])+[\w.-]+\.[A-Za-z]\w*"
)
_NUMERO = re.compile(r"[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?")


def normalizar_mensaje(mensaje):
    """Sustituye rutas y números; un mensaje oculto nunca se inventa a partir de su longitud."""
    if not isinstance(mensaje, str):
        return "[mensaje oculto o ausente]"
    return " ".join(_NUMERO.sub("<n>", _RUTA.sub("<ruta>", mensaje)).split())


def _texto(valor):
    return valor.strip() if isinstance(valor, str) else ""


def agrupar(carpeta):
    """Lee partes de sesiones y devuelve grupos, totales y avisos de calidad de los datos.

    Errores: (comando, mensaje normalizado); sin comando usa tipo_op y luego «sin comando».
    Bloqueos: comando, o accion si no hay panel, con duración estrictamente mayor a 3000 ms.
    """
    rutas = sorted(Path(carpeta).glob("sesion_*.jsonl"))
    if not rutas:
        raise ValueError(f"No hay archivos sesion_*.jsonl en {carpeta}.")
    grupos, sesiones, avisos = {}, set(), []
    lineas = duplicados = ocultos = 0
    primera = ultima = None
    vistos = set()
    for ruta in rutas:
        coincidencia = _ARCHIVO.fullmatch(ruta.name)
        if not coincidencia:
            avisos.append(f"Nombre de archivo no reconocido: {ruta.name}")
            continue
        sesion = coincidencia[1]
        sesiones.add(sesion)
        with ruta.open("rb") as archivo:
            for numero, cruda in enumerate(archivo, 1):
                lineas += 1
                try:
                    evento = json.loads(cruda)
                    if not isinstance(evento, dict) or not isinstance(evento.get("datos"), dict):
                        raise ValueError("evento o datos no es un objeto")
                    fecha = datetime.fromisoformat(evento["ts"])
                    if fecha.tzinfo is None:
                        raise ValueError("fecha sin zona horaria")
                    fecha = fecha.astimezone(timezone.utc)
                    secuencia = evento["seq"]
                    if not isinstance(secuencia, int) or isinstance(secuencia, bool):
                        raise ValueError("seq no es entero")
                except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
                    avisos.append(f"{ruta.name}:{numero}: línea omitida ({exc})")
                    continue
                primera = min(primera, fecha) if primera else fecha
                ultima = max(ultima, fecha) if ultima else fecha
                clave_evento = (sesion, secuencia)
                duplicados += clave_evento in vistos
                vistos.add(clave_evento)
                tipo, datos = evento.get("tipo"), evento["datos"]
                if tipo not in ("error", "bloqueo_ui"):
                    continue
                comando = _texto(datos.get("comando"))
                duracion = None
                if tipo == "bloqueo_ui":
                    duracion = datos.get("duracion_ms")
                    if (isinstance(duracion, bool) or not isinstance(duracion, (int, float))
                            or not math.isfinite(duracion) or duracion < 0):
                        avisos.append(f"{ruta.name}:{numero}: bloqueo omitido (duración inválida)")
                        continue
                    if duracion <= 3000:
                        continue
                    comando = comando or _texto(datos.get("accion")) or "sin comando"
                    mensaje = "Bloqueo de interfaz > 3 s"
                else:
                    comando = comando or _texto(datos.get("tipo_op")) or "sin comando"
                    ocultos += not isinstance(datos.get("mensaje"), str)
                    mensaje = normalizar_mensaje(datos.get("mensaje"))
                clave = (tipo, comando, mensaje)
                if clave not in grupos:
                    grupos[clave] = {
                        "tipo": tipo, "comando": comando, "mensaje": mensaje, "cantidad": 0,
                        "sesiones": set(), "primera": fecha, "ultima": fecha,
                        "ejemplo": {"sesion": sesion, "archivo": ruta.name, "linea": numero,
                                    "seq": secuencia, "datos": datos},
                        "origenes": Counter(), "acciones": Counter(), "maximo_ms": 0,
                    }
                grupo = grupos[clave]
                grupo["cantidad"] += 1
                grupo["sesiones"].add(sesion)
                grupo["primera"] = min(grupo["primera"], fecha)
                grupo["ultima"] = max(grupo["ultima"], fecha)
                grupo["origenes"][_texto(datos.get("origen")) or "sin origen"] += 1
                if tipo == "bloqueo_ui":
                    grupo["acciones"][_texto(datos.get("accion")) or "sin acción"] += 1
                    grupo["maximo_ms"] = max(grupo["maximo_ms"], duracion)
                elif datos.get("traza") and not grupo["ejemplo"]["datos"].get("traza"):
                    grupo["ejemplo"] = {"sesion": sesion, "archivo": ruta.name, "linea": numero,
                                        "seq": secuencia, "datos": datos}
    ordenados = sorted(grupos.values(), key=lambda g: (-g["cantidad"], g["comando"], g["mensaje"]))
    errores = [g for g in ordenados if g["tipo"] == "error"]
    bloqueos = [g for g in ordenados if g["tipo"] == "bloqueo_ui"]
    return {"errores": errores, "bloqueos": bloqueos, "archivos": len(rutas),
            "sesiones": len(sesiones), "lineas": lineas, "duplicados": duplicados,
            "ocultos": ocultos, "avisos": avisos, "primera": primera, "ultima": ultima}


def _celda(texto):
    return (" ".join(str(texto).split()).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("|", "&#124;").replace("`", "&#96;"))


def generar_informe(datos):
    """Markdown ordenado por cantidad; cada grupo conserva una localización y hasta seis cuadros de traza."""
    lineas = [f"# Registro de bugs — {date.today().isoformat()}", "",
              f"Archivos: {datos['archivos']}; sesiones: {datos['sesiones']}; líneas: {datos['lineas']}.",
              f"Período completo (UTC): {datos['primera']} — {datos['ultima']}.", "",
              "## Criterio y calidad de datos", "",
              "- Se cuentan eventos `error`, incluidos avisos y validaciones; no todos son bugs.",
              "- Mensaje normalizado: rutas → `<ruta>`; números → `<n>`; espacios compactados.",
              "- Sin comando se usa tipo_op (errores), accion (bloqueos), o «sin comando».",
              "- accion es la última acción observada: atribución orientativa, no prueba de causalidad.",
              "- Las partes de un JSONL cuentan como una sesión. Fechas comparadas en UTC.",
              f"- Mensajes ocultos/ausentes: {datos['ocultos']}; no permiten identificar la causa.",
              f"- Secuencias repetidas: {datos['duplicados']} (se conservan, no se deduplican).",
              f"- Líneas o bloqueos omitidos y nombres inválidos: {len(datos['avisos'])}.", ""]
    lineas.extend(f"- ⚠ {aviso}" for aviso in datos["avisos"])
    for titulo, clave, prefijo in (("Errores", "errores", "E"), ("Bloqueos > 3 s", "bloqueos", "L")):
        grupos = datos[clave]
        lineas += [f"## {titulo}", "",
                   f"{sum(g['cantidad'] for g in grupos)} eventos; {len(grupos)} grupos.", "",
                   "| Grupo | Comando | Mensaje normalizado | Veces | Sesiones | Primera UTC | Última UTC |",
                   "|---|---|---|---:|---:|---|---|"]
        for indice, g in enumerate(grupos, 1):
            lineas.append(f"| {prefijo}{indice:02d} | {_celda(g['comando'])} | {_celda(g['mensaje'])} "
                          f"| {g['cantidad']} | {len(g['sesiones'])} | {g['primera'].isoformat()} "
                          f"| {g['ultima'].isoformat()} |")
        for indice, g in enumerate(grupos, 1):
            e = g["ejemplo"]
            lineas += ["", f"### {prefijo}{indice:02d} · {_celda(g['comando'])}", "",
                       f"- Sesión de ejemplo: `{e['sesion']}`.",
                       f"- Evento: `{e['archivo']}:{e['linea']}`; seq {e['seq']}.",
                       f"- Orígenes: {_celda(dict(g['origenes']))}."]
            if clave == "bloqueos":
                lineas += [f"- Máximo: {g['maximo_ms'] / 1000:.3f} s.",
                           f"- Acciones observadas: {_celda(dict(g['acciones']))}."]
            else:
                lineas.append(f"- Mensaje de ejemplo: {_celda(e['datos'].get('mensaje'))}.")
            traza = e["datos"].get("traza")
            if isinstance(traza, list) and traza:
                lineas += ["- Traza de ejemplo (últimos seis cuadros):", "", "```text"]
                for marco in traza[-6:]:
                    lineas.append(str(marco)[:300])
                lineas.append("```")
            else:
                lineas.append("- Traza: no registrada en este evento.")
    lineas += ["", "## Filas nuevas propuestas", "",
               "Pendiente de contraste manual con seguimiento y código actual.", "",
               "## Ya tienen fila", "", "Pendiente de contraste manual.", ""]
    return "\n".join(lineas)


def principal():
    """Entrada de consola: carpeta opcional y destino Markdown."""
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("carpeta", nargs="?", type=Path, default=REGISTROS)
    argumentos.add_argument("--salida", type=Path,
                            default=EVIDENCIAS / f"registro_{date.today().isoformat()}.md")
    opciones = argumentos.parse_args()
    try:
        datos = agrupar(opciones.carpeta)
        opciones.salida.parent.mkdir(parents=True, exist_ok=True)
        opciones.salida.write_text(generar_informe(datos), encoding="utf-8")
    except (OSError, ValueError) as exc:
        argumentos.exit(1, f"Error: {exc}\n")
    print(f"Archivos: {datos['archivos']}; sesiones: {datos['sesiones']}; líneas: {datos['lineas']}.")
    for clave, prefijo in (("errores", "E"), ("bloqueos", "L")):
        grupos = datos[clave]
        print(f"{clave.capitalize()}: {sum(g['cantidad'] for g in grupos)} eventos; {len(grupos)} grupos.")
        for indice, g in enumerate(grupos, 1):
            print(f"{prefijo}{indice:02d}: {g['cantidad']} veces / {len(g['sesiones'])} sesiones; "
                  f"{g['comando']}: {g['mensaje']}")
    print(f"Calidad: {datos['ocultos']} mensajes ocultos; {datos['duplicados']} secuencias repetidas; "
          f"{len(datos['avisos'])} avisos.")
    print(f"Informe: {opciones.salida}")


if __name__ == "__main__":
    principal()
