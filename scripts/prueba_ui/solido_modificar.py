# -*- coding: utf-8 -*-
"""Fase B · SÓLIDO › MODIFICAR y patrones: cada comando en la ventana real, con selección por el visor."""
import math
import sys

import arnes as A
import corredor as C
import escena

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "SÓLIDO·MODIFICAR"
pi = math.pi
caja, cil, hueca = ids["caja"], ids["cil"], ids["hueca"]


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


cuerpo = lambda cid: (lambda: [A.hit_cuerpo(v, cid)])  # noqa: E731
arista = lambda cid, **k: (lambda: [A.hit_arista(v, cid, **k)])  # noqa: E731
cara = lambda cid, **k: (lambda: [A.hit_cara(v, cid, **k)])  # noqa: E731
eje = lambda i: (lambda: [A.hit_eje(v, i)])  # noqa: E731
plano = lambda i: (lambda: [A.hit_plano(v, i)])  # noqa: E731
V_CAJA = 30 * 30 * 20

# Empalme y chaflán -----------------------------------------------------------------------------------------------------
def _hit_por_normal(normal):
    """Hit de la cara con esa normal sin clic en el visor (la cara de atrás del modelo no se puede elegir con el mouse)."""
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    estado = v.doc.estado_final
    forma = estado.cuerpos[caja].forma
    c = next(c for c in refs.subformas(forma, "cara") if sum(x * y for x, y in zip(refs.firma_cara(c)["normal"], normal, strict=True)) > 0.99)
    return hit_desde_ref(refs.referencia(caja, c, forma), estado)


run("empalme_3d", lambda: (
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm"}, foto="empalme_3d"),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm", "tipo_radio": "cuerda", "cuerda": "3 mm"}, etiqueta="empalme cuerda", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm", "tipo_radio": "variable", "radio_fin": "4 mm"}, etiqueta="empalme variable 2→4", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "100 mm"}, etiqueta="empalme radio 100 (grande)", rt=False),
    C.caso(v, AR, "empalme_3d", {"central": cara(caja, normal=(0, 0, 1)),
                                 "laterales": lambda: [_hit_por_normal((1, 0, 0)), _hit_por_normal((-1, 0, 0))]},
           {"tipo": "completo"}, etiqueta="redondeo completo (media caña)", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm", "tipo_radio": "variable", "radio_fin": "2 mm", "puntos_radio": "0.5: 4 mm"},
           etiqueta="empalme variable con punto intermedio 0.5:4", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm", "tipo_radio": "asimetrico", "radio2": "3 mm"}, etiqueta="empalme asimétrico 2/3", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm", "continuidad": "g2"}, etiqueta="empalme G2", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": lambda: [A.hit_arista(v, caja, cerca=(-85, 15, 10))],
                                 "aristas_2": lambda: [A.hit_arista(v, caja, cerca=(-100, 15, 20))]},
           {"radio": "2 mm", "radio_2": "3 mm"}, etiqueta="empalme con un segundo conjunto de aristas", rt=False),
    C.caso(v, AR, "empalme_3d", {"aristas": lambda: [A.hit_arista(v, caja, cerca=p) for p in ((-85, 15, 10), (-85, 0, 20), (-100, 15, 20))]},
           {"radio": "2 mm", "esquina": "setback", "setback": "3 mm", "cadena_tangente": False}, etiqueta="empalme esquina setback", rt=False),
    C.negativos(v, AR, "empalme_3d", {"aristas": arista(caja)}, "radio2", malos=("abc", "0 mm", "-2 mm"), vals={"tipo_radio": "asimetrico"}),
    C.negativos(v, AR, "empalme_3d", {"aristas": arista(caja)}, "radio", malos=("abc", "0 mm", "-2 mm"))))
run("chaflan_3d", lambda: (
    C.caso(v, AR, "chaflan_3d", {"aristas": arista(caja)}, {"distancia": "2 mm"}, foto="chaflan_3d"),
    C.caso(v, AR, "chaflan_3d", {"aristas": arista(caja)}, {"tipo": "dos_distancias", "distancia": "2 mm", "distancia2": "3 mm"}, etiqueta="chaflán dos distancias", rt=False),
    C.caso(v, AR, "chaflan_3d", {"aristas": arista(caja)}, {"tipo": "distancia_angulo", "distancia": "2 mm", "angulo": "30 deg"}, etiqueta="chaflán distancia-ángulo", rt=False),
    C.caso(v, AR, "chaflan_3d", {"aristas": lambda: [A.hit_arista(v, caja, cerca=p) for p in ((-85, 15, 10), (-85, 0, 20), (-100, 15, 20))]},
           {"distancia": "2 mm", "esquina": "inglete", "cadena_tangente": False}, etiqueta="chaflán, esquina inglete (tres aristas)", rt=False),
    C.caso(v, AR, "chaflan_3d", {"aristas": lambda: [A.hit_arista(v, caja, cerca=p) for p in ((-85, 15, 10), (-85, 0, 20), (-100, 15, 20))]},
           {"distancia": "2 mm", "esquina": "mezcla", "cadena_tangente": False}, etiqueta="chaflán, esquina mezcla (tres aristas)", rt=False),
    C.negativos(v, AR, "chaflan_3d", {"aristas": arista(caja)}, "distancia", malos=("abc", "0 mm", "-2 mm", "100 mm"))))

