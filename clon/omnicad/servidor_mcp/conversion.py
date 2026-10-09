# -*- coding: utf-8 -*-
"""
De la respuesta de `api.llamar` al resultado de una herramienta MCP.

  - Resultado ok: contenido de texto con el JSON de la respuesta y, después, un contenido de imagen PNG por
    cada `api.Imagen` que traiga el resultado. En el JSON, cada imagen queda como una referencia corta
    (`{"attached_image": N, ...}`), nunca como base64.
  - Resultado con error: `isError=true` y el JSON {ok, error_kind, mensaje, pistas} como texto.
  - Sin `structuredContent`: repetiría el mismo JSON y el agente pagaría los tokens dos veces.
"""
import base64
import json

from mcp_types import CallToolResult, ImageContent, TextContent

from .. import api


def separar_imagenes(valor, imagenes):
    """Copia de `valor` con cada `Imagen` reemplazada por su referencia; las imágenes se agregan a `imagenes`."""
    if isinstance(valor, api.Imagen):
        imagenes.append(valor)
        return {"attached_image": len(imagenes), "mime_type": "image/png", "width": valor.ancho, "height": valor.alto}
    if isinstance(valor, dict):
        return {k: separar_imagenes(v, imagenes) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [separar_imagenes(v, imagenes) for v in valor]
    return valor


def a_resultado_mcp(respuesta):
    """`respuesta` es el dict de `api.llamar`. Devuelve un `CallToolResult`."""
    imagenes = []
    limpia = separar_imagenes(respuesta, imagenes)
    contenido = [TextContent(type="text", text=json.dumps(limpia, ensure_ascii=False))]
    contenido += [ImageContent(type="image", data=base64.b64encode(i.png).decode("ascii"), mime_type="image/png")
                  for i in imagenes]
    return CallToolResult(content=contenido, is_error=not respuesta.get("ok", False))
