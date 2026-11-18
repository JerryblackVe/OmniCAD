"""P-158: los mensajes de los paneles de Bocetos y Sólido son de 1 renglón (regla 14 de CLAUDE.md).

Límite medido: el panel «simple» mide 320 px (`formulario.ANCHOS`); descontando 44 px de márgenes y el símbolo quedan
276 px, y con la fuente por defecto (Sans Serif 9 pt, unos 6,3 px por letra) entran unos 44 caracteres.
Trinquete: cada archivo tiene el tope de mensajes que todavía pasan el límite. Solo puede bajar: un mensaje largo nuevo
falla, y acortar uno obliga a bajar el tope. La lista completa está en `docs/auditoria_mensajes_paneles.md`."""
import ast
import re
from pathlib import Path

import pytest

LIMITE = 45
HUECO = 6        # lo que ocupa un valor «{}» al mostrarse (p. ej. «36,26 mm»)
RAIZ = Path(__file__).resolve().parent.parent / "omnicad"
NOMBRES = {"ErrorGeometria", "ErrorOperacion", "ErrorComando", "ErrorBoceto", "exigir", "_mostrar"}
TOPES = {
    "nucleo/malla.py": 0,
    "nucleo/render_cpu.py": 0,
    "timeline/ops_chapa.py": 0,
    "timeline/ops_engranaje.py": 0,
    "nucleo/engranajes.py": 0,
    "nucleo/chapa.py": 0,
    "nucleo/tolerancias.py": 0,
    "nucleo/fijaciones.py": 0,
    "nucleo/preajustes.py": 0,
    "nucleo/plastico.py": 0,
    "ui/comandos/chapa.py": 0,
    "ui/comandos/malla.py": 0,
    "nucleo/aspectos.py": 0,
    "nucleo/calcomanias.py": 0,
    "nucleo/calibracion.py": 0,
    "ui/render.py": 0,
    "nucleo/comparar_malla.py": 0,
    "nucleo/simplificar.py": 0,
    "nucleo/sustentabilidad.py": 0,
    "timeline/posicion.py": 0,
    "nucleo/dibujo.py": 0,
    "nucleo/reticula.py": 0,
    "nucleo/malla_seccion.py": 0,
    "timeline/ops_derivacion.py": 0,
    "restricciones/boceto3d.py": 0,
    "ui/editor_boceto.py": 0,
    "ui/editor_boceto_comun.py": 0,
    "ui/editor_boceto_base.py": 0,
    "ui/editor_boceto_crear.py": 0,
    "ui/editor_boceto_modificar.py": 0,
    "ui/editor_boceto_proyeccion.py": 0,
    "ui/editor_boceto_texto.py": 0,
    "ui/editor_boceto_cotas.py": 0,
    "ui/editor_boceto_restricciones.py": 0,
    "ui/editor_boceto_interaccion.py": 0,
    "ui/editor_boceto_dibujo.py": 0,
    "nucleo/curvas3d.py": 0,
    "nucleo/patron_geometrico.py": 0,
    "api/herramientas_boceto.py": 0,
    "api/herramientas_boceto_extra.py": 0,
    "nucleo/revision.py": 0,
    "nucleo/perfiles.py": 0,
    "ui/comandos/proyectar_boceto.py": 0,
    "ui/comandos/insertar_en_boceto.py": 0,
    "ui/modo_boceto.py": 0,
    "timeline/documento.py": 0,
    "nucleo/desfase_aristas.py": 0,
    "nucleo/seleccion_por_limite.py": 0,
    "restricciones/solver.py": 0,
    "timeline/aspectos_doc.py": 0,
    "timeline/ops_fijacion.py": 0,
    "timeline/ops_grafo.py": 0,
    "ui/comandos/derivacion.py": 0,
    "api/herramientas_vectores.py": 0,
    "nucleo/motor.py": 0,
    "timeline/ops_insertar.py": 0,
    "timeline/ops_revision.py": 0,
    "ui/comando.py": 0,
    "ui/comandos/aspecto.py": 0,
    "ui/comandos/comunes.py": 0,
    "ui/comandos/revision.py": 0,
    "ui/comandos/sustentabilidad.py": 0,
    "ui/objetos_vectoriales.py": 0,
    "api/herramientas_objetos_vectoriales.py": 0,
    "nucleo/formas_malla.py": 0,
    "nucleo/intercambio.py": 0,
    "nucleo/solidos_crear.py": 0,
    "nucleo/solidos_crear_occ.py": 0,
    "nucleo/solidos_crear_comun.py": 0,
    "nucleo/solidos_crear_extrusion.py": 0,
    "nucleo/solidos_crear_revolucion.py": 0,
    "nucleo/solidos_crear_barrido.py": 0,
    "nucleo/solidos_crear_solevacion.py": 0,
    "nucleo/solidos_crear_nervios.py": 0,
    "nucleo/solidos_crear_repujado.py": 0,
    "nucleo/solidos_crear_agujeros.py": 0,
    "nucleo/solidos_crear_roscas.py": 0,
    "nucleo/solidos_crear_bobina_tuberia.py": 0,
    "nucleo/solidos_crear_patrones.py": 0,
    "nucleo/solidos_crear_volumenes.py": 0,
    "nucleo/solidos_crear_plastico.py": 0,
    "nucleo/solidos_modificar.py": 0,
    "timeline/ops_solido.py": 0,
    "restricciones/boceto.py": 0,
    "ui/comandos/crear.py": 0,
    "ui/comandos/modificar.py": 0,
    "ui/comandos/solido.py": 0,
    "ui/comandos/primitivas.py": 0,
    "ui/comandos/patrones.py": 0,
    "ui/manipuladores.py": 0,
    "nucleo/superficies.py": 0,
    "timeline/ops_superficie.py": 0,
    "ui/comandos/superficie.py": 0,
    "nucleo/editar_cara.py": 0,
    "timeline/ops_modificar.py": 0,
    "nucleo/vectores.py": 0,
    "nucleo/analisis.py": 0,
    "nucleo/construccion.py": 0,
    "nucleo/geometria.py": 0,
    "timeline/operaciones.py": 0,
    "ui/comandos/ensamblar.py": 0,
    "timeline/ops_ensamblar.py": 0,
    "ui/comandos/construir.py": 0,
    "ui/comandos/inspeccionar.py": 0,
    "timeline/ops_construir.py": 0,
}