# Pulsar/Tirar ------------------------------------------------------------------------------------------------------------
run("pulsar_tirar", lambda: (
    C.caso(v, AR, "pulsar_tirar", {"objetos": cara(caja, normal=(0, 0, 1))}, {"distancia": "3 mm"}, esperado=30 * 30 * 3, foto="pulsar_tirar"),
    C.caso(v, AR, "pulsar_tirar", {"objetos": cara(caja, normal=(0, 0, 1))}, {"distancia": "-3 mm"}, esperado=-30 * 30 * 3, etiqueta="pulsar/tirar -3", rt=False),
    C.negativos(v, AR, "pulsar_tirar", {"objetos": cara(caja, normal=(0, 0, 1))}, "distancia", malos=("abc", "0 mm", "-100 mm"))))

# Vaciado ----------------------------------------------------------------------------------------------------------------------
run("vaciado", lambda: (
    C.caso(v, AR, "vaciado", {"caras": cara(caja, normal=(0, 0, 1))}, {"espesor_interior": "2 mm"}, foto="vaciado"),
    C.caso(v, AR, "vaciado", {"caras": cuerpo(caja)}, {"espesor_interior": "2 mm"}, etiqueta="vaciado del cuerpo entero (sin quitar caras)", rt=False),
    C.caso(v, AR, "vaciado", {"caras": cara(caja, normal=(0, 0, 1))}, {"espesor_interior": "2 mm", "direccion": "ambos", "espesor_exterior": "1 mm"}, etiqueta="vaciado ambos lados", rt=False),
    C.negativos(v, AR, "vaciado", {"caras": cara(caja, normal=(0, 0, 1))}, "espesor_interior", malos=("abc", "0 mm", "-2 mm", "50 mm"))))

# Desmoldeo ---------------------------------------------------------------------------------------------------------------------
run("desmoldeo", lambda: (
    C.caso(v, AR, "desmoldeo", {"plano": cara(caja, normal=(0, 0, 1)), "caras": cara(caja, normal=(1, 0, 0))}, {"angulo": "5 deg"}, foto="desmoldeo"),
    C.caso(v, AR, "desmoldeo", {"plano": plano("XY"), "herramienta_particion": plano("PM"), "caras": cara(caja, normal=(1, 0, 0))},
           {"tipo": "linea_particion", "angulo": "5 deg", "lados": "uno"}, etiqueta="desmoldeo con línea de partición (plano medio)", rt=False),
    C.caso(v, AR, "desmoldeo", {"plano": plano("XY"), "herramienta_particion": plano("PM"), "caras": cara(caja, normal=(1, 0, 0))},
           {"tipo": "linea_particion", "linea": "mover", "lado_mover": "arriba", "angulo": "5 deg"}, etiqueta="desmoldeo moviendo la línea de partición (arriba)", rt=False),
    C.negativos(v, AR, "desmoldeo", {"plano": cara(caja, normal=(0, 0, 1)), "caras": cara(caja, normal=(1, 0, 0))}, "angulo", malos=("abc", "0 deg", "-5 deg", "90 deg"))))

# Escala -----------------------------------------------------------------------------------------------------------------------------
run("escala_3d", lambda: (
    C.caso(v, AR, "escala_3d", {"cuerpos": cuerpo(caja)}, {"factor": "2"}, esperado=V_CAJA * 7, foto="escala_3d"),
    C.caso(v, AR, "escala_3d", {"cuerpos": cuerpo(caja)}, {"tipo": "no_uniforme", "fx": "2", "fy": "1", "fz": "1"}, esperado=V_CAJA, etiqueta="escala no uniforme X2", rt=False),
    C.caso(v, AR, "escala_3d", {"bocetos": lambda: [A.hit_curva(v, s, "Rect")]}, {"factor": "2"}, etiqueta="escalar un boceto entero", rt=False),
    C.negativos(v, AR, "escala_3d", {"cuerpos": cuerpo(caja)}, "factor", malos=("abc", "0", "-1", "1e9", "2 mm"))))

