# -*- coding: utf-8 -*-
"""PREP del comando INSPECCIONAR › Revisar geometría (clave `revisar_geometria`), según la ayuda de Fusion.

Fuente: docs/fusion_docs/contenido/fusion-model/validate-reference-f6a64645b51.md (Validate: verifica la calidad
de un modelo importado, comprueba los cuerpos y reporta los problemas). Un caso con un valor numérico (caja
10×20×30: válida, estanca, volumen 6000 mm³, sin problemas) y un caso borde (documento sin cuerpos: el comando
no se puede ejecutar).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.comandos.revision import RevisarGeometria


def _doc():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30"))
    return doc


def _cuerpo(doc, cid):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, doc.estado_final)


def _valores(cmd, ctx, **v):
    base = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    base.update(v)
    return base


def test_revisar_geometria_caja_valida_reporta_volumen_6000():
    """Caso numérico: un cuerpo válido no tiene problemas y reporta volumen 6000 mm³."""
    doc = _doc()
    cmd, ctx = CATALOGO["revisar_geometria"](), ContextoComando(doc)
    cid = next(iter(doc.estado_final.cuerpos))
    texto = cmd._resultado(_valores(cmd, ctx, cuerpos=[_cuerpo(doc, cid)]), ctx)
    assert "Válido: sí" in texto
    assert "Estanco: sí" in texto
    assert "Volumen: 6000" in texto
    assert "Sin problemas." in texto
    assert cmd.calcular(_valores(cmd, ctx, cuerpos=[_cuerpo(doc, cid)]), ctx)[0][1]["errores"] == 0


def test_revisar_geometria_sin_cuerpos_no_se_puede_ejecutar():
    """Caso borde: sin cuerpos en el documento, el comando no se puede ejecutar."""
    doc = Documento()
    cmd, ctx = RevisarGeometria(), ContextoComando(doc)
    assert cmd.verificar(ctx) == "No hay cuerpos para revisar."