"""Contrato neutral que los proveedores traducen a su formato de API.

Los mensajes son una lista de {"rol": "usuario" | "asistente", "contenido": [bloques]}.
Los bloques tienen estos formatos:
  - {"tipo": "texto", "texto": str}
  - {"tipo": "imagen", "png": bytes, "ancho": int, "alto": int}
  - {"tipo": "documento", "pdf": bytes, "nombre": str}   (un PDF adjunto, IA-9)
Los bloques de un adjunto llevan además "adjunto": nombre del archivo (el historial no guarda su contenido).
  - {"tipo": "pedido_herramienta", "id": str, "nombre": str, "args": dict}
  - {"tipo": "resultado_herramienta", "id": str, "error": bool, "contenido": [bloques texto/imagen]}
"""
import copy
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class ErrorProveedor(Exception):
    """Falla al hablar con la API; el mensaje es para el usuario y nunca lleva la clave."""


def clave_de(clave, variable):
    """La clave pasada o la de la variable de entorno; None si no hay ninguna."""
    return clave or os.environ.get(variable) or None


def pedir_json(url, cuerpo, encabezados, timeout, clave=None):
    """POST con JSON y respuesta JSON completa (sin streaming), con errores claros en español."""
    pedido = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
                                    headers={"content-type": "application/json", **encabezados})
    host = urlsplit(url).netloc
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detalle = json.loads(e.read().decode("utf-8", "replace")).get("error", "")
            detalle = detalle.get("message", "") if isinstance(detalle, dict) else str(detalle)
        except (ValueError, AttributeError, OSError):
            detalle = ""
        if clave:  # antes de recortar: un recorte podría dejar media clave a la vista
            detalle = detalle.replace(clave, "***")
        if e.code in (401, 403):
            mensaje = f"La clave de API no es válida o no tiene permiso (HTTP {e.code})."
        elif e.code == 429:
            mensaje = "Se superó el límite de pedidos o el saldo de la cuenta (HTTP 429). Esperá un momento o revisá el saldo."
        elif e.code >= 500:
            mensaje = f"El servicio de {host} falló (HTTP {e.code}). Probá de nuevo más tarde."
        else:
            mensaje = f"{host} rechazó el pedido (HTTP {e.code})."
        if detalle:
            mensaje += f" Detalle: {detalle[:300]}"
    except TimeoutError:
        mensaje = f"{host} no respondió en {timeout} s."
    except OSError as e:  # URLError y cortes de conexión
        mensaje = f"No se pudo conectar con {host}: {getattr(e, 'reason', e)}."
    except ValueError:
        mensaje = f"{host} devolvió una respuesta que no es JSON."
    raise ErrorProveedor(mensaje) from None


@dataclass
class PedidoHerramienta:
    id: str
    nombre: str
    args: dict


@dataclass
class Respuesta:
    """Uso reportado por la API: entrada/salida (tokens) y costo_usd (float o None)."""

    texto: str = ""
    herramientas: list = field(default_factory=list)
    uso: dict = field(default_factory=dict)


class Proveedor:
    def responder(self, sistema, mensajes, herramientas):
        """Devuelve una Respuesta; herramientas contiene nombre, descripcion y esquema."""
        raise NotImplementedError


class ProveedorFalso(Proveedor):
    def __init__(self, guion):
        self.guion = iter(guion)
        self.recibidos = []

    def responder(self, sistema, mensajes, herramientas):
        """Guarda lo recibido y entrega la siguiente respuesta, sin red."""
        self.recibidos.append((copy.deepcopy(mensajes), [h["nombre"] for h in herramientas]))
        return next(self.guion, Respuesta(texto="(fin del guion)"))
