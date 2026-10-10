# -*- coding: utf-8 -*-
"""
SÓLIDO › CREAR › Prisma rectangular, Cilindro, Esfera y Toroide como comandos con panel, vista previa y
manipuladores (Fusion: SLD-BOX-SOLID, SLD-CYLINDER-SOLID, SLD-SPHERE-SOLID, SLD-TORUS-SOLID). Reemplazan al
diálogo viejo `dialogos.DialogoPrimitiva` (X/Y/Z escritos a mano y RADIO).

Como en Fusion se hace clic en un plano o una cara plana: donde se hace clic queda el centro (con enganche al
centro, las esquinas y los puntos medios de la cara), y se puede arrastrar con el aro sobre el plano. También
sirve un punto o un vértice. Las medidas redondas se piden como DIÁMETRO, con asas en la vista para tirar del
diámetro y de la altura. Sin selección valen los campos Posición X/Y/Z (expresiones con parámetros).

El paso del timeline sigue siendo `OpPrimitiva` (la receta no cambia): guarda RADIOS (el diámetro se traduce:
«20 mm» → radio «10 mm»; con parámetros, «d_eje» → «(d_eje) / 2») y la posición X/Y/Z. Limitación honesta:
`OpPrimitiva` no guarda un plano, así que la caja, el cilindro y el toroide se crean con el eje en Z (sobre un
plano o una cara horizontal; sobre una cara que mira hacia abajo crecen hacia abajo). Para otra orientación,
girarlos después con Mover/copiar. La esfera acepta cualquier plano.
"""
import re

import numpy as np

from ...timeline import entidades as ent
from ...timeline.operaciones import OpPrimitiva
from ...timeline.parametros import nombres_usados
from ..comando import Comando, ErrorComando, Expresion, Info, Seleccion, hits
from . import registrar
from .comunes import campo_operacion, evaluar_o_cero

FILTROS_CENTRO = {"plano", "cara_plana", "punto", "vertice"}
_MITAD = re.compile(r"^\((.*)\)\s*/\s*2$")


def _mm(valor):
    """Número como lo escribe el panel: «12.5 mm» (sin ceros de más ni «-0»)."""
    texto = f"{float(valor):.6f}".rstrip("0").rstrip(".")
    return f"{'0' if texto in ('-0', '') else texto} mm"


def radio_desde_diametro(expr, ctx):
    """Radio a guardar en `OpPrimitiva` a partir del diámetro del panel: número → la mitad («20 mm» → «10 mm»);
    con parámetros → «(expr) / 2», así el paso sigue al parámetro."""
    texto = str(expr).strip()
    valor = ctx.evaluar(texto)
    return f"({texto}) / 2" if nombres_usados(texto) else _mm(valor / 2)


def diametro_desde_radio(expr, ctx):
    """Lo inverso, para editar un paso: «(d) / 2» → «d»; «10 mm» → «20 mm»; otro → «2 * (expr)»."""
    texto = str(expr).strip()
    m = _MITAD.match(texto)
    if m:
        return m.group(1).strip()
    if not nombres_usados(texto):
        try:
            return _mm(2 * ctx.evaluar(texto))
        except Exception:  # noqa: BLE001 — una expresión rota se muestra tal cual, para corregirla
            pass
    return f"2 * ({texto})"


def _sin_seleccion(v):
    return not v.get("centro")


def _con_operacion(v):
    return v.get("operacion") != "nuevo"


