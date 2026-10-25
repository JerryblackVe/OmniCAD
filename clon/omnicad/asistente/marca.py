"""Marca de deshacer de un pedido del asistente: foto del documento antes del pedido y vuelta exacta a ella."""
import json


def tomar(doc):
    """Receta, pilas de deshacer/rehacer y «modificado» del documento, antes del pedido."""
    return {"doc": doc, "receta": doc._instantanea(), "deshacer": list(doc._deshacer),
            "rehacer": list(doc._rehacer), "modificado": doc.modificado}


def cambio(marca, doc):
    """Indica si `doc` ya no está como en la marca (otra receta u otro documento)."""
    return doc is not marca["doc"] or doc._instantanea() != marca["receta"]


def volver(marca):
    """Deja el documento de la marca exactamente como estaba: receta, vistas, comentarios, unidades y pilas."""
    doc = marca["doc"]
    datos = json.loads(marca["receta"])
    doc._cargar(datos)
    # _cargar es el de deshacer: no toca lo que no entra en deshacer (vistas, comentarios, unidades).
    doc.vistas = datos.get("vistas", {})
    doc.comentarios = datos.get("comentarios", [])
    doc.unidades = doc.unidades_de(datos)
    doc._deshacer[:], doc._rehacer[:] = marca["deshacer"], marca["rehacer"]
    doc.modificado = marca["modificado"]
    doc._notificar()
