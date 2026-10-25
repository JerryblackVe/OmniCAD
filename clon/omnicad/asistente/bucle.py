"""Bucle de conversación y ejecución de herramientas del asistente."""
import json

from omnicad import api
from omnicad.api.errores import error

from .herramientas import Herramientas


def correr(proveedor, mensajes, ejecutar, herramientas=None, sistema="", al_evento=None,
           tope_vueltas=25, cancelado=None, aprobar=None):
    """Agrega respuestas y resultados al chat y devuelve motivo, vueltas y uso acumulado.

    `aprobar(pedidos) -> bool` se llama antes de una tanda con herramientas que cambian algo: en Hacer, una vez
    por pedido (aprobado el plan, sigue solo); en Guiar, en cada tanda. Si no aprueba, la tanda vuelve al modelo
    como CANCELLED y el motivo es «rechazado» (o «cancelado», si además se canceló el pedido).
    """
    herramientas = Herramientas() if herramientas is None else herramientas
    resultado = {"motivo": "tope", "vueltas": 0,
                 "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}
    aprobado = False

    def emitir(tipo, datos):
        if al_evento is not None:
            al_evento(tipo, datos)

    def separar_imagenes(valor, imagenes):
        if isinstance(valor, api.Imagen):
            imagenes.append(valor)
            return "(imagen adjunta)"
        if isinstance(valor, dict):
            return {k: separar_imagenes(v, imagenes) for k, v in valor.items()}
        if isinstance(valor, list):
            return [separar_imagenes(v, imagenes) for v in valor]
        return valor

    for vuelta in range(tope_vueltas):
        if cancelado is not None and cancelado():
            resultado["motivo"] = "cancelado"
            return resultado
        resultado["vueltas"] = vuelta + 1
        try:
            respuesta = proveedor.responder(sistema, mensajes, herramientas.definiciones())
        except Exception as e:
            emitir("error", str(e))
            resultado["motivo"] = "error"
            return resultado

        uso = resultado["uso"]
        for clave in ("entrada", "salida"):
            uso[clave] += respuesta.uso.get(clave) or 0
        costo = respuesta.uso.get("costo_usd")
        if costo is not None:
            uso["costo_usd"] = (uso["costo_usd"] or 0) + costo
        emitir("uso", respuesta.uso)

        contenido = [{"tipo": "texto", "texto": respuesta.texto}] if respuesta.texto else []
        contenido += [{"tipo": "pedido_herramienta", "id": p.id, "nombre": p.nombre, "args": p.args}
                      for p in respuesta.herramientas]
        if not contenido:  # la API de Claude rechaza un mensaje de asistente vacío
            resultado["motivo"] = "fin"
            return resultado
        mensajes.append({"rol": "asistente", "contenido": contenido})
        if respuesta.texto:
            emitir("texto", respuesta.texto)
        if not respuesta.herramientas:
            resultado["motivo"] = "fin"
            return resultado

        resultados = []
        interrumpido = rechazado = False
        pendientes = [p for p in respuesta.herramientas if herramientas.necesita_aprobacion(p.nombre)]
        if aprobar is not None and pendientes and not aprobado and not (cancelado is not None and cancelado()):
            if aprobar(pendientes):
                aprobado = herramientas.modo == "hacer"
            elif cancelado is not None and cancelado():
                interrumpido = True
            else:
                rechazado = True
        for pedido in respuesta.herramientas:
            if rechazado:
                salida = error("CANCELLED", "La persona no aprobó estos cambios; no se ejecutó nada.",
                               "Preguntale qué quiere cambiar del plan antes de proponer otro.").a_dict()
            elif interrumpido or (cancelado is not None and cancelado()):
                interrumpido = True
                salida = error("CANCELLED", "El usuario canceló el pedido; no se ejecutó.").a_dict()
            elif pedido.nombre == "buscar_herramientas":
                try:
                    salida = herramientas.buscar(**pedido.args)
                except TypeError:
                    salida = error("INVALID_ARGUMENTS",
                                   "buscar_herramientas necesita solo el argumento tema (texto).").a_dict()
            elif pedido.nombre in herramientas.fuera_de_modo:
                salida = error("TOOL_NOT_AVAILABLE",
                               f"La herramienta '{pedido.nombre}' no se puede usar en el modo {herramientas.modo}.",
                               "Explicale a la persona qué harías y que cambie a modo Guiar o Hacer.").a_dict()
            elif not herramientas.permitida(pedido.nombre):
                salida = error("TOOL_NOT_AVAILABLE", f"La herramienta '{pedido.nombre}' no está habilitada.",
                               "Usá buscar_herramientas(tema) para sumar las de un grupo.").a_dict()
            else:
                try:
                    salida = ejecutar(pedido.nombre, pedido.args)
                except Exception as e:
                    salida = error("INTERNAL_ERROR", f"{type(e).__name__}: {e}").a_dict()

            imagenes = []
            sin_imagenes = separar_imagenes(salida, imagenes)
            bloques = [{"tipo": "texto", "texto": json.dumps(sin_imagenes, ensure_ascii=False, default=str)}]
            bloques += [{"tipo": "imagen", "png": i.png, "ancho": i.ancho, "alto": i.alto} for i in imagenes]
            resultados.append({"tipo": "resultado_herramienta", "id": pedido.id,
                               "error": not salida["ok"], "contenido": bloques})
            emitir("herramienta", {"nombre": pedido.nombre, "args": pedido.args, "respuesta": sin_imagenes})
            for imagen in imagenes:
                emitir("imagen", imagen)
        mensajes.append({"rol": "usuario", "contenido": resultados})
        if interrumpido or rechazado:
            resultado["motivo"] = "cancelado" if interrumpido else "rechazado"
            return resultado

    emitir("error", f"Se llegó al tope de {tope_vueltas} vueltas: el pedido se cortó.")
    return resultado