def _textos(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        yield n.value
    elif isinstance(n, ast.JoinedStr):
        yield "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format":
        yield from _textos(n.func.value)


def largos(archivo):
    """Los mensajes de errores y avisos de `archivo` que pasan del límite: [(línea, largo, texto)]."""
    arbol = ast.parse((RAIZ / archivo).read_text(encoding="utf-8"))
    salida = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call) and n.args:
            f = n.func
            if (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "") in NOMBRES:
                for t in _textos(n.args[0]):
                    largo = len(re.sub(r"\{[^}]*\}", "x" * HUECO, t))
                    if largo > LIMITE:
                        salida.append((n.lineno, largo, t))
    return salida


@pytest.mark.parametrize("archivo", TOPES)
def test_mensajes_de_panel_de_1_renglon(archivo):
    n = len(largos(archivo))
    assert n <= TOPES[archivo], (f"{archivo}: {n} mensajes pasan de {LIMITE} caracteres (tope {TOPES[archivo]}): "
                                 f"acortá el nuevo; ejemplos: {largos(archivo)[:2]}")
    assert n == TOPES[archivo], f"{archivo}: ahora son {n}; bajá el tope a {n} en TOPES"


def test_el_empalme_de_gerardo_ya_no_tiene_6_renglones():
    """El caso de Gerardo (2026-11-15): «el asa frena en 36.26 mm… reordená los empalmes del timeline…»."""
    fuente = (RAIZ / "nucleo/solidos_modificar.py").read_text(encoding="utf-8")
    assert "reordená los" not in fuente
    assert "Con más:" not in (RAIZ / "ui/manipuladores.py").read_text(encoding="utf-8")
