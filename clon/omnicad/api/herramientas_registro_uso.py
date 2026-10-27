"""Telemetría local optativa: activación, lectura en vivo, resumen, marcadores e informe.

Todo queda en la carpeta de datos del usuario. Nada se envía. Las herramientas leen los JSONL
que la app escribe con flush por línea, así que el modo en vivo usa la misma sesión abierta.
"""
import os
import re

from .. import registro_uso
from ..registro_uso import almacen, detector
from .errores import error
from .registro import herramienta

_SESION = re.compile(r"[A-Za-z0-9_.-]{1,200}\Z")
_LABEL = re.compile(r"[^A-Za-z0-9_.-]+")


def _sesion(sesion):
    if sesion is None:
        sesion = almacen.ultima_sesion()
    if not isinstance(sesion, str) or not _SESION.fullmatch(sesion) or not almacen.rutas(sesion):
        raise error("INVALID_ARGUMENTS", f"No existe la sesión de registro «{sesion}».",
                    "get_usage_log sin session usa la última sesión.")
    return sesion


@herramienta("set_usage_logging", "avanzado", "Prende o apaga el registro LOCAL de uso. No envía datos; "
             "solo números, claves y longitudes. Apagado de fábrica. No entra en deshacer.",
             modifica=False)
def set_usage_logging(sesion, enabled: bool):
    """
    enabled: true activa la sesión local; false la drena y apaga.
    """
    configurar = getattr(sesion, "configurar_registro", None)
    if configurar:
        return configurar(enabled)
    return registro_uso.configurar(enabled, {"proyecto": sesion.doc.nombre})


@herramienta("get_usage_log", "avanzado", "Lee eventos recientes del registro LOCAL de uso. En vivo lee la sesión "
             "abierta (los JSONL se escriben con flush). Usá since para traer solo lo nuevo.")
def get_usage_log(sesion, since: int = 0, kinds: list[str] | None = None, limit: int = 200,
                  session: str | None = None):
    """
    since: último seq ya visto; devuelve los eventos posteriores (0 = toda la sesión, acotada por limit).
    kinds: tipos a incluir (p. ej. ["op_ejecutada", "error"]); vacío = todos.
    limit: máximo de eventos devueltos (1 a 5000).
    session: id de sesión; vacío = la última.
    """
    if isinstance(since, bool) or not 0 <= since <= 2**63:
        raise error("INVALID_ARGUMENTS", "since tiene que ser un entero no negativo.")
    if isinstance(limit, bool) or not 1 <= limit <= 5000:
        raise error("INVALID_ARGUMENTS", "limit tiene que estar entre 1 y 5000.")
    if kinds is not None and (not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds)):
        raise error("INVALID_ARGUMENTS", "kinds tiene que ser una lista de tipos de evento.")
    sesion = _sesion(session)
    lista = almacen.eventos(sesion, desde=since, tipos=kinds, limite=limit)
    return {"session": sesion, "events": lista, "count": len(lista),
            "last_seq": lista[-1]["seq"] if lista else since, "active": almacen.activa(sesion)}


@herramienta("get_usage_summary", "avanzado", "Resume la sesión local: tiempo por comando, top 10 de operaciones "
             "lentas, cantidad de errores y hallazgos del detector. No envía nada.")
def get_usage_summary(sesion, session: str | None = None, thresholds: dict[str, float] | None = None):
    """
    session: id de sesión; vacío = la última.
    thresholds: umbrales del detector que se quieran pisar (claves de detector.UMBRALES).
    """
    if thresholds is not None and (not isinstance(thresholds, dict) or not all(
            isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool) for k, v in thresholds.items())):
        raise error("INVALID_ARGUMENTS", "thresholds tiene que ser un objeto de números por umbral.")
    sesion = _sesion(session)
    lista = almacen.eventos(sesion)
    if not lista:
        raise error("FILE_NOT_FOUND", f"La sesión «{sesion}» no tiene eventos.",
                    "Prendé el registro con set_usage_logging(enabled=true).")
    return {"session": sesion, "active": almacen.activa(sesion),
            "first_ts": lista[0].get("ts"), "last_ts": lista[-1].get("ts"),
            **detector.resumir(lista, umbrales=thresholds)}