class _Primitiva(Comando):
    """Base de las cuatro primitivas. `MEDIDAS`: [(campo del panel, etiqueta, defecto, clave en OpPrimitiva,
    es_diametro)]."""
    CLASE_OP = OpPrimitiva
    FORMA = ""
    MEDIDAS = []
    CRECE_EN_Z = True               # caja y cilindro: la altura crece desde la base (hacia abajo en una cara de abajo)
    CUALQUIER_PLANO = False         # la esfera no tiene orientación

    # ------------------------------------------------------------ campos
    def campos(self, ctx):
        medidas = [Expresion(c, et, d, ayuda=("Se guarda como radio (la mitad)." if diam else ""))
                   for c, et, d, _k, diam in self.MEDIDAS]
        return [Seleccion("centro", "Plano / punto", FILTROS_CENTRO, minimo=0,
                          ayuda="Clic en un plano o una cara plana (el centro queda donde hacés clic; se arrastra con el "
                                "aro) o en un punto o vértice. Sin selección: Posición X/Y/Z.")] + medidas + [
            Expresion("x", "Posición X", "0 mm", visible_si=_sin_seleccion),
            Expresion("y", "Posición Y", "0 mm", visible_si=_sin_seleccion),
            Expresion("z", "Posición Z", "0 mm", visible_si=_sin_seleccion),
            Info("posicion", "Posición", self._texto_posicion),
            campo_operacion("nuevo"),
            Seleccion("objetivo", "Cuerpo", {"cuerpo"}, minimo=0, maximo=1, visible_si=_con_operacion,
                      ayuda="Cuerpo que se une, corta o interseca. Sin selección: los que toca.")]

    def nombre_nuevo(self, ctx):
        base = OpPrimitiva.ETIQUETAS[self.FORMA]
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"

    # ------------------------------------------------------------ posición
    def _centro_elegido(self, hit, ctx):
        """(punto 3D, normal del plano o None) de lo elegido en «Plano / punto»."""
        punto, plano = hit.get("punto"), hit.get("plano")
        if punto is None or (plano is None and hit["ref"].get("tipo") in ("plano", "cara")):
            try:
                e = ent.resolver(hit["ref"], ctx.estado)
            except Exception as ex:  # noqa: BLE001
                raise ErrorComando(f"No se encuentra lo elegido: {ex}") from ex
            plano = plano if plano is not None else e.plano
            if punto is None:
                punto = e.punto if e.punto is not None else (plano.origen if plano is not None else None)
        if punto is None:
            raise ErrorComando("Elegí un plano, una cara plana, un punto o un vértice.")
        normal = None
        if hit["ref"].get("tipo") in ("plano", "cara") and plano is not None:
            normal = np.asarray(plano.normal, float)
            if not self.CUALQUIER_PLANO and abs(abs(normal[2]) - 1.0) > 1e-6:
                nombre = {"caja": "la caja", "cilindro": "el cilindro", "toroide": "el toroide"}[self.FORMA]
                raise ErrorComando(f"Por ahora {nombre} se crea con el eje en Z: "
                                   "elegí un plano o una cara horizontal (o un punto) y giralo después con "
                                   "Mover/copiar.")
        return np.asarray(punto, float).reshape(3), normal

    def posicion(self, v, ctx):
        """(x, y, z, caja_centrada) a guardar. Con algo elegido, el centro (o el centro de la base) sale de ahí."""
        sel = v.get("centro") or []
        caja = self.FORMA == "caja"
        if not sel:
            centrada = bool(ctx.op.p.get("caja_centrada")) if (ctx.op is not None and caja) else caja
            for k in ("x", "y", "z"):
                ctx.evaluar(v[k])
            return str(v["x"]), str(v["y"]), str(v["z"]), centrada
        punto, normal = self._centro_elegido(sel[0], ctx)
        z = _mm(punto[2])
        if self.CRECE_EN_Z and normal is not None and normal[2] < 0:     # cara que mira hacia abajo: crece hacia abajo
            z = f"{z} - ({v['alto']})"
        return _mm(punto[0]), _mm(punto[1]), z, caja

    def _texto_posicion(self, v, ctx):
        try:
            x, y, z, centrada = self.posicion(v, ctx)
            p = [ctx.evaluar(t) for t in (x, y, z)]
        except Exception:  # noqa: BLE001 — el error ya lo muestra el panel
            return ""
        que = {"caja": "Centro de la base" if centrada else "Esquina mínima", "cilindro": "Centro de la base"}.get(
            self.FORMA, "Centro")
        return f"{que}: ({'; '.join(f'{c:.6g}' for c in p)}) mm" + (" · eje Z" if self.FORMA != "esfera" else "")

    def _base_numerica(self, v, ctx):
        """Centro (esfera, toroide) o centro de la base (caja, cilindro) en números, y sentido de la altura."""
        x, y, z, centrada = self.posicion(v, ctx)
        p = np.array([evaluar_o_cero(ctx, t) for t in (x, y, z)])
        if self.FORMA == "caja" and not centrada:
            p += (evaluar_o_cero(ctx, v.get("ancho")) / 2, evaluar_o_cero(ctx, v.get("largo")) / 2, 0.0)
        sel = v.get("centro") or []
        sentido = 1.0
        if sel and self.CRECE_EN_Z:
            _p, normal = self._centro_elegido(sel[0], ctx)
            if normal is not None and normal[2] < 0:
                sentido = -1.0
                p[2] += evaluar_o_cero(ctx, v.get("alto"))      # la base queda sobre la cara (arriba)
        return p, sentido

    # ------------------------------------------------------------ operación
    def construir(self, v, ctx):
        params = dict(ctx.op.p) if ctx.op is not None else {}
        for campo, etiqueta, _d, clave, diametro in self.MEDIDAS:
            valor = ctx.evaluar(v[campo])
            if not valor > 0:
                raise ErrorComando(f"{etiqueta}: tiene que ser mayor que cero.")
            params[clave] = radio_desde_diametro(v[campo], ctx) if diametro else str(v[campo])
        if self.FORMA == "toroide" and not ctx.evaluar(params["radio_menor"]) < ctx.evaluar(params["radio_mayor"]):
            raise ErrorComando("El diámetro del tubo tiene que ser menor que el diámetro mayor.")
        x, y, z, centrada = self.posicion(v, ctx)
        objetivo = [h["ref"]["cuerpo"] for h in v.get("objetivo") or [] if h["ref"].get("tipo") == "cuerpo"]
        params.update(forma=self.FORMA, x=x, y=y, z=z, caja_centrada=centrada, operacion=v.get("operacion", "nuevo"),
                      objetivo=objetivo[0] if objetivo and v.get("operacion") != "nuevo" else "")
        return self.crear_op(OpPrimitiva, v, ctx, **params)

    def desde_op(self, op, ctx):
        p = op.p
        valores = {"centro": [], "x": p["x"], "y": p["y"], "z": p["z"], "operacion": p.get("operacion", "nuevo"),
                   "objetivo": hits([{"tipo": "cuerpo", "cuerpo": p["objetivo"]}], ctx.estado) if p.get("objetivo")
                   else []}
        for campo, _et, _d, clave, diametro in self.MEDIDAS:
            valores[campo] = diametro_desde_radio(p[clave], ctx) if diametro else p[clave]
        return valores

    def ajustar_hit(self, campo, hit, ctx, visor):
        """Clic en una cara: el centro se engancha al centro de la cara, a una esquina o a un punto medio si queda a
        menos de ENGANCHE_PX píxeles (como el Agujero y como Fusion)."""
        from .. import manipuladores as mp
        if campo.clave != "centro" or hit["ref"].get("tipo") != "cara" or hit.get("punto") is None:
            return None
        e = mp.entidad(hit, ctx.estado)
        try:
            cands = mp.puntos_enganche_cara(e.forma) if e is not None and e.forma is not None else []
        except Exception:  # noqa: BLE001 — sin enganches vale el punto del clic
            return None
        if not cands:
            return None
        s, ok = visor.puntos_pantalla(np.array([c[0] for c in cands] + [hit["punto"]], float))
        s, ok = np.asarray(s, float), np.asarray(ok, bool)
        if not ok[-1]:
            return None
        d = np.linalg.norm(s[:-1] - s[-1], axis=1)
        d[~ok[:-1]] = np.inf
        i = int(np.argmin(d))
        return dict(hit, punto=np.asarray(cands[i][0], float)) if d[i] <= mp.ENGANCHE_PX else None

    # ------------------------------------------------------------ manipuladores
    def manipuladores(self, ctx, v):
        """Aro para mover el centro por el plano (con enganches en la cara) y asas de diámetro y altura."""
        from .. import manipuladores as mp
        try:
            base, sentido = self._base_numerica(v, ctx)
        except Exception:  # noqa: BLE001 — sin posición válida no hay asas
            return []
        asas = []
        sel = v.get("centro") or []
        if sel and sel[0]["ref"].get("tipo") in ("plano", "cara"):
            hit = sel[0]
            try:
                punto, normal = self._centro_elegido(hit, ctx)
            except ErrorComando:
                punto, normal = None, None
            if punto is not None:
                def al_mover(q, hit=hit):
                    return {"centro": [dict(hit, punto=np.asarray(q, float))]}
                cands = []
                if hit["ref"]["tipo"] == "cara":
                    e = mp.entidad(hit, ctx.estado)
                    try:
                        cands = mp.puntos_enganche_cara(e.forma) if e is not None and e.forma is not None else []
                    except Exception:  # noqa: BLE001 — sin enganches, el centro se mueve libre
                        cands = []
                asas.append(mp.Posicion("centro", punto, normal, al_mover, candidatos=cands))
        elif not sel:
            centrada = self.FORMA != "caja" or self.posicion(v, ctx)[3]
            dx = evaluar_o_cero(ctx, v.get("ancho")) / 2 if not centrada else 0.0
            dy = evaluar_o_cero(ctx, v.get("largo")) / 2 if not centrada else 0.0

            def al_mover(q):
                return {"x": float(q[0]) - dx, "y": float(q[1]) - dy}
            asas.append(mp.Posicion("centro", base, (0.0, 0.0, 1.0), al_mover))
        asas += self.asas_medidas(base, sentido)
        return asas

    def asas_medidas(self, base, sentido):
        return []


