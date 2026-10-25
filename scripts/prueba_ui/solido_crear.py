# -*- coding: utf-8 -*-
"""Fase B · SÓLIDO › CREAR: cada comando en la ventana real, con selección por el visor."""
import math
import sys

import arnes as A
import corredor as C
import escena

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "SÓLIDO·CREAR"
pi = math.pi
caja, cil, hueca, tubo = ids["caja"], ids["cil"], ids["hueca"], ids["tubo"]


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


per = lambda nombre, i=0: (lambda: [A.hit_perfil(v, s, nombre, i)])  # noqa: E731
cur = lambda nombre, i=0: (lambda: [A.hit_curva(v, s, nombre, i)])  # noqa: E731
eje = lambda i: (lambda: [A.hit_eje(v, i)])  # noqa: E731

# Extruir ---------------------------------------------------------------------------------------------------------
run("extruir", lambda: (
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm"}, esperado=20 * 10 * 15, foto="extruir"),
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "direccion": "simetrica"}, esperado=6000, etiqueta="extruir simétrico (media longitud = 15 a cada lado)"),
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "direccion": "dos_lados", "distancia2": "5 mm"}, esperado=20 * 10 * 20,
           etiqueta="extruir dos lados 15+5"),
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "invertir": True}, esperado=3000, etiqueta="extruir invertido"),
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"tipo": "delgada", "espesor": "1 mm", "distancia": "15 mm"}, etiqueta="extruir delgada 1 mm", rt=False),
    C.caso(v, AR, "extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "conicidad": "5 deg"}, etiqueta="extruir con conicidad 5°", rt=False),
    C.caso(v, AR, "extruir", {"perfiles": per("Circ")}, {"distancia": "30 mm", "operacion": "unir"}, etiqueta="extruir unir (sin objetivo)", rt=False),
    C.caso(v, AR, "extruir", {"perfiles": per("Circ")}, {"extension": "todo"}, etiqueta="extruir a todo", rt=False),
    C.negativos(v, AR, "extruir", {"perfiles": per("Rect")}, "distancia", malos=("abc", "0 mm", "-5 mm", "1e7 mm"))))

# Revolución --------------------------------------------------------------------------------------------------------
run("revolucion", lambda: (
    C.caso(v, AR, "revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, {}, esperado=pi * 100 * 20, foto="revolucion"),
    C.caso(v, AR, "revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, {"extension": "angulo", "angulo": "90 deg"}, esperado=pi * 100 * 20 / 4, etiqueta="revolución 90°"),
    C.caso(v, AR, "revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, {"extension": "angulo", "angulo": "90 deg", "direccion": "simetrica"},
           esperado=pi * 100 * 20 / 4, etiqueta="revolución 90° simétrica", rt=False),
    C.caso(v, AR, "revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, {"proyectar_eje": True}, esperado=pi * 100 * 20, etiqueta="revolución con eje proyectado", rt=False),
    C.negativos(v, AR, "revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, "angulo", malos=("abc", "0 deg", "-90 deg", "400 deg"),
                vals={"extension": "angulo"})))

# Barrido -----------------------------------------------------------------------------------------------------------
run("barrido", lambda: (
    C.caso(v, AR, "barrido", {"perfiles": per("Perf"), "ruta": cur("Ruta")}, {}, esperado=pi * 4 * 30, foto="barrido"),
    C.caso(v, AR, "barrido", {"perfiles": per("Perf"), "ruta": cur("Ruta")}, {"orientacion": "paralela"}, etiqueta="barrido paralelo", rt=False),
    C.caso(v, AR, "barrido", {"perfiles": per("Perf"), "ruta": cur("Ruta")}, {"torsion": "90 deg"}, etiqueta="barrido torsión 90°", rt=False),
    C.caso(v, AR, "barrido", {"perfiles": per("Perf"), "ruta": cur("Ruta")}, {"conicidad": "-5 deg"}, etiqueta="barrido conicidad -5°", rt=False),
    C.negativos(v, AR, "barrido")))

# Solevación ----------------------------------------------------------------------------------------------------------
run("solevacion", lambda: (
    C.caso(v, AR, "solevacion", {"secciones": lambda: [A.hit_perfil(v, s, "Circ"), A.hit_perfil(v, s, "Circ2")]}, {},
           esperado=pi * 20 / 3 * (25 + 40 + 64), foto="solevacion"),
    C.caso(v, AR, "solevacion", {"secciones": lambda: [A.hit_perfil(v, s, "Circ"), A.hit_perfil(v, s, "Circ2")]}, {"reglada": True}, etiqueta="solevación reglada", rt=False),
    C.negativos(v, AR, "solevacion")))

# Nervio y Red (sobre la caja hueca) ---------------------------------------------------------------------------------
run("nervio", lambda: (
    C.caso(v, AR, "nervio", {"curvas": cur("NerL"), "objetivo": lambda: [A.hit_cuerpo(v, hueca)]}, {"espesor": "2 mm"}, foto="nervio"),
    C.caso(v, AR, "nervio", {"curvas": cur("NerL"), "objetivo": lambda: [A.hit_cuerpo(v, hueca)]}, {"espesor": "2 mm", "extension": "profundidad", "profundidad": "5 mm"},
           etiqueta="nervio profundidad 5", rt=False),
    C.negativos(v, AR, "nervio", {"curvas": cur("NerL")}, "espesor", malos=("abc", "0 mm", "-1 mm"))))
run("red", lambda: (
    C.caso(v, AR, "red", {"curvas": cur("NerL"), "objetivo": lambda: [A.hit_cuerpo(v, hueca)]}, {"espesor": "2 mm"}, foto="red"),
    C.negativos(v, AR, "red")))

# Repujado ---------------------------------------------------------------------------------------------------------------
run("repujado", lambda: (
    C.caso(v, AR, "repujado", {"perfiles": per("Rep"), "caras": lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]}, {"profundidad": "1 mm"}, foto="repujado"),
    C.negativos(v, AR, "repujado")))

# Agujero ---------------------------------------------------------------------------------------------------------------
sup_caja = lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]  # noqa: E731
run("agujero", lambda: (
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"diametro": "6 mm", "profundidad": "8 mm"}, esperado=-pi * 9 * 8, foto="agujero"),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"diametro": "6 mm", "extension": "todo"}, esperado=-pi * 9 * 20, etiqueta="agujero a todo", rt=False),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"diametro": "6 mm", "profundidad": "8 mm", "tipo": "abocardado"}, etiqueta="agujero abocardado", rt=False),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"diametro": "6 mm", "profundidad": "8 mm", "tipo": "avellanado"}, etiqueta="agujero avellanado", rt=False),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"profundidad": "8 mm", "rosca": "holgura", "tam_holgura": "M6"}, etiqueta="agujero holgura M6", rt=False),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"profundidad": "8 mm", "rosca": "cosmetica", "tam_iso_metrica": "M6"}, etiqueta="agujero rosca cosmética M6", rt=False),
    C.caso(v, AR, "agujero", {"colocacion": sup_caja}, {"profundidad": "8 mm", "rosca": "modelada", "tam_iso_metrica": "M6"}, etiqueta="agujero rosca modelada M6", rt=False),
    C.negativos(v, AR, "agujero", {"colocacion": sup_caja}, "diametro", malos=("abc", "0 mm", "-3 mm", "500 mm"))))