@herramienta("mark_usage_event", "avanzado", "Agrega un marcador al registro local desde la IA. La etiqueta se "
             "guarda solo como slug corto (letras, números, punto, guion y guion bajo). No envía nada.")
def mark_usage_event(sesion, label: str):
    """
    label: etiqueta corta (se sanea a un slug de hasta 80 caracteres).
    """
    if not isinstance(label, str) or not label.strip():
        raise error("INVALID_ARGUMENTS", "label no puede estar vacío.")
    etiqueta = _LABEL.sub("_", label.strip())[:80].strip("._-") or "marca"
    if not (etiqueta[0].isalpha() or etiqueta[0] == "_"):
        etiqueta = "m_" + etiqueta
    registrar = getattr(sesion, "registrar_marca", None)
    if registrar:
        seq = registrar(etiqueta)
        if seq is None:
            raise error("LOGGING_DISABLED", "El registro de uso está apagado en la ventana abierta.",
                        "Prendelo con set_usage_logging(enabled=true).")
        return {"marked": True, "label": etiqueta, "seq": seq}
    if registro_uso.activo is None:
        raise error("LOGGING_DISABLED", "El registro de uso está apagado: no hay una sesión que marcar.",
                    "Prendelo con set_usage_logging(enabled=true).")
    seq = registro_uso.activo.emitir("marca", {"label": etiqueta, "origen": "ia"})
    if seq is None:
        raise error("LOGGING_DISABLED", "No se pudo escribir el marcador: la cola del registro está cerrada.",
                    "Revisá el estado con set_usage_logging(enabled=true).")
    return {"marked": True, "label": etiqueta, "seq": seq,
            "session": registro_uso.activo.id}


def _detalle(evento):
    """Una línea corta y sin texto libre para la línea de tiempo del informe."""
    d = evento.get("datos") if isinstance(evento.get("datos"), dict) else {}
    partes = []
    for clave in ("comando", "paso", "tipo_op", "accion", "formato", "categoria", "label", "origen"):
        if d.get(clave) and not isinstance(d[clave], (dict, list)):
            partes.append(f"{clave}={d[clave]}")
    for clave in ("duracion_ms", "duracion_s", "exito", "tamano", "cuerpos", "volumen", "fps_p95", "rss"):
        if d.get(clave) is not None:
            valor = d[clave]
            partes.append(f"{clave}={valor:.1f}" if isinstance(valor, float) else f"{clave}={valor}")
    if isinstance(d.get("antes"), dict) and isinstance(d.get("despues"), dict):
        partes.append(f"volumen {d['antes'].get('volumen')} → {d['despues'].get('volumen')}")
    return " · ".join(partes)


