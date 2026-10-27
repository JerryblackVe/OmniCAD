# -*- coding: utf-8 -*-
"""`omnicad registro`: resumen del registro local de uso y seguimiento en vivo (`--seguir`)."""
import time

from . import util


def _resumen(sesion=None):
    from ..registro_uso import almacen, detector
    sesion = sesion or almacen.ultima_sesion()
    if not sesion:
        raise util.UsoError("No hay sesiones del registro local.",
                            ["Prendé el registro con `omnicad call set_usage_logging enabled=true`."])
    eventos = almacen.eventos(sesion)
    if not eventos:
        raise util.UsoError(f"La sesión «{sesion}» no tiene eventos.")
    return sesion, detector.resumir(eventos)


def _mostrar_humano(sesion, resumen):
    util.decir(f"Sesión: {sesion} · {resumen['eventos']} eventos · {resumen['duracion_s']} s")
    util.decir(f"Comandos: {len(resumen['comandos'])} · errores: {resumen['errores']} · "
               f"recálculos: {resumen['recalculos']['cantidad']} · "
               f"picking promedio: {resumen['picking_ms_promedio']} ms")
    util.decir(f"Hallazgos: alta {resumen['hallazgos_por_severidad']['alta']}, "
               f"media {resumen['hallazgos_por_severidad']['media']}, "
               f"baja {resumen['hallazgos_por_severidad']['baja']}")
    if resumen["operaciones_lentas"]:
        util.decir("\nOperaciones más lentas:")
        for op in resumen["operaciones_lentas"][:5]:
            util.decir(f"  {str(op['paso']):>8}  {str(op['tipo_op']):<16} {op['duracion_ms']:>10.1f} ms  "
                       f"{'ok' if op['exito'] else 'error'}")
    if resumen["comandos"]:
        util.decir("\nPor comando:")
        for nombre, c in sorted(resumen["comandos"].items()):
            util.decir(f"  {nombre:<24} {c['abiertos']:>2} abiertos · {c['aceptados']:>2} aceptados · "
                       f"{c['cancelados']:>2} cancelados · {c['cambios']:>3} cambios · {c['tiempo_s']:.1f} s")
    if resumen["hallazgos"]:
        util.decir("\nHallazgos:")
        for h in resumen["hallazgos"][:10]:
            util.decir(f"  [{h['severidad']}] t={h['t']} · {h['que']}")
        if len(resumen["hallazgos"]) > 10:
            util.decir(f"  … y {len(resumen['hallazgos']) - 10} más (mirá el informe).")


def _linea(evento, como_json):
    if como_json:
        print(util.a_json(evento), flush=True)
    else:
        d = evento.get("datos") if isinstance(evento.get("datos"), dict) else {}
        detalle = " ".join(f"{k}={d[k]}" for k in ("comando", "paso", "tipo_op", "accion", "categoria", "label")
                           if d.get(k) and not isinstance(d[k], (dict, list)))
        util.decir(f"[{evento.get('t', 0):8.3f}] {evento.get('tipo', '?'):<20} {detalle}")


def _seguir(ns):
    from ..registro_uso import almacen
    sesion = ns.sesion or almacen.ultima_sesion()
    if not sesion or not almacen.rutas(sesion):
        raise util.UsoError(f"No existe la sesión de registro «{sesion}».",
                            ["Mirá las sesiones con `omnicad registro --json`."])
    if ns.since is not None and ns.since < 0:
        raise util.UsoError("--since tiene que ser un entero no negativo.")
    lector = almacen.Lector(sesion, desde=ns.since or 0)
    if ns.since is None:
        lector.al_final()
        if not ns.json:
            util.decir(f"Siguiendo {sesion} (solo lo nuevo; Ctrl+C para salir)…")
    elif not ns.json:
        util.decir(f"Siguiendo {sesion} desde seq {ns.since}…")
    try:
        while True:
            if ns.sesion is None:
                nueva = almacen.ultima_sesion()
                if nueva and nueva != lector.sesion:
                    lector = almacen.Lector(nueva)
                    if not ns.json:
                        util.decir(f"Nueva sesión: {nueva}")
            for evento in lector.nuevos():
                _linea(evento, ns.json)
            time.sleep(0.4)
    except KeyboardInterrupt:
        return 130


def registro(ns):
    if ns.seguir:
        return _seguir(ns)
    if ns.since is not None:
        raise util.UsoError("--since se usa con --seguir.")
    sesion, resumen = _resumen(ns.sesion)
    if ns.json:
        print(util.a_json({"ok": True, "session": sesion, **resumen}))
    else:
        _mostrar_humano(sesion, resumen)
    return 0


def registrar(sub, comun):
    p = sub.add_parser("registro", parents=[comun], help="ver el registro local de uso o seguirlo en vivo",
                       description="Resumen de la última sesión del registro local. Con --seguir muestra los "
                                   "eventos nuevos línea a línea (los JSONL se escriben con flush: sirve para "
                                   "seguir la app abierta). Nada se envía a la red.")
    p.add_argument("--seguir", action="store_true", help="quedarse mostrando los eventos nuevos hasta Ctrl+C")
    p.add_argument("--sesion", metavar="ID", help="id de sesión (por defecto la última)")
    p.add_argument("--since", type=int, metavar="SEQ",
                   help="con --seguir: arrancar en este seq (por defecto, solo lo nuevo)")
    p.set_defaults(func=registro)
