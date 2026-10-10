# -*- coding: utf-8 -*-
"""
Reparar cuerpos (INSPECCIONAR › Revisar geometría › Reparar): el paso del timeline que deja arreglado lo que
`nucleo.revision.revisar` encontró. Equivale a FreeCAD Part › Check Geometry (reparar), Set Tolerance y Refine
Shape, y a «Hacer manifold» de la caja de impresión 3D de Blender. Revisar no deja paso (es un informe, como
Medir); Reparar sí, y se edita con doble clic como cualquier otro.
"""
from ..nucleo import geometria as geo
from .operaciones import ErrorOperacion, Operacion, _deps_objetivo, registrar_operacion


def _rv():
    from ..nucleo import revision
    return revision


class OpReparar(Operacion):
    """Reparar cuerpo: B-rep → coser (si tiene aristas libres), bajar las tolerancias mayores que `tolerancia`,
    ShapeFix y refinar (unir caras coplanares); malla → `malla.reparar(tipo="coser_y_quitar")` (une vértices a
    menos de `tolerancia`, orienta normales y cierra agujeros). `tolerancia` "0 mm" = sin tope. Si al terminar el
    cuerpo sigue inválido o abierto, el paso queda con aviso (no con error: lo que se pudo arreglar queda)."""
    TIPO, ETIQUETA, ICONO = "reparar_cuerpo", "Reparar cuerpo", "✓"
    PARAMS = {"cuerpos": [], "tolerancia": "0.01 mm", "coser": True, "refinar": True, "arreglar": True}
    EXPRESIONES = ("tolerancia",)

    def dependencias(self):
        return (super().dependencias() | _deps_objetivo(self.p.get("cuerpos"))) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a reparar.")
        tol = ctx.evaluar(self.p["tolerancia"])
        if tol < 0:
            raise ErrorOperacion("La tolerancia de reparación no puede ser negativa.")
        rv = _rv()
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            malla = getattr(c, "tipo", "solido") == "malla"
            nueva = rv.reparar(c.forma, tolerancia=tol, coser=bool(self.p["coser"]), refinar=bool(self.p["refinar"]),
                               arreglar=bool(self.p["arreglar"]))
            c.forma = nueva
            if malla:
                if not nueva.es_cerrada():
                    ctx.aviso(f"{c.nombre}: la malla sigue abierta después de reparar.")
                continue
            if geo.solidos(nueva):
                c.tipo = "solido"                     # coser cerró una superficie: pasa a sólido, como Fusion
            if not geo.es_valida(nueva):
                ctx.aviso(f"{c.nombre} sigue inválido después de reparar: probá con otra tolerancia "
                          "(INSPECCIONAR › Revisar geometría dice qué falla).")
            elif c.tipo == "solido" and not rv.es_estanca(nueva):
                ctx.aviso(f"{c.nombre} sigue abierto (aristas libres): coser no alcanzó con esa tolerancia.")


registrar_operacion(OpReparar)
