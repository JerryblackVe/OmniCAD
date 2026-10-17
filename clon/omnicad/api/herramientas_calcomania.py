"""Calcomanías por API: imágenes embebidas y referencias persistentes, sin Qt."""
import base64
import io
from pathlib import Path

from PIL import Image

from ..timeline.ops_insertar import OpLienzo
from .errores import error
from .registro import Expr, herramienta
from .herramientas_modificar import _refs
from .herramientas_solido import _agregar, texto_expr


@herramienta("set_decal", "documento", "Crea o edita una calcomanía sobre una cara, con tamaño, "
             "proporción, caras tangentes, opacidad, posición, giro y volteos. La imagen queda embebida. "
             "El factor de escala multiplica uniformemente anchura y altura. "
             "En cilindros usa el desarrollo por arco; en otras caras, proyección tangente.", modifica=True)
def set_decal(sesion, image: str | None = None, face: str | None = None, body: str | None = None,
              feature: str | None = None, width: Expr | None = None, height: Expr | None = None,
              keep_aspect: bool | None = None, chain_faces: bool | None = None,
              opacity: int | None = None, use_opacity: bool | None = None,
              x: Expr | None = None, y: Expr | None = None, angle: Expr | None = None,
              flip_h: bool | None = None, flip_v: bool | None = None, scale: Expr | None = None):
    """
    image: ruta de imagen PNG/JPEG/BMP/TIFF; omitida al editar conserva la embebida.
    face: selector o id de UNA cara; omitida al editar conserva su referencia.
    body: cuerpo sobre el que se evalúa el selector de face.
    feature: id o nombre del paso a editar; vacío crea uno.
    width: anchura en mm; omitida al crear ajusta la imagen dentro de la cara.
    height: altura en mm; con keep_aspect ajusta también la anchura.
    keep_aspect: conserva la proporción de la imagen; por defecto true al crear.
    chain_faces: incluye las caras tangentes encadenadas.
    opacity: porcentaje de opacidad (0 a 100).
    use_opacity: false ignora el porcentaje y usa 100 por ciento.
    x: distancia X sobre la cara, en mm.
    y: distancia Y sobre la cara, en mm.
    angle: ángulo Z en grados.
    flip_h: volteo horizontal de imagen.
    flip_v: volteo vertical de imagen.
    scale: factor uniforme positivo sobre anchura y altura; 1 conserva el tamaño (también con keep_aspect=false).
    """
    anterior = sesion.paso(feature) if feature else None
    if anterior is not None and (not isinstance(anterior, OpLienzo) or not anterior.p["calcomania"]):
        raise error("INVALID_ARGUMENTS", "El paso no es una calcomanía.")
    params = dict(anterior.p) if anterior else dict(OpLienzo.PARAMS, calcomania=True, centrada=True,
                                                   encadenar=True, opacidad=100)
    if image is not None:
        ruta = Path(image)
        if not ruta.is_file():
            raise error("FILE_NOT_FOUND", "No encuentro la imagen de la calcomanía.")
        if ruta.stat().st_size > 32 * 1024 * 1024:
            raise error("INVALID_ARGUMENTS", "La imagen supera 32 MB.")
        datos = ruta.read_bytes()
        try:
            with Image.open(io.BytesIO(datos)) as img:
                img.verify()
                proporcion = img.height / img.width
        except (OSError, ValueError, Image.DecompressionBombError):
            raise error("INVALID_ARGUMENTS", "La imagen está dañada o no es compatible.") from None
        params.update(archivo=ruta.name, imagen=base64.b64encode(datos).decode("ascii"), proporcion=proporcion)
    if not params["imagen"]:
        raise error("INVALID_ARGUMENTS", "Elegí la imagen de la calcomanía.")
    if face is not None:
        refs, _ = _refs(sesion, face, "cara", body)
        if len(refs) != 1:
            raise error("INVALID_ARGUMENTS", "Elegí una sola cara para la calcomanía.")
        params["plano"] = refs[0]
    if params["plano"] is None:
        raise error("INVALID_ARGUMENTS", "Elegí la cara de la calcomanía.")
    cambios = {"mantener_proporcion": keep_aspect, "encadenar": chain_faces, "opacidad": opacity,
               "usar_opacidad": use_opacity, "dx": x, "dy": y, "angulo": angle,
               "voltear": flip_h, "voltear_v": flip_v, "ancho": width, "alto": height, "escala": scale}
    for clave, valor in cambios.items():
        if valor is not None:
            params[clave] = texto_expr(valor) if clave in OpLienzo.EXPRESIONES else valor
    if opacity is not None and not 0 <= opacity <= 100:
        raise error("INVALID_ARGUMENTS", "La opacidad debe estar entre 0 y 100.")
    if width is None and height is None and anterior is None:
        from ..timeline import entidades
        from ..nucleo.calcomanias import superficie
        e = entidades.resolver(params["plano"], sesion.doc.estado_final)
        tam = superficie(e.forma)["tamano"]
        params["ancho"] = str(min(tam[0], tam[1] / params["proporcion"]) * 0.9)
    if height is not None and width is None and params["mantener_proporcion"]:
        params["ancho"] = f"({params['alto']}) / {params['proporcion']}"
    doc = sesion.doc
    op = OpLienzo(anterior.id if anterior else doc.nuevo_id(), anterior.nombre if anterior else "Calcomanía",
                  anterior.suprimida if anterior else False, **params)
    if anterior:
        doc.reemplazar(op.id, op)
        return {"feature": op.id}
    return _agregar(sesion, op)