# Combinar ---------------------------------------------------------------------------------------------------------------------------
run("combinar", lambda: (
    C.caso(v, AR, "combinar", {"objetivo": cuerpo(caja), "herramientas": cuerpo(cil)}, {}, foto="combinar"),
    C.caso(v, AR, "combinar", {"objetivo": cuerpo(caja), "herramientas": cuerpo(cil)}, {"operacion": "cortar", "mantener": True}, etiqueta="combinar cortar y mantener", rt=False),
    C.negativos(v, AR, "combinar")))

# Desfase de cara / Reemplazar cara / Dividir ---------------------------------------------------------------------------------------
run("desfase_cara", lambda: (
    C.caso(v, AR, "desfase_cara", {"caras": cara(caja, normal=(0, 0, 1))}, {"distancia": "3 mm"}, esperado=30 * 30 * 3, foto="desfase_cara"),
    C.negativos(v, AR, "desfase_cara", {"caras": cara(caja, normal=(0, 0, 1))}, "distancia", malos=("abc", "0 mm", "-100 mm"))))
run("desfase (curvas)", lambda: (
    C.caso(v, AR, "desfase", {"objetos": cara(caja, normal=(0, 0, 1))}, {"distancia": "3 mm"}, foto="desfase",
           rt=False),   # con una cara el paso es de cara y se reabre con «Cara de desfase» (campo «caras», no «objetos»)
    C.negativos(v, AR, "desfase")))
run("reemplazar_cara", lambda: (
    C.caso(v, AR, "reemplazar_cara", {"caras": cara(caja, normal=(0, 0, 1)), "destino": plano("PM")}, {}, esperado=-30 * 30 * 10, etiqueta="reemplazar cara de arriba por plano z=10", foto="reemplazar_cara"),
    C.caso(v, AR, "reemplazar_cara", {"caras": cara(caja, normal=(0, 0, 1)), "destino": plano("PL")}, {}, etiqueta="reemplazar cara por plano que ya coincide", rt=False),
    C.negativos(v, AR, "reemplazar_cara")))
run("dividir_cara", lambda: (
    C.caso(v, AR, "dividir_cara", {"caras": cara(caja, normal=(1, 0, 0)), "herramienta": plano("PM")}, {}, esperado=0, foto="dividir_cara"),
    C.caso(v, AR, "dividir_cara", {"caras": cara(caja, normal=(0, 0, 1)), "herramienta": plano("YZ")}, {}, etiqueta="dividir cara con plano que NO la corta", rt=False),
    C.negativos(v, AR, "dividir_cara")))
run("dividir_cuerpo", lambda: (
    C.caso(v, AR, "dividir_cuerpo", {"cuerpo": cuerpo(caja), "herramienta": plano("PM")}, {}, esperado=0, foto="dividir_cuerpo"),
    C.negativos(v, AR, "dividir_cuerpo")))
run("division_silueta", lambda: (
    C.caso(v, AR, "division_silueta", {"direccion": eje("X"), "cuerpo": cuerpo(cil)}, {}, esperado=0, foto="division_silueta"),
    C.caso(v, AR, "division_silueta", {"direccion": eje("Z"), "cuerpo": cuerpo(cil)}, {}, etiqueta="división de silueta mirando el eje (sin silueta)", rt=False),
    C.caso(v, AR, "division_silueta", {"direccion": eje("X"), "cuerpo": cuerpo(cil)}, {"operacion": "solido"}, etiqueta="división de silueta, cuerpo sólido (dos cuerpos)", rt=False),
    C.negativos(v, AR, "division_silueta")))

# Mover/copiar, Alinear, Apoyar --------------------------------------------------------------------------------------------------------
run("mover_copiar", lambda: (
    C.caso(v, AR, "mover_copiar", {"cuerpos": cuerpo(caja)}, {"tipo": "traslacion", "distancia": "10 mm"}, etiqueta="mover traslación sin dirección", rt=False),
    C.caso(v, AR, "mover_copiar", {"cuerpos": cuerpo(caja), "direccion": eje("X")}, {"tipo": "traslacion", "distancia": "10 mm"}, foto="mover_copiar"),
    C.caso(v, AR, "mover_copiar", {"cuerpos": cuerpo(caja)}, {"tipo": "libre", "dx": "10 mm", "dy": "5 mm", "dz": "0 mm", "copiar": True}, esperado=V_CAJA, etiqueta="mover libre + copiar", rt=False),
    C.caso(v, AR, "mover_copiar", {"cuerpos": cuerpo(caja), "eje": eje("Z")}, {"tipo": "rotacion", "angulo": "45 deg"}, etiqueta="mover rotación 45° Z", rt=False),
    C.caso(v, AR, "mover_copiar", {"bocetos": lambda: [A.hit_curva(v, s, "Rect")]}, {"objeto": "bocetos", "tipo": "traslacion", "dx": "10 mm"},
           etiqueta="mover un boceto entero", rt=False),
    C.caso(v, AR, "mover_copiar", {"bocetos": lambda: [A.hit_curva(v, s, "Rect")]}, {"objeto": "bocetos", "tipo": "traslacion", "dx": "10 mm", "copiar": True},
           etiqueta="copiar un boceto entero", rt=False),
    C.negativos(v, AR, "mover_copiar", {"cuerpos": cuerpo(caja), "direccion": eje("X")}, "distancia", malos=("abc", "1e9 mm"), vals={"tipo": "traslacion"})))
