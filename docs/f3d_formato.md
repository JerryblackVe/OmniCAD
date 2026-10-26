# Archivos .f3d de Fusion: qué se lee, qué no y por qué

Cómo abre OmniCAD un `.f3d` sin Fusion (`clon/omnicad/io_archivos/f3d_*.py`) y hasta dónde llega. Medido con los
ejemplos de `~/Desktop/f3z` (BINCHA, abanicos, cartera, extrusor). Lo que falta está en
[seguimiento/faltantes.md](seguimiento/faltantes.md) (P-11h, P-11l, P-11m, FU-8).

## Qué trae el ZIP

| Miembro | Qué es | Qué hace OmniCAD |
|---|---|---|
| `Breps.BlobParts/BREP.*.smbh` | B-rep actual de un componente (SAB de ShapeManager) | cuerpos: `f3d_nativo`, `sab`, `acis_occ` |
| `Breps.BlobParts/BREP.*.smb` | perfiles de los bocetos + cuerpos auxiliares de las herramientas | bocetos: `f3d_bocetos` |
| `OGS.BlobFolder/OGS/DefaultScene/world` + `Fusion_mesh_000` | escena de dibujo: matriz de cada componente y la malla de los cuerpos VISIBLES | ubicar componentes y copias: `f3d_escena` |
| `FusionDesignSegmentType1/BulkStream.dat` (viejos: `Design1/`) | flujo de diseño propietario: nombres, historial, parámetros | nombres de componentes y tabla de operaciones: `f3d_historial` |
| `ParaMeshGeometry.BlobParts/*.paramesh` | malla de un cuerpo de malla (Elemento de malla base) | no se lee |

## Cuerpos ocultos

La escena solo trae malla de los cuerpos que se ven. Un cuerpo del B-rep con las mismas caras que un registro de cuerpo
SIN malla de la escena es un cuerpo oculto de Fusion (el ojo cerrado): entra, pero oculto en el navegador
(`__navegador__.ocultos`). BINCHA.f3d: 6 registros de cuerpo y 6 cuerpos SAB con las mismas caras (366 del sólido
visible; 18 716, 3 708, 3 516, 3 516 y 88 de las mallas OBJ convertidas con «Convertir malla»). El número de cuerpos que
muestra Fusion en su navegador NO se verificó contra Fusion.

## Rendimiento (BINCHA.f3d, 7,8 MB, 30 MB de B-rep)

Antes 300 s; ahora 23 s (mediana de tres corridas en proceso aparte: 22,5 / 22,9 / 23,3). El cuello de botella era
`ShapeFix_Shape` sobre una malla convertida abierta de 18 716 caras: 247 s, cuadrático (500 caras 0,17 s; 2 000 5,7 s; 4 000
11,6 s). `acis_occ.CARAS_SIN_ARREGLO` = 2000: un cuerpo abierto con más caras entra sin repararlo. Lo que queda de los 23 s:

| Etapa | s |
|---|---|
| Zstandard (decodificador puro en Python, 30 MB) | 8,6 |
| Conversión ACIS → OpenCascade | 3,6 |
| Lector SAB (`sab.leer`) | 3,6 |
| Ubicar componentes (escena de 11 MB) | 3,8 |
| `brep_a_texto` de los 6 cuerpos | 2,2 |

Zstandard y SAB son datos puros: candidatos a Rust (regla de rendimiento de `CLAUDE.md`); el crate `ruzstd` es una
dependencia nueva y pide permiso (P-11n).

## Bocetos

El `.smb` guarda las regiones cerradas de cada boceto como cuerpos de hoja planos. `f3d_bocetos` toma cada cuerpo hecho solo
de caras planas coplanares, deduplica las formas repetidas (las tapas de una extrusión caen en otro plano paralelo) y
pasa las aristas únicas (recta, círculo, arco, elipse, spline) a un `Boceto` sobre el plano de las caras (en mm). BINCHA:
10 bocetos —el contorno de la bincha, los de las letras, el recorte y un triángulo suelto—, que coincide con los 10 `DcSketch`
de la tabla del flujo. Límites conocidos:

- solo salen las regiones CERRADAS: los trazos abiertos, la construcción, las cotas, las restricciones y los nombres no
  están en el `.smb` (P-11m);
- con más de un componente no se importan (P-11l): el bloque `.smb` no dice de qué componente es y la caja de los cuerpos
  no alcanza (415 de 418 perfiles de CARTERA GOTICA caen en más de un componente);
- tope de 150 bocetos y 30 000 trazos por archivo.

## Historial: lo que se lee y lo que no (P-11h, FU-8)

El flujo de diseño trae una tabla de tipos (`<largo u32>DcXxxMetaType<cantidad u64>`): BINCHA tiene 44 extrusiones, 14
empalmes, 10 eliminar cuerpo, 10 bocetos, 9 chaflanes, 4 combinar, 4 planos, 2 patrones circulares, 2 simetrías… `f3d_historial` la
lee y el aviso de apertura declara que NO se traduce (CL8). Las operaciones en sí no se descifraron. Dos caminos probados:

**1. Gramática del flujo.** Los registros son `01 <id u32> 00…`, con clases de tres dígitos ASCII, textos UTF-16 con su
largo y dobles de 64 bits. Los parámetros se leen bien: el de la extrusión de BINCHA es `AlongDistance` = «5 mm» (nombre
`d14`, valor 0,5 cm en el flujo). Lo que NO se resuelve: qué perfil usa cada extrusión y qué aristas toca cada empalme. Esas
selecciones se guardan como recetas de nombre persistente (`edge_recipe_data` ×69, `face_recipe_data` ×3, `body_recipe_data`
×2, `crv_primary_id` y `crv_secondary_id` ×26) ligadas a las etiquetas `generic_tag_attrib_def` de las entidades ACIS
(en BINCHA, 1 a 5 y 11), y solo Fusion sabe resolverlas contra la historia de su modelo: el archivo guarda únicamente el estado
final del B-rep.

**2. Reconstruir por geometría con los datos del `.smb`.** Se puede en el caso más simple: el perfil de área 1 193,3 mm²
(cuerpo 25 del `.smb`) extruido 5 mm da 5 966,5 mm³, igual al sólido auxiliar del `.smb` (5 966,4) y a la malla de la escena
(5 968,3). Pero el sólido final mide 6 014,0 mm³ tras 43 extrusiones más, 14 empalmes y 9 chaflanes cuyas selecciones no
se pueden reproducir: un historial a medias que no reconstruye la forma sería peor que declararlo. Un tercer camino —pedirle
el historial a Fusion con su API pública— existe (el puente `puente_fusion`, que hoy trae solo la forma y los parámetros)
pero exige tener Fusion abierto.