# Rosca ---------------------------------------------------------------------------------------------------------------------
cara_cil = lambda: [A.hit_cara(v, cil)]  # noqa: E731
run("rosca", lambda: (
    C.caso(v, AR, "rosca", {"caras": cara_cil}, {}, foto="rosca"),
    C.caso(v, AR, "rosca", {"caras": cara_cil}, {"modelada": True, "longitud": "10 mm"}, etiqueta="rosca modelada 10 mm", rt=False),
    C.caso(v, AR, "rosca", {"caras": cara_cil}, {"modelada": True, "longitud": "10 mm", "mano": "izquierda"}, etiqueta="rosca modelada izquierda", rt=False),
    C.negativos(v, AR, "rosca", {"caras": cara_cil}, "longitud", malos=("abc", "0 mm", "-3 mm"), vals={"modelada": True, "largo_completo": False})))

# Primitivas -----------------------------------------------------------------------------------------------------------------
pl = lambda: [A.hit_plano(v, "XY")]  # noqa: E731
run("caja", lambda: (
    C.caso(v, AR, "caja", {"centro": pl}, {"ancho": "10 mm", "largo": "20 mm", "alto": "5 mm", "x": "300 mm"}, esperado=1000, foto="caja"),
    C.negativos(v, AR, "caja", {"centro": pl}, "alto", malos=("abc", "0 mm", "-5 mm"), vals={"ancho": "10 mm", "largo": "20 mm", "x": "300 mm"})))
run("cilindro", lambda: (
    C.caso(v, AR, "cilindro", {"centro": pl}, {"diametro": "10 mm", "alto": "20 mm", "x": "300 mm"}, esperado=pi * 25 * 20, foto="cilindro"),
    C.negativos(v, AR, "cilindro", {"centro": pl}, "diametro", malos=("abc", "0 mm", "-5 mm"), vals={"alto": "20 mm", "x": "300 mm"})))
run("esfera", lambda: (
    C.caso(v, AR, "esfera", {"centro": pl}, {"diametro": "10 mm", "x": "300 mm"}, esperado=4 / 3 * pi * 125, foto="esfera"),
    C.negativos(v, AR, "esfera", {"centro": pl}, "diametro", malos=("abc", "0 mm", "-5 mm"), vals={"x": "300 mm"})))