run("alinear", lambda: (
    C.caso(v, AR, "alinear", {"cuerpos": cuerpo(caja), "origen": cara(caja, normal=(0, 0, 1)), "destino": plano("PL")}, {}, foto="alinear"),
    C.negativos(v, AR, "alinear")))
run("apoyar", lambda: (
    C.caso(v, AR, "apoyar", {"cuerpos": cuerpo(caja)}, {}, foto="apoyar"),
    C.negativos(v, AR, "apoyar")))

# Quitar empalmes (primero se hace uno) -----------------------------------------------------------------------------------------------------
def quitar():
    C.caso(v, AR, "empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm"}, deshacer=False, rt=False, etiqueta="empalme previo para quitar_empalmes")
    C.caso(v, AR, "quitar_empalmes", {"cuerpos": cuerpo(caja)}, {}, esperado=None, foto="quitar_empalmes")
    C.negativos(v, AR, "quitar_empalmes")


run("quitar_empalmes", quitar)

# Patrones -----------------------------------------------------------------------------------------------------------------------------------
run("patron_rectangular_3d", lambda: (
    C.caso(v, AR, "patron_rectangular_3d", {"cuerpos": cuerpo(caja), "dir1": eje("X")}, {"n1": 3, "d1": "50 mm"}, esperado=V_CAJA * 2, foto="patron_rectangular_3d"),
    C.negativos(v, AR, "patron_rectangular_3d", {"cuerpos": cuerpo(caja), "dir1": eje("X")}, "d1", malos=("abc", "0 mm", "-50 mm"), vals={"n1": 3})))
run("patron_circular_3d", lambda: (
    C.caso(v, AR, "patron_circular_3d", {"cuerpos": cuerpo(caja), "eje": eje("Z")}, {"n": 4}, esperado=V_CAJA * 3, foto="patron_circular_3d"),
    C.negativos(v, AR, "patron_circular_3d", {"cuerpos": cuerpo(caja), "eje": eje("Z")}, "angulo", malos=("abc", "0 deg", "-90 deg", "720 deg"), vals={"n": 4})))
run("patron_ruta", lambda: (
    C.caso(v, AR, "patron_ruta", {"cuerpos": cuerpo(caja), "ruta": lambda: [A.hit_curva(v, s, "Lin")]}, {"n1": 3, "d1": "40 mm"}, foto="patron_ruta"),
    C.negativos(v, AR, "patron_ruta", {"cuerpos": cuerpo(caja), "ruta": lambda: [A.hit_curva(v, s, "Lin")]}, "d1", malos=("abc", "0 mm", "-40 mm"), vals={"n1": 3})))
run("patron_puntos", lambda: C.negativos(v, AR, "patron_puntos"))
run("multitransformar", lambda: C.negativos(v, AR, "multitransformar"))

# Retícula volumétrica (al final: deja un cuerpo de malla en lugar de la caja) --------------------------------------------------------------------------------------------------------
run("reticula_volumetrica", lambda: (
    C.caso(v, AR, "reticula_volumetrica", {"cuerpo": cuerpo(caja)}, {"forma_celda": "cross", "tamano": "10 mm", "solidez": "25"},
           etiqueta="retícula cruz 10 mm al 25 %", rt=False, foto="reticula_volumetrica"),
    C.caso(v, AR, "reticula_volumetrica", {"cuerpo": cuerpo(caja)}, {"forma_celda": "gyroid", "tamano": "10 mm", "solidez": "30", "resolucion": 6},
           etiqueta="retícula giroide", rt=False),
    C.negativos(v, AR, "reticula_volumetrica", {"cuerpo": cuerpo(caja)}, "tamano", malos=("abc", "0 mm", "-5 mm"), vals={"forma_celda": "cross"})))

A.guardar_registro("u2b_solido_modificar")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)
