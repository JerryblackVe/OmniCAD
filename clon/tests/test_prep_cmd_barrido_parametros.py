# -*- coding: utf-8 -*-
"""PREP: test de comando Barrido de parámetros (barrido_parametros).
Cubre casos con valores numéricos y casos borde en los campos del diálogo.
"""
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comando import ContextoComando
from omnicad.ui.comandos.inspeccionar import BarridoParametros


def _hacer_comando(doc, **valores):
    cmd = BarridoParametros()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    op = cmd.construir(v, ctx)
    return op, v, ctx


def test_prep_cmd_barrido_parametros_campos():
    """Test que los campos del comando Barrido de parámetros están bien definidos."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="5"))
    cmd = BarridoParametros()
    ctx = ContextoComando(doc)
    campos = cmd.campos(ctx)
    claves = [c.clave for c in campos]
    assert "parametro" in claves
    assert "desde" in claves
    assert "hasta" in claves
    assert "pasos" in claves
    assert "interferencia" in claves
    assert "calcular" in claves


def test_prep_cmd_barrido_parametros_valores_defecto():
    """Test que los campos tienen valores por defecto correctos."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="5"))
    cmd = BarridoParametros()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    # El default del parámetro es el primero del documento (d1)
    assert v["parametro"] == "d1"
    assert v["desde"] == "10 mm"
    assert v["hasta"] == "30 mm"
    assert v["pasos"] == 5
    assert v["interferencia"] is False


def test_prep_cmd_barrido_parametros_sin_parametros():
    """Test que verificar avisa cuando no hay parámetros para barrer."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="5"))
    cmd = BarridoParametros()
    ctx = ContextoComando(doc)
    mensaje = cmd.verificar(ctx)
    assert mensaje is None  # hay parámetros (d1)


def test_prep_cmd_barrido_parametros_sin_parametros_doc():
    """Test que verificar avisa cuando el doc no tiene parámetros barribles."""
    doc = Documento()
    # No agregar operaciones que creen parámetros automáticos
    cmd = BarridoParametros()
    ctx = ContextoComando(doc)
    mensaje = cmd.verificar(ctx)
    # Documento vacío no tiene parámetros definidos
    assert mensaje is not None