class Caja(_Primitiva):
    CLAVE, TITULO, ICONO, FORMA = "caja", "Prisma rectangular", "caja", "caja"
    AYUDA = ("Prisma rectangular (Fusion: Box): clic en un plano o una cara para ubicar el centro de la base; ancho, "
             "largo y alto con asas en la vista.")
    VARIANTE = ("forma", "caja")
    MEDIDAS = [("ancho", "Ancho (X)", "20 mm", "ancho", False), ("largo", "Largo (Y)", "20 mm", "largo", False),
               ("alto", "Alto (Z)", "20 mm", "alto", False)]

    def asas_medidas(self, base, sentido):
        from .. import manipuladores as mp
        return [mp.AsaRadial("ancho", base, (1.0, 0.0, 0.0), factor=0.5, minimo=0.01),
                mp.AsaRadial("largo", base, (0.0, 1.0, 0.0), factor=0.5, minimo=0.01),
                mp.Flecha("alto", base, (0.0, 0.0, sentido), minimo=0.01)]


class Cilindro(_Primitiva):
    CLAVE, TITULO, ICONO, FORMA = "cilindro", "Cilindro", "cilindro", "cilindro"
    AYUDA = ("Cilindro (Fusion: Cylinder): clic en un plano o una cara para el centro de la base, Diámetro y Alto, "
             "con asas en la vista.")
    VARIANTE = ("forma", "cilindro")
    MEDIDAS = [("diametro", "Diámetro", "20 mm", "radio", True), ("alto", "Alto", "20 mm", "alto", False)]

    def asas_medidas(self, base, sentido):
        from .. import manipuladores as mp
        return [mp.AsaRadial("diametro", base, (1.0, 0.0, 0.0), factor=0.5, minimo=0.01),
                mp.Flecha("alto", base, (0.0, 0.0, sentido), minimo=0.01)]


class Esfera(_Primitiva):
    CLAVE, TITULO, ICONO, FORMA = "esfera", "Esfera", "esfera", "esfera"
    AYUDA = "Esfera (Fusion: Sphere): clic en un plano, una cara o un punto para el centro y Diámetro, con asa en la vista."
    VARIANTE = ("forma", "esfera")
    MEDIDAS = [("diametro", "Diámetro", "20 mm", "radio", True)]
    CRECE_EN_Z, CUALQUIER_PLANO = False, True

    def asas_medidas(self, base, sentido):
        from .. import manipuladores as mp
        return [mp.AsaRadial("diametro", base, (1.0, 0.0, 0.0), factor=0.5, minimo=0.01)]


class Toroide(_Primitiva):
    CLAVE, TITULO, ICONO, FORMA = "toroide", "Toroide", "toroide", "toroide"
    AYUDA = ("Toroide (Fusion: Torus): clic en un plano o una cara horizontal para el centro, diámetro mayor (del "
             "círculo que recorre el centro del tubo) y diámetro del tubo.")
    VARIANTE = ("forma", "toroide")
    MEDIDAS = [("diametro", "Diámetro mayor", "40 mm", "radio_mayor", True),
               ("diametro_tubo", "Diámetro del tubo", "10 mm", "radio_menor", True)]
    CRECE_EN_Z = False

    def asas_medidas(self, base, sentido):
        from .. import manipuladores as mp
        return [mp.AsaRadial("diametro", base, (1.0, 0.0, 0.0), factor=0.5, minimo=0.01)]


registrar(Caja, Cilindro, Esfera, Toroide)
