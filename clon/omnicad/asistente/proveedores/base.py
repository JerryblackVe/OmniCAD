"""Contrato neutral que los proveedores traducen a su formato de API.

Los mensajes son una lista de {"rol": "usuario" | "asistente", "contenido": [bloques]}.
Los bloques tienen estos formatos:
  - {"tipo": "texto", "texto": str}
  - {"tipo": "imagen", "png": bytes, "ancho": int, "alto": int}
  - {"tipo": "pedido_herramienta", "id": str, "nombre": str, "args": dict}
  - {"tipo": "resultado_herramienta", "id": str, "error": bool, "contenido": [bloques texto/imagen]}
"""
import copy
from dataclasses import dataclass, field


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
