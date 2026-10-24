"""Ajustes a objetos durante el dibujo de Fusion (SKT-CREATE-LINES), sin modificar el boceto."""
import math
from dataclasses import dataclass, field

from .boceto import Boceto, dominio, evaluar_primitiva, mas_cercano


@dataclass
class Inferencia:
    """Ajuste propuesto y restricción pendiente de completar con la entidad nueva.

    `restriccion` es (tipo, id_objetivo), o (tipo,) para horizontal/vertical.
    En perpendicular, un tercer elemento ("coincidente", id_objetivo) indica
    que también hay que unir el extremo nuevo al segmento. `objetivo` es None
    para horizontal/vertical; `guias` contiene segmentos en mm del plano.
    """
    tipo: str
    xy: tuple[float, float]
    objetivo: int | None
    restriccion: tuple | None
    guias: list[tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=list)


def _direccion_cercana(base, cursor, punto, angulo_tol):
    """Direcciones no nulas, en el mismo sentido y dentro de la tolerancia angular."""
    ux, uy = cursor[0] - base[0], cursor[1] - base[1]
    vx, vy = punto[0] - base[0], punto[1] - base[1]
    if math.hypot(ux, uy) <= 1e-9 or math.hypot(vx, vy) <= 1e-9:
        return False
    return abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)) <= angulo_tol


def _tangencias(prim, base):
    """Contactos desde una base exterior; normalizar la elipse reduce el cálculo al círculo unidad."""
    tipo, _, (cx, cy), a = prim[:4]
    eliptica = tipo in ("elipse", "arco_elipse")
    menor, giro = (prim[4], prim[5]) if eliptica else (a, 0.0)
    if a <= 1e-9 or menor <= 1e-9:
        return
    c, s = math.cos(giro), math.sin(giro)
    dx, dy = base[0] - cx, base[1] - cy
    x, y = (dx * c + dy * s) / a, (-dx * s + dy * c) / menor
    distancia = math.hypot(x, y)
    if distancia <= 1.0:
        return
    direccion = math.atan2(y, x)
    apertura = math.acos(1 / distancia)
    inicio = prim[6] if tipo == "arco_elipse" else prim[4] if tipo == "arco" else 0.0
    fin = dominio(prim)[1]
    for angulo in (direccion - apertura, direccion + apertura):
        parametro = (angulo - inicio) % math.tau
        if parametro <= fin + 1e-12:
            yield evaluar_primitiva(prim, min(parametro, fin))[0]


def inferir(b: Boceto, cursor_xy, tol_mm, base=None, excluir=(), coincidente=False,
            angulo_tol=math.radians(3)) -> Inferencia | None:
    """Símbolos de ajuste a objetos de Fusion: medio, tangente, perpendicular, curva y H/V.

    Distancias en mm, ángulos en radianes. Dentro de cada prioridad gana el
    ajuste más cercano al cursor; los empates se resuelven por id de curva.
    Excluir un punto excluye también sus curvas para evitar autoinferencia.
    Las tangencias y los pies deben estar a `tol_mm` del cursor y próximos a
    la curva: no se salta a un contacto lejano aunque la dirección coincida.
    Mayús (`coincidente`) conserva el ajuste al medio pero cambia su restricción.
    """
    cursor = tuple(cursor_xy)
    base = tuple(base) if base is not None else None
    excluidos = set(excluir)
    candidatos = []
    for cid, curva in b.curvas.items():
        if cid in excluidos or excluidos.intersection(curva.puntos()) or curva.tipo == "texto":
            continue
        for prim in b.primitivas(cid):
            tipo = prim[0]
            if curva.tipo in ("linea", "arco"):
                medio = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
                distancia = math.dist(cursor, medio)
                if distancia <= tol_mm:
                    restriccion = ("coincidente" if coincidente else "punto_medio", cid)
                    candidatos.append((0, distancia, cid, Inferencia("punto_medio", medio, cid, restriccion)))

            _, distancia_curva, cercano = mas_cercano(prim, cursor)
            if base is not None and distancia_curva <= tol_mm:
                if tipo in ("circulo", "arco", "elipse", "arco_elipse"):
                    for punto in _tangencias(prim, base):
                        distancia = math.dist(cursor, punto)
                        if distancia <= tol_mm and _direccion_cercana(base, cursor, punto, angulo_tol):
                            candidatos.append((1, distancia, cid, Inferencia(
                                "tangente", punto, cid, ("tangente", cid), [(base, punto)])))
                elif tipo == "linea":
                    (x, y), (fx, fy) = prim[2:4]
                    dx, dy = fx - x, fy - y
                    largo2 = dx * dx + dy * dy
                    if largo2 > 1e-18:
                        t = ((base[0] - x) * dx + (base[1] - y) * dy) / largo2
                        pie = (x + t * dx, y + t * dy)
                        distancia = math.dist(cursor, pie)
                        if distancia <= tol_mm and _direccion_cercana(base, cursor, pie, angulo_tol):
                            restriccion = ("perpendicular", cid)
                            if 0 <= t <= 1:
                                restriccion += (("coincidente", cid),)
                            candidatos.append((2, distancia, cid, Inferencia(
                                "perpendicular", pie, cid, restriccion, [(base, pie)])))

            if distancia_curva <= tol_mm:
                candidatos.append((3, distancia_curva, cid, Inferencia(
                    "sobre_curva", cercano, cid, ("coincidente", cid))))

    if candidatos:
        return min(candidatos, key=lambda c: c[:3])[3]
    if base is not None and math.dist(base, cursor) > 1e-9:
        for tipo, punto in (("horizontal", (cursor[0], base[1])), ("vertical", (base[0], cursor[1]))):
            if _direccion_cercana(base, cursor, punto, angulo_tol):
                return Inferencia(tipo, punto, None, (tipo,), [(base, punto)])
    return None