def _informe(sesion, lista, resumen):
    inicio = next((e for e in lista if e.get("tipo") == "sesion_inicio"), {})
    datos = inicio.get("datos") if isinstance(inicio.get("datos"), dict) else {}
    lineas = [f"# Informe de sesión {sesion}", "",
              f"- Inicio: {inicio.get('ts', '?')}",
              f"- Fin: {lista[-1].get('ts', '?')}",
              f"- Duración observada: {resumen['duracion_s']} s · {resumen['eventos']} eventos",
              f"- Versión: {datos.get('version', '?')} · SO: {datos.get('so', '?')}",
              f"- Proyecto: {datos.get('proyecto', '?')} · ventana: {datos.get('ventana', '?')}",
              f"- GPU/OpenGL: {datos.get('gpu', '?')}",
              "", "## Resumen", "",
              f"- Comandos: {len(resumen['comandos'])} · errores: {resumen['errores']} · "
              f"recálculos: {resumen['recalculos']['cantidad']} "
              f"({resumen['recalculos']['total_ms']} ms) · picking promedio: {resumen['picking_ms_promedio']} ms",
              f"- Hallazgos: {len(resumen['hallazgos'])} "
              f"(alta {resumen['hallazgos_por_severidad']['alta']}, "
              f"media {resumen['hallazgos_por_severidad']['media']}, "
              f"baja {resumen['hallazgos_por_severidad']['baja']})", "", "### Comandos", "",
              "| Comando | Abiertos | Aceptados | Cancelados | Cambios | Tiempo (s) |",
              "|---|---:|---:|---:|---:|---:|"]
    for nombre, c in sorted(resumen["comandos"].items()):
        lineas.append(f"| {nombre} | {c['abiertos']} | {c['aceptados']} | {c['cancelados']} | "
                      f"{c['cambios']} | {c['tiempo_s']} |")
    lineas += ["", "### Operaciones más lentas", "",
               "| Paso | Tipo | Duración (ms) | Éxito | t (s) |", "|---|---|---:|---|---:|"]
    for op in resumen["operaciones_lentas"]:
        lineas.append(f"| {op['paso']} | {op['tipo_op']} | {op['duracion_ms']} | "
                      f"{'sí' if op['exito'] else 'no'} | {op['t']} |")
    lineas += ["", "## Hallazgos del detector", ""]
    if resumen["hallazgos"]:
        lineas += ["| Severidad | t (s) | Qué |", "|---|---:|---|"]
        for h in resumen["hallazgos"]:
            lineas.append(f"| {h['severidad']} | {h['t']} | {h['que']} |")
    else:
        lineas.append("Sin hallazgos con los umbrales actuales.")
    lineas += ["", "## Línea de tiempo", "", "| t (s) | Tipo | Detalle |", "|---:|---|---|"]
    for evento in lista:
        if evento.get("tipo") in ("memoria", "visor_cuadros", "clic"):
            continue
        lineas.append(f"| {evento.get('t', 0)} | {evento.get('tipo')} | {_detalle(evento)} |")
    lineas += ["", "## Filas sugeridas para docs/seguimiento/ (borrador, no se escribieron)", "",
               "```markdown"]
    if resumen["hallazgos"]:
        lineas += [h["sugerencia"] for h in resumen["hallazgos"]]
    else:
        lineas.append("Sin filas: la sesión no disparó ninguna regla.")
    lineas += ["```", "",
               "Los datos son locales y ya vienen saneados (sin texto de campos, chat ni rutas).",
               "Este informe NO se agregó a docs/seguimiento/: revisalo antes de cargar una fila.", ""]
    return "\n".join(lineas)


@herramienta("build_usage_report", "avanzado", "Arma un informe Markdown de una sesión del registro local en su "
             "carpeta: resumen, hallazgos, línea de tiempo y filas sugeridas. No modifica docs/seguimiento/.")
def build_usage_report(sesion, session: str | None = None):
    """
    session: id de sesión; vacío = la última.
    """
    sesion = _sesion(session)
    lista = almacen.eventos(sesion)
    if not lista:
        raise error("FILE_NOT_FOUND", f"La sesión «{sesion}» no tiene eventos.",
                    "Prendé el registro con set_usage_logging(enabled=true).")
    destino = registro_uso.carpeta() / f"informe_sesion_{sesion}.md"
    contenido = _informe(sesion, lista, detector.resumir(lista))
    temporal = destino.with_name(destino.name + f".{os.getpid()}.tmp")
    try:
        with open(temporal, "w", encoding="utf-8", newline="\n") as f:
            f.write(contenido)
        os.replace(temporal, destino)
    except OSError as e:
        try:
            temporal.unlink()
        except OSError:
            pass
        raise error("FILE_ERROR", f"No se pudo escribir el informe: {e}.",
                    "Revisá los permisos de la carpeta del registro.") from None
    return {"path": str(destino), "session": sesion, "events": len(lista),
            "findings": len(detector.analizar(lista))}
