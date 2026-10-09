# -*- coding: utf-8 -*-
"""
Modelo de ejemplo: usa todas las capas (parámetros, boceto con restricciones, timeline,
extrusión, revolución, primitivas, booleanos). Lo usan la app (Ayuda → Cargar ejemplo),
las pruebas automáticas y la prueba de humo.
"""
from .restricciones import Boceto
from .timeline.documento import Documento
from .timeline.operaciones import OpBoceto, OpCombinar, OpExtrusion, OpPrimitiva, OpRevolucion


def boceto_placa():
    """Rectángulo ancho × 40 con un agujero centrado. Totalmente restringido y paramétrico."""
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (60, 40))
    esquina = b.curvas[lineas[0]].p1
    b.agregar_restriccion("fijo", [esquina])
    b.agregar_cota("distancia", [lineas[0]], "ancho")
    b.agregar_cota("distancia", [lineas[1]], "40 mm")
    agujero = b.agregar_circulo((30, 20), 6)
    centro = b.curvas[agujero].centro
    b.agregar_cota("radio", [agujero], "radio_agujero")
    b.agregar_cota("distancia_h", [esquina, centro], "ancho / 2")
    b.agregar_cota("distancia_v", [esquina, centro], "20 mm")
    return b


def boceto_perfil_revolucion():
    """Rectángulo en el plano XZ, alejado del eje Z, para revolucionarlo y formar un aro."""
    b = Boceto()
    b.agregar_rectangulo((80, 0), (86, 12))
    return b


def crear_documento_ejemplo():
    doc = Documento()
    doc.nombre = "Ejemplo"
    doc.parametros.agregar("ancho", "60 mm", comentario="Ancho de la placa")
    doc.parametros.agregar("alto_placa", "8 mm", comentario="Espesor de la placa")
    doc.parametros.agregar("radio_agujero", "6 mm")

    sk = OpBoceto(doc.nuevo_id(), "Boceto placa", plano="XY", boceto=boceto_placa())
    doc.agregar(sk)
    anillo = max(doc.estado_final.bocetos[sk.id].perfiles, key=lambda p: p.area)
    doc.agregar(OpExtrusion(doc.nuevo_id(), "Extrusión placa", boceto=sk.id,
                            perfiles=[OpExtrusion.referencia_perfil(anillo)], distancia="alto_placa"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Pilar", forma="cilindro", radio="4 mm", alto="20 mm",
                            x="10 mm", y="10 mm", z="0", operacion="unir"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Hueco esférico", forma="esfera", radio="5 mm",
                            x="45 mm", y="30 mm", z="alto_placa", operacion="cortar"))
    sk2 = OpBoceto(doc.nuevo_id(), "Boceto aro", plano="XZ", boceto=boceto_perfil_revolucion())
    doc.agregar(sk2)
    perfil = doc.estado_final.bocetos[sk2.id].perfiles[0]
    rev = OpRevolucion(doc.nuevo_id(), "Aro", boceto=sk2.id, perfiles=[OpRevolucion.referencia_perfil(perfil)],
                       eje="v", angulo="360 deg")
    doc.agregar(rev)
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Toroide", forma="toroide", radio_mayor="12 mm",
                            radio_menor="3 mm", x="-40 mm", y="0", z="5 mm"))
    cuerpos = list(doc.estado_final.cuerpos)
    doc.agregar(OpCombinar(doc.nuevo_id(), "Unir aro y toroide", objetivo=cuerpos[1],
                           herramientas=[cuerpos[2]], operacion="unir"))
    doc.modificado = False
    return doc