run("toroide", lambda: (
    C.caso(v, AR, "toroide", {"centro": pl}, {"diametro": "20 mm", "diametro_tubo": "4 mm", "x": "300 mm"}, esperado=2 * pi ** 2 * 10 * 4, foto="toroide"),
    C.caso(v, AR, "toroide", {"centro": pl}, {"diametro": "4 mm", "diametro_tubo": "10 mm", "x": "300 mm"}, etiqueta="toroide tubo mayor que el aro", rt=False)))

# Bobina y tubería ----------------------------------------------------------------------------------------------------------
run("bobina", lambda: (
    C.caso(v, AR, "bobina", {"plano": pl}, {"diametro": "20 mm", "revoluciones": "3", "altura": "30 mm", "tamano": "2 mm"}, foto="bobina"),
    C.caso(v, AR, "bobina", {"plano": pl}, {"diametro": "20 mm", "revoluciones": "3", "altura": "30 mm", "tamano": "2 mm", "seccion": "cuadrada"}, etiqueta="bobina sección cuadrada", rt=False),
    C.negativos(v, AR, "bobina", {"plano": pl}, "diametro", malos=("abc", "0 mm", "-5 mm"), vals={"revoluciones": "3", "altura": "30 mm", "tamano": "2 mm"})))
run("tuberia", lambda: (
    C.caso(v, AR, "tuberia", {"ruta": cur("Ruta")}, {"tamano": "4 mm"}, esperado=pi * 4 * 30, foto="tuberia"),
    C.caso(v, AR, "tuberia", {"ruta": cur("Ruta")}, {"tamano": "4 mm", "hueca": True, "espesor": "1 mm"}, etiqueta="tubería hueca", rt=False),
    C.negativos(v, AR, "tuberia", {"ruta": cur("Ruta")}, "tamano", malos=("abc", "0 mm", "-5 mm"))))

# Simetría / Envolvente / Relleno de contorno ------------------------------------------------------------------------------
run("simetria_3d", lambda: (
    C.caso(v, AR, "simetria_3d", {"cuerpos": lambda: [A.hit_cuerpo(v, caja)], "plano": lambda: [A.hit_plano(v, "YZ")]}, {}, foto="simetria_3d"),
    C.caso(v, AR, "simetria_3d", {"cuerpos": lambda: [A.hit_cuerpo(v, caja)], "plano": lambda: [A.hit_plano(v, "YZ")]}, {"combinar": True}, etiqueta="simetría combinada", rt=False),
    C.negativos(v, AR, "simetria_3d")))
run("cuerpo_envolvente", lambda: (
    C.caso(v, AR, "cuerpo_envolvente", {"cuerpos": lambda: [A.hit_cuerpo(v, cil)]}, {}, esperado=20 * 20 * 30, foto="cuerpo_envolvente"),
    C.caso(v, AR, "cuerpo_envolvente", {"cuerpos": lambda: [A.hit_cuerpo(v, cil)]}, {"tipo": "cilindro"}, esperado=pi * 100 * 30, etiqueta="envolvente cilindro", rt=False),
    C.caso(v, AR, "cuerpo_envolvente", {"cuerpos": lambda: [A.hit_cuerpo(v, cil)]}, {"tipo": "tubo", "espesor_tubo": "1 mm"}, esperado=pi * (100 - 81) * 30, etiqueta="envolvente tubo", rt=False),
    C.caso(v, AR, "cuerpo_envolvente", {"cuerpos": lambda: [A.hit_cuerpo(v, cil)]}, {"orientacion": "automatica"}, esperado=20 * 20 * 30, etiqueta="envolvente automática", rt=False),
    C.negativos(v, AR, "cuerpo_envolvente")))
run("relleno_contorno", lambda: C.negativos(v, AR, "relleno_contorno"))
run("patron_geometrico", lambda: (
    C.caso(v, AR, "patron_geometrico", {"caras": lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]},
           {"tamano1": "2 mm", "tamano2": "4 mm", "distancia": "6 mm", "operacion": "cortar"}, etiqueta="patrón geométrico de esferas (cortar)", rt=False, foto="patron_geometrico"),
    C.caso(v, AR, "patron_geometrico", {"caras": lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]},
           {"objeto": "cilindro", "distribucion": "hexagonal", "tamano1": "2 mm", "tamano2": "2 mm", "distancia": "6 mm", "operacion": "unir"},
           etiqueta="patrón geométrico hexagonal de cilindros (unir)", rt=False),
    C.negativos(v, AR, "patron_geometrico", {"caras": lambda: [A.hit_cara(v, caja, normal=(0, 0, 1))]}, "distancia", malos=("abc", "0 mm", "-5 mm"))))

A.guardar_registro("u2a_solido_crear")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)
