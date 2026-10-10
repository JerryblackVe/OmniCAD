# -*- coding: utf-8 -*-
"""
Espacio de trabajo RENDERIZAR (Fusion › Render): ventana propia con su cinta (CONFIGURAR, RENDERIZAR EN EL
LIENZO, RENDERIZAR, TERMINAR RENDERIZAR), el lienzo con el modelo, «Aspecto» y «Configuración de escena»
como paneles flotantes (como los diálogos de Fusion) y la Galería de renders abajo.

Punto de entrada para la ventana principal:
    ventana = VentanaRender(doc, parent)     # doc: timeline.documento.Documento
    ventana.desde_dict(datos)                # opcional: escena y cámara guardadas con `a_dict()`
    ventana.show()
    datos = ventana.a_dict()                 # {"version", "escena", "camara", "lienzo"}; `cambiado` avisa
Los aspectos se guardan EN EL DOCUMENTO (entran en deshacer y en el proyecto), con dos propiedades por
cuerpo: "apariencia" [r, g, b] (la que ya usa el visor del diseño) y "acabado" {nombre, categoria, metalico,
rugosidad, transparencia, barniz, patron, color2}.

Lienzo (`LienzoRender`, también lo usa ANIMACIÓN): un Visor3D (misma navegación con el ratón y ViewCube)
con un camino GLSL propio: sombreado por píxel (Fresnel + Blinn-Phong según la rugosidad, reflejo del
entorno, barniz, vetas 3D de madera), mapa de sombras con filtrado de Poisson, plano de suelo que recibe
sombras y reflejos, oclusión ambiental en espacio de pantalla y anti-alias (multimuestreo; con «Renderizar en
el lienzo», supermuestreo). Es el mismo modelo que `nucleo.render_cpu`, que hace la imagen cuando no hay
OpenGL o si se elige el motor de CPU. Si el GLSL no compila, el lienzo dibuja como el Visor3D.
"""
import ctypes
import logging
import math
import os
import time
import weakref
from pathlib import Path

import numpy as np
from OpenGL import GL
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressDialog,
                               QPushButton, QScrollArea, QSlider, QSpinBox, QTabWidget, QToolButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import NOMBRE_APP, VERSION
from ..nucleo import render_cpu as rc
from ..nucleo.geometria import ErrorGeometria
from ..timeline.operaciones import propiedades_cuerpo
from . import temas
from .cinta import ESPACIOS
from .iconos import icono
from .superposiciones import AreaVisor
from ..nucleo.render_cpu import color_y_acabado, malla_suave  # noqa: F401 — se re-exportan (tests, animación)
from .visor3d import ENTORNOS, ConfigVista, Visor3D, aristas_cuerpo, rayo_triangulos

log = logging.getLogger(__name__)
_F = np.float32


# =============================================================== utilidades
def cielo_de(entorno):
    """(arriba, abajo, intensidad) del entorno de visor3d.ENTORNOS (sRGB)."""
    _n, arriba, abajo, luz = ENTORNOS.get(entorno, ENTORNOS["fotomaton"])
    return tuple(arriba), tuple(abajo), float(luz)


# =============================================================== GLSL
def _glsl_vec2s(pares):
    return ", ".join(f"vec2({a:.4f}, {b:.4f})" for a, b in pares)


def _nucleo_ssao():
    rng = np.random.default_rng(7)               # el mismo núcleo que render_cpu._ssao
    dirs = rng.normal(size=(12, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    escalas = 0.25 + 0.75 * (np.arange(1, 13) / 12) ** 2
    return (", ".join(f"vec3({a:.4f}, {b:.4f}, {c:.4f})" for a, b, c in dirs),
            ", ".join(f"{e:.4f}" for e in escalas))


_SSAO_DIRS, _SSAO_ESC = _nucleo_ssao()
_COMUN = """
uniform vec3 u_arriba; uniform vec3 u_abajo; uniform float u_int; uniform float u_brillo; uniform float u_exposicion;
uniform vec3 u_luz[3]; uniform vec2 u_tiras[3];
uniform sampler2D u_sombras; uniform mat4 u_luz_mat; uniform int u_con_sombras;
uniform float u_texel; uniform float u_pcf; uniform float u_sesgo;
const vec2 DISCO[16] = vec2[16](%(disco)s);
const float TIRAS[3] = float[3](%(tiras)s);
vec3 a_lineal(vec3 c) { return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }
vec3 a_srgb(vec3 c) { c = clamp(c, 0.0, 1.0); return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
float suave(float a, float b, float x) { float t = clamp((x - a) / (b - a), 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }
vec3 radiancia(vec3 d) {
    vec3 c = mix(a_lineal(u_abajo), a_lineal(u_arriba), suave(-0.25, 0.85, d.z)) * (1.0 - 0.55 * suave(0.05, -0.35, d.z));
    float caja = 5.0 * suave(0.93, 0.975, dot(d, u_luz[0])) + 2.2 * suave(0.95, 0.985, dot(d, u_luz[1]))
               + 2.6 * suave(0.955, 0.988, dot(d, u_luz[2])) + 1.4 * suave(0.90, 0.97, d.z);
    float hxy = length(d.xy);
    if (hxy > 1e-6) {
        vec2 h = d.xy / hxy;
        float banda = suave(-0.75, -0.45, d.z) * (1.0 - suave(0.55, 0.8, d.z));
        for (int i = 0; i < 3; i++) caja += TIRAS[i] * suave(0.985, 0.997, dot(h, u_tiras[i])) * banda;
    }
    return (c + caja * 0.55 * u_int) * u_brillo;
}
vec3 irradiancia(vec3 n) {
    return (mix(a_lineal(u_abajo), a_lineal(u_arriba), 0.5 + 0.5 * n.z) + 0.18 * u_int) * u_brillo * 0.9;
}
vec3 tonos(vec3 c) {
    vec3 x = c * exp2(u_exposicion) * 0.8;
    return a_srgb((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
}
float sombra(vec3 p, vec3 n) {
    if (u_con_sombras == 0) return 1.0;
    vec4 q = u_luz_mat * vec4(p + n * u_texel * 1.5, 1.0);
    if (q.x < 0.0 || q.y < 0.0 || q.x > 1.0 || q.y > 1.0) return 1.0;
    float luz = 0.0;
    for (int i = 0; i < 16; i++) {
        float d = texture2D(u_sombras, q.xy + DISCO[i] * u_pcf).r;
        luz += (d >= 0.99999 || q.z <= d + u_sesgo) ? 1.0 : 0.0;
    }
    return luz / 16.0;
}
""" % {"disco": _glsl_vec2s(rc.DISCO_PCF), "tiras": ", ".join(f"{k:.3f}" for _a, k in rc.TIRAS)}

_VS_CUERPO = """#version 120
uniform mat4 u_vp; uniform mat4 u_modelo;
varying vec3 v_pos; varying vec3 v_nor; varying vec3 v_loc;
void main() {
    vec4 p = u_modelo * gl_Vertex;
    v_pos = p.xyz; v_nor = mat3(u_modelo) * gl_Normal; v_loc = gl_MultiTexCoord0.xyz;
    gl_Position = u_vp * p;
}
"""
_FS_CUERPO = """#version 120
%(comun)s
uniform vec3 u_ojo; uniform vec3 u_atras; uniform int u_orto;
uniform vec3 u_color; uniform vec3 u_color2; uniform float u_met; uniform float u_rug; uniform float u_transp;
uniform float u_barniz; uniform int u_madera; uniform int u_modo;
uniform sampler2D u_prof; uniform int u_con_ao; uniform mat4 u_vista; uniform mat4 u_proy; uniform float u_radio_ao;
uniform float u_lejos; uniform float u_z_suelo;
varying vec3 v_pos; varying vec3 v_nor; varying vec3 v_loc;
const vec3 NUCLEO[12] = vec3[12](%(dirs)s);
const float ESCALA[12] = float[12](%(esc)s);
const float INTENS[3] = float[3](%(intens)s);
vec3 veta(vec3 q, vec3 c1, vec3 c2) {
    float r = sqrt(q.x * q.x + q.z * q.z);
    float w = r * 0.42 + 1.3 * sin(q.y * 0.07 + q.x * 0.05) + 0.4 * sin(q.y * 0.29 + q.z * 0.11);
    float anillo = pow(0.5 + 0.5 * sin(6.2831853 * w), 3.0);
    float fibra = 0.5 + 0.5 * sin(q.y * 2.1 + sin(q.x * 0.9) * 3.0);
    return mix(c1, c2, clamp(anillo * 0.45 + fibra * 0.10, 0.0, 1.0));
}
float vista_z(vec2 uv) {
    float d = texture2D(u_prof, uv).r;
    if (d >= 1.0) return -1e9;
    float ndc = d * 2.0 - 1.0;
    if (u_orto == 1) return -ndc * u_lejos;
    return -u_proy[3][2] / (ndc + u_proy[2][2]);
}
float oclusion(vec3 p, vec3 n) {
    if (u_con_ao == 0) return 1.0;
    vec3 pv = (u_vista * vec4(p, 1.0)).xyz;
    vec3 nv = normalize(mat3(u_vista) * n);
    float giro = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) * 6.2831853;
    float c = cos(giro), s = sin(giro), occ = 0.0;
    for (int i = 0; i < 12; i++) {
        vec3 d = vec3(c * NUCLEO[i].x - s * NUCLEO[i].y, s * NUCLEO[i].x + c * NUCLEO[i].y, NUCLEO[i].z);
        if (dot(d, nv) < 0.0) d = -d;
        vec3 q = pv + d * u_radio_ao * ESCALA[i];
        vec4 k = u_proy * vec4(q, 1.0);
        vec2 uv = k.xy / k.w * 0.5 + 0.5;
        if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) continue;
        float zs = vista_z(uv);
        float rango = suave(0.0, 1.0, u_radio_ao / max(abs(zs - pv.z), 1e-6));
        if (zs > q.z + u_radio_ao * 0.02) occ += rango;
    }
    return clamp(1.0 - occ / 12.0 * 1.1, 0.25, 1.0);
}
void main() {
    if (u_modo == 3 && v_pos.z > u_z_suelo) discard;      // reflejo de lo que quedó debajo del suelo
    vec3 n = normalize(v_nor);
    vec3 v = (u_orto == 1) ? u_atras : normalize(u_ojo - v_pos);
    if (dot(n, v) < 0.0) n = -n;
    vec3 base = (u_madera == 1) ? veta(v_loc, u_color, u_color2) : u_color;
    if (u_modo == 2) { gl_FragColor = vec4(mix(vec3(1.0), a_srgb(base), u_transp), 1.0); return; }
    float sh = (u_modo == 3) ? 1.0 : sombra(v_pos, n);
    float ao = (u_modo == 0) ? oclusion(v_pos, n) : 1.0;
    float nv = clamp(dot(n, v), 1e-4, 1.0);
    vec3 f0 = mix(vec3(0.04), base, u_met);
    vec3 fr = f0 + (max(vec3(1.0 - u_rug), f0) - f0) * pow(1.0 - nv, 5.0);
    float a = max(u_rug * u_rug, 0.002);
    float sp = clamp(2.0 / (a * a) - 2.0, 1.0, 4096.0);
    vec3 dif = irradiancia(n) * ao;
    vec3 esp = vec3(0.0);
    for (int i = 0; i < 3; i++) {
        float nl = clamp(dot(n, u_luz[i]), 0.0, 1.0);
        float inten = INTENS[i] * u_int * u_brillo * nl * ((i == 0) ? sh : 1.0);
        dif += vec3(inten);
        vec3 h = normalize(v + u_luz[i]);
        esp += fr * inten * (sp + 2.0) / 25.1327412 * pow(clamp(dot(n, h), 0.0, 1.0), sp);
    }
    vec3 r = 2.0 * nv * n - v;
    vec3 nitido = radiancia(r);
    vec3 env = mix(nitido, irradiancia(r), clamp(u_rug * 1.6, 0.0, 1.0));
    float occl = 0.5 + 0.5 * ao;
    esp += fr * env * occl;
    if (u_barniz > 0.0) {
        float fc = (0.04 + 0.96 * pow(1.0 - nv, 5.0)) * u_barniz;
        esp = esp * (1.0 - fc) + fc * nitido * occl;
        dif *= 1.0 - fc;
    }
    dif *= base * (1.0 - u_met);
    if (u_modo == 4) {
        gl_FragColor = vec4(tonos(dif + esp) * (1.0 - u_transp), 1.0 - u_transp);
    } else if (u_modo == 1) {
        float frm = (fr.x + fr.y + fr.z) / 3.0;
        gl_FragColor = vec4(tonos((1.0 - u_transp) * (dif + esp) + u_transp * esp), 1.0 - u_transp * (1.0 - frm));
    } else {
        gl_FragColor = vec4(tonos(dif + esp), 1.0);
    }
}
"""
_VS_SIMPLE = """#version 120
uniform mat4 u_vp; uniform mat4 u_modelo;
varying vec3 v_pos;
void main() { vec4 p = u_modelo * gl_Vertex; v_pos = p.xyz; gl_Position = u_vp * p; }
"""
_FS_PROF = """#version 120
void main() { gl_FragColor = vec4(1.0); }
"""
_FS_SUELO = """#version 120
%(comun)s
uniform vec3 u_centro; uniform float u_rxy; uniform float u_fuerza; uniform sampler2D u_refl; uniform int u_con_refl;
uniform vec2 u_tam; uniform float u_desenfoque;
varying vec3 v_pos;
void main() {
    float fade = 1.0 - suave(u_rxy * 0.9, u_rxy * 3.2, length(v_pos.xy - u_centro.xy));
    float osc = %(oscuridad)s * (1.0 - sombra(v_pos, vec3(0.0, 0.0, 1.0))) * fade;
    vec3 refl = vec3(0.0); float f = 0.0;
    if (u_con_refl == 1) {
        vec2 uv = gl_FragCoord.xy / u_tam;
        vec4 acum = texture2D(u_refl, uv);
        for (int i = 0; i < 16; i++) acum += texture2D(u_refl, uv + DISCO[i] * u_desenfoque / u_tam);
        if (acum.a > 0.001) { refl = acum.rgb / acum.a; f = u_fuerza * fade * acum.a / 17.0; }
    }
    gl_FragColor = vec4(refl * f * (1.0 - osc), 1.0 - (1.0 - f) * (1.0 - osc));
}
"""
_VS_FONDO = """#version 120
uniform mat4 u_inv;
varying vec3 v_dir;
void main() {
    vec4 a = u_inv * vec4(gl_Vertex.xy, -1.0, 1.0); vec4 b = u_inv * vec4(gl_Vertex.xy, 1.0, 1.0);
    v_dir = b.xyz / b.w - a.xyz / a.w;
    gl_Position = vec4(gl_Vertex.xy, 0.9999, 1.0);
}
"""
_FS_FONDO = """#version 120
uniform int u_tipo; uniform vec3 u_color; uniform vec3 u_arriba; uniform vec3 u_abajo;
varying vec3 v_dir;
float suave(float a, float b, float x) { float t = clamp((x - a) / (b - a), 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }
void main() {
    vec3 d = normalize(v_dir);
    gl_FragColor = (u_tipo == 1) ? vec4(u_color, 1.0) : vec4(mix(u_abajo, u_arriba, suave(-0.35, 0.65, d.z)), 1.0);
}
"""
_VS_QUAD = """#version 120
void main() { gl_Position = vec4(gl_Vertex.xy, 0.0, 1.0); }
"""
_FS_REDUCIR = """#version 120
uniform sampler2D u_tex; uniform vec2 u_origen; uniform int u_ss;
void main() {
    vec4 acc = vec4(0.0);
    vec2 base = floor(gl_FragCoord.xy) * float(u_ss);
    for (int j = 0; j < 4; j++) for (int i = 0; i < 4; i++)
        if (i < u_ss && j < u_ss) acc += texture2D(u_tex, (base + vec2(float(i), float(j)) + 0.5) / u_origen);
    gl_FragColor = acc / float(u_ss * u_ss);
}
"""


class _Programa:
    """Programa GLSL (PyOpenGL) con caché de ubicaciones de uniformes."""

    def __init__(self, vs, fs):
        self.id = GL.glCreateProgram()
        for fuente, tipo in ((vs, GL.GL_VERTEX_SHADER), (fs, GL.GL_FRAGMENT_SHADER)):
            sh = GL.glCreateShader(tipo)
            GL.glShaderSource(sh, fuente)
            GL.glCompileShader(sh)
            if not GL.glGetShaderiv(sh, GL.GL_COMPILE_STATUS):
                raise RuntimeError(GL.glGetShaderInfoLog(sh).decode(errors="replace"))
            GL.glAttachShader(self.id, sh)
        GL.glLinkProgram(self.id)
        if not GL.glGetProgramiv(self.id, GL.GL_LINK_STATUS):
            raise RuntimeError(GL.glGetProgramInfoLog(self.id).decode(errors="replace"))
        self._locs = {}

    def usar(self):
        GL.glUseProgram(self.id)
        return self

    def _loc(self, nombre):
        if nombre not in self._locs:
            self._locs[nombre] = GL.glGetUniformLocation(self.id, nombre)
        return self._locs[nombre]

    def f(self, nombre, *valores):
        loc = self._loc(nombre)
        if loc >= 0:
            (GL.glUniform1f, GL.glUniform2f, GL.glUniform3f, GL.glUniform4f)[len(valores) - 1](loc, *map(float, valores))

    def i(self, nombre, valor):
        loc = self._loc(nombre)
        if loc >= 0:
            GL.glUniform1i(loc, int(valor))

    def m4(self, nombre, m):
        loc = self._loc(nombre)
        if loc >= 0:
            GL.glUniformMatrix4fv(loc, 1, GL.GL_FALSE, np.ascontiguousarray(np.asarray(m, _F).T))

    def v3(self, nombre, arr):
        loc = self._loc(nombre)
        if loc >= 0:
            a = np.ascontiguousarray(np.asarray(arr, _F).reshape(-1, 3))
            GL.glUniform3fv(loc, len(a), a)


class _FBO:
    """Framebuffer propio: color en textura (o renderbuffer multimuestreado) y profundidad en renderbuffer
    o en textura (para muestrearla: sombras y oclusión)."""

    def __init__(self, ancho, alto, color=True, prof_textura=False, muestras=0):
        self.ancho, self.alto, self.muestras = int(ancho), int(alto), int(muestras)
        self.id = int(GL.glGenFramebuffers(1))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.id)
        self.color = self.prof = None
        self.rbs = []
        if color:
            if self.muestras:
                rb = int(GL.glGenRenderbuffers(1))
                GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, rb)
                GL.glRenderbufferStorageMultisample(GL.GL_RENDERBUFFER, self.muestras, GL.GL_RGBA8, self.ancho, self.alto)
                GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_RENDERBUFFER, rb)
                self.rbs.append(rb)
            else:
                self.color = self._textura(GL.GL_RGBA8, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, GL.GL_LINEAR)
                GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.color, 0)
        if prof_textura:
            self.prof = self._textura(GL.GL_DEPTH_COMPONENT24, GL.GL_DEPTH_COMPONENT, GL.GL_UNSIGNED_INT, GL.GL_NEAREST)
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.prof, 0)
        else:
            rb = int(GL.glGenRenderbuffers(1))
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, rb)
            if self.muestras:
                GL.glRenderbufferStorageMultisample(GL.GL_RENDERBUFFER, self.muestras, GL.GL_DEPTH24_STENCIL8,
                                                    self.ancho, self.alto)
            else:
                GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH24_STENCIL8, self.ancho, self.alto)
            GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_STENCIL_ATTACHMENT, GL.GL_RENDERBUFFER, rb)
            self.rbs.append(rb)
        if not color:
            GL.glDrawBuffer(GL.GL_NONE)
            GL.glReadBuffer(GL.GL_NONE)
        self.completo = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)

    def _textura(self, interno, formato, tipo, filtro):
        GL.glActiveTexture(GL.GL_TEXTURE7)          # no tocar las unidades 0-3 que usa la pasada en curso
        t = int(GL.glGenTextures(1))
        GL.glBindTexture(GL.GL_TEXTURE_2D, t)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, interno, self.ancho, self.alto, 0, formato, tipo, None)
        for p, v in ((GL.GL_TEXTURE_MIN_FILTER, filtro), (GL.GL_TEXTURE_MAG_FILTER, filtro),
                     (GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE), (GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)):
            GL.glTexParameteri(GL.GL_TEXTURE_2D, p, v)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        return t

    def borrar(self):
        GL.glDeleteFramebuffers(1, [self.id])
        texturas = [t for t in (self.color, self.prof) if t]
        if texturas:
            GL.glDeleteTextures(texturas)
        if self.rbs:
            GL.glDeleteRenderbuffers(len(self.rbs), self.rbs)


# =============================================================== lienzo
class LienzoRender(Visor3D):
    """Visor3D con aspectos, entorno, sombras, suelo y oclusión (ver el docstring del módulo). Admite una
    matriz 4x4 por cuerpo (`set_transformaciones`) y opacidad por cuerpo (`opacidad`), para la animación."""
    navegacion_terminada = Signal()
    estado_render = Signal(str)

    def __init__(self, parent=None, escena=None):
        config = ConfigVista()
        config.estilo_visual = "sombreado"
        config.rejilla = False
        config.visibilidad = {k: False for k in config.visibilidad}
        config.efectos = {"cupula": True, "suelo": False, "sombra_suelo": False, "reflejo": False, "aa": True}
        super().__init__(parent, config)
        self.escena = rc.escena_normalizada(escena)
        self.alta_calidad = False           # «Renderizar en el lienzo»
        self.supermuestreo = 2              # del render en el lienzo
        self.aristas = False                # dibujar las aristas encima (como «Sombreado con aristas visibles»)
        self.deflexion = 0.04
        self.objetos = {}                   # id de cuerpo → {"v0", "n0", "seg0", "color", "acabado", …}
        self.transformaciones = {}          # id de cuerpo → matriz 4x4 (animación)
        self.z_suelo = 0.0
        self._cache_mallas = {}             # id(forma) → (forma, v, n, aristas)
        self._gl = None                     # recursos GL (programas, fbos, vbos) o None
        self.gl_error = None
        self.ultimo_motor = None
        self._t_rueda = QTimer(self, singleShot=True, interval=350)
        self._t_rueda.timeout.connect(self.navegacion_terminada.emit)
        self.set_escena(self.escena)

    # ------------------------------------------------------------ escena y modelo
    def set_escena(self, escena):
        self.escena = rc.escena_normalizada(escena)
        self.fov = rc.focal_a_fov(self.escena["focal"])
        self.config.camara = "ortografica" if self.escena["camara"] == "ortografica" else "perspectiva"
        self.config.entorno = self.escena["entorno"] if self.escena["entorno"] in ENTORNOS else "fotomaton"
        self.update()

    def cielo(self):
        return cielo_de(self.escena["entorno"])

    def _malla(self, forma):
        clave = id(forma)
        if clave not in self._cache_mallas:
            v, n = malla_suave(forma, self.deflexion)
            seg = aristas_cuerpo(forma) if self.aristas else np.zeros((0, 3), _F)
            self._cache_mallas[clave] = (forma, v, n, seg)
        return self._cache_mallas[clave]

    def cargar(self, estado, propiedades=None, ocultos=()):
        """Muestra un estado del modelo con los aspectos de `propiedades` (las de `Documento.propiedades`)."""
        propiedades = propiedades or {}
        self._estado, self._ocultos, self._excluir_bocetos = estado, frozenset(ocultos), ()
        objetos, formas, cache = {}, {}, {}
        for i, c in enumerate(estado.cuerpos.values()):
            forma, v, n, seg = self._malla(c.forma)
            cache[id(forma)] = (forma, v, n, seg)
            if c.id in ocultos or not len(v):
                continue
            color, acabado = color_y_acabado(c, propiedades_cuerpo(propiedades, c))
            objetos[c.id] = {"v0": v, "n0": n, "seg0": seg, "color": color, "acabado": acabado, "indice": i,
                             "tipo": getattr(c, "tipo", "solido"), "nombre": propiedades.get(c.id, {}).get("nombre")
                             or c.nombre}
            formas[c.id] = c.forma
        self._cache_mallas, self.objetos, self._formas = cache, objetos, formas
        self._bocetos = np.zeros((0, 3), _F)
        zs = [float(o["v0"][:, 2].min()) for o in objetos.values()]
        self.z_suelo = min(zs) if zs else 0.0
        self._aplicar()

    def set_modelo(self, estado, ocultos=frozenset(), excluir_bocetos=(), apariencias=None):
        """Compatibilidad con Visor3D: colores sueltos (sin acabado)."""
        props = {cid: {"apariencia": list(c)} for cid, c in (apariencias or {}).items()}
        self.cargar(estado, props, ocultos)

    def set_transformaciones(self, matrices):
        self.transformaciones = {k: np.asarray(m, float) for k, m in (matrices or {}).items()}
        self._aplicar()

    def _aplicar(self):
        mallas = []
        for cid, o in self.objetos.items():
            M = self.transformaciones.get(cid)
            v, n, seg = o["v0"], o["n0"], o["seg0"]
            if M is not None and not np.allclose(M, np.identity(4)):
                R, t = M[:3, :3], M[:3, 3]
                v = (v @ R.T + t).astype(_F)
                n = (n @ R.T).astype(_F)
                seg = (seg @ R.T + t).astype(_F) if len(seg) else seg
            mallas.append({"v": np.ascontiguousarray(v, _F), "n": np.ascontiguousarray(n, _F),
                           "seg": np.ascontiguousarray(seg, _F), "loc": o["v0"], "indice": o["indice"], "id": cid,
                           "color": tuple(o["color"]), "tipo": o["tipo"], "acabado": o["acabado"],
                           "caja": (v.min(0).astype(float), v.max(0).astype(float))})
        self._mallas = mallas
        self._hover_ent = None
        self.update()

    def objetos_render(self):
        """Los cuerpos visibles en el formato de `render_cpu.renderizar`."""
        return [{"v": m["v"], "n": m["n"], "local": m["loc"], "color": list(m["color"]), "acabado": m["acabado"],
                 "opacidad": float(self.opacidad.get(m["id"], 1.0))} for m in self._mallas]

    # ------------------------------------------------------------ cámara
    def camara_dict(self):
        return rc.camara(self.R, self.objetivo, self.distancia, self.fov, self.ortografica)

    def aplicar_camara(self, cam):
        if not cam:
            return
        R = np.asarray(cam["R"], float)
        u, b = R[1], R[2] / max(np.linalg.norm(R[2]), 1e-12)
        d = np.cross(u, b)
        d /= max(np.linalg.norm(d), 1e-12)
        self.R = np.array([d, np.cross(b, d), b])
        self.objetivo = np.asarray(cam["objetivo"], float)
        self.distancia = max(0.5, float(cam["distancia"]))
        self.update()

    def _matrices_tam(self, ancho, alto):
        return rc.matrices_camara(self.camara_dict(), max(ancho, 1) / max(alto, 1))

    def _matrices(self):
        return self._matrices_tam(self.width(), self.height())

    # ------------------------------------------------------------ selección de cuerpos (con transformaciones)
    def elegir_entidad(self, pos, filtros=None, a_traves=False):   # misma firma que Visor3D (solo elige cuerpos)
        filtros = set(filtros if filtros is not None else (self.filtro or ()))
        if "cuerpo" not in filtros:
            return None
        o, d = self.rayo(pos)
        mejor = (np.inf, None)
        for m in self._mallas:
            if self.opacidad.get(m["id"], 1.0) < 0.05 or not len(m["v"]):
                continue
            ts = rayo_triangulos(o, d, m["v"].reshape(-1, 3, 3).astype(float))
            i = int(np.argmin(ts))
            if ts[i] < mejor[0]:
                mejor = (float(ts[i]), m)
        if mejor[1] is None:
            return None
        t, m = mejor
        return {"tipo": "cuerpo", "ref": {"tipo": "cuerpo", "cuerpo": m["id"]}, "dibujo": [("tris", m["v"], None, 0.35)],
                "t": t, "punto": o + d * t, "cuerpo": m["id"]}

    def mouseReleaseEvent(self, e):
        navegando = self._accion in ("orbita", "encuadre", "zoom")
        super().mouseReleaseEvent(e)
        if navegando:
            self.navegacion_terminada.emit()

    def wheelEvent(self, e):
        super().wheelEvent(e)
        self._t_rueda.start()

    # ------------------------------------------------------------ OpenGL
    def initializeGL(self):
        super().initializeGL()
        try:
            disco = {"comun": _COMUN, "dirs": _SSAO_DIRS, "esc": _SSAO_ESC, "oscuridad": f"{rc.OSCURIDAD_SOMBRA:.3f}",
                     "intens": ", ".join(f"{k:.3f}" for k in rc.INTENSIDAD_LUCES)}
            self._gl = {"cuerpo": _Programa(_VS_CUERPO, _FS_CUERPO % disco),
                        "prof": _Programa(_VS_SIMPLE, _FS_PROF),
                        "suelo": _Programa(_VS_SIMPLE, _FS_SUELO % disco),
                        "fondo": _Programa(_VS_FONDO, _FS_FONDO),
                        "reducir": _Programa(_VS_QUAD, _FS_REDUCIR),
                        "fbos": {}}
            GL.glUseProgram(0)
            self.gl_error = None
        except Exception as e:  # noqa: BLE001 — sin GLSL el lienzo dibuja como el Visor3D
            self._gl = None
            self.gl_error = str(e)
            log.warning("Render en el lienzo sin GLSL: %s", e)

    def gl_disponible(self):
        return self._gl is not None and self.isValid() and self.context() is not None

    def _fbo(self, clave, ancho, alto, **kw):
        fbos = self._gl["fbos"]
        f = fbos.get(clave)
        if f is None or (f.ancho, f.alto) != (int(ancho), int(alto)) or f.muestras != kw.get("muestras", 0):
            if f is not None:
                f.borrar()
            f = fbos[clave] = _FBO(ancho, alto, **kw)
            if not f.completo:
                raise RuntimeError(f"Framebuffer incompleto ({clave} {ancho}×{alto}).")
        return f

    def _dibujar_malla(self, m, normales=True):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer_gl(m["v"]))
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, ctypes.c_void_p(0))
        if normales:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer_gl(m["n"]))
            GL.glNormalPointer(GL.GL_FLOAT, 0, ctypes.c_void_p(0))
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer_gl(m["loc"]))
            GL.glTexCoordPointer(3, GL.GL_FLOAT, 0, ctypes.c_void_p(0))
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(m["v"]))

    def _clasificar(self):
        opacos, transp = [], []
        for m in self._mallas:
            op = float(self.opacidad.get(m["id"], 1.0))
            if op <= 0.01 or not len(m["v"]):
                continue
            (opacos if op >= 0.999 and m["acabado"]["transparencia"] < 0.02 else transp).append(m)
        return opacos, transp

    def _luz(self, mallas):
        """Matrices de la luz principal (clip y [0,1]³) ajustadas a la esfera de los cuerpos."""
        mn, mx = self._caja_mallas(mallas)
        c = (mn + mx) / 2
        r = max(float(np.linalg.norm(mx - mn)) / 2, 1e-6) * 1.02
        atras = rc.luces(self.escena["rotacion"])[0]
        arriba = (0.0, 0.0, 1.0) if abs(atras[2]) < 0.95 else (0.0, 1.0, 0.0)
        der = np.cross(arriba, atras)
        der /= np.linalg.norm(der)
        arr = np.cross(atras, der)
        m = np.identity(4)              # profundidad: de r (hacia la luz) a -3r (el suelo) → [-1, 1]
        m[0, :3], m[1, :3], m[2, :3] = der / r, arr / r, -atras / (2 * r)
        m[0, 3], m[1, 3], m[2, 3] = -der @ c / r, -arr @ c / r, (atras @ c) / (2 * r) - 0.5
        sesgo = np.identity(4) * 0.5
        sesgo[3, 3] = 1.0
        sesgo[:3, 3] = 0.5
        return m, sesgo @ m, r

    def _uniformes_comunes(self, p, luz01, r_luz, res_sombras, con_sombras):
        arriba, abajo, inten = self.cielo()
        e = self.escena
        p.f("u_arriba", *arriba)
        p.f("u_abajo", *abajo)
        p.f("u_int", inten)
        p.f("u_brillo", e["brillo"])
        p.f("u_exposicion", e["exposicion"])
        p.v3("u_luz", rc.luces(e["rotacion"]))
        loc = p._loc("u_tiras")
        if loc >= 0:
            tiras = [(math.cos(math.radians(a + e["rotacion"])), math.sin(math.radians(a + e["rotacion"])))
                     for a, _k in rc.TIRAS]
            GL.glUniform2fv(loc, 3, np.asarray(tiras, _F))
        p.i("u_sombras", 0)
        p.i("u_con_sombras", 1 if con_sombras else 0)
        if con_sombras:
            texel = 2 * r_luz / res_sombras
            p.m4("u_luz_mat", luz01)
            p.f("u_texel", texel)
            p.f("u_pcf", rc.SOMBRA_BLANDO / 2)
            p.f("u_sesgo", 1.5 * texel / (4 * r_luz) * 3.0)

    def _pintar(self, destino, ancho, alto, lienzo=True, ss=1, transparente=False, res_sombras=2048):
        """Dibuja la escena con el camino GLSL en el framebuffer `destino` (ancho × alto)."""
        g, e = self._gl, self.escena
        GL.glUseProgram(0)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glDisable(GL.GL_STENCIL_TEST)
        opacos, transp = self._clasificar()
        todos = opacos + transp
        W, H = ancho * ss, alto * ss
        proy, vista = self._matrices_tam(ancho, alto)
        vp = proy @ vista
        identidad = np.identity(4)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glClientActiveTexture(GL.GL_TEXTURE0)

        # 1) mapa de sombras de la luz principal
        casters = [m for m in todos if m["acabado"]["transparencia"] < 0.6]
        con_sombras = bool(e["sombras"] and casters)
        luz01, r_luz = identidad, 1.0
        if con_sombras:
            luz_clip, luz01, r_luz = self._luz(casters)
            f = self._fbo("sombras", res_sombras, res_sombras, color=False, prof_textura=True)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, f.id)
            GL.glViewport(0, 0, res_sombras, res_sombras)
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            p = g["prof"].usar()
            p.m4("u_vp", luz_clip)
            p.m4("u_modelo", identidad)
            for m in casters:
                self._dibujar_malla(m, normales=False)
        # 2) profundidad de la cámara (oclusión ambiental)
        con_ao = bool(e["oclusion"] and opacos and (self.alta_calidad or not lienzo))
        if con_ao:
            f = self._fbo("prof", W, H, color=False, prof_textura=True)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, f.id)
            GL.glViewport(0, 0, W, H)
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            p = g["prof"].usar()
            p.m4("u_vp", vp)
            p.m4("u_modelo", identidad)
            for m in opacos:
                self._dibujar_malla(m, normales=False)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, g["fbos"]["sombras"].prof if con_sombras else 0)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, g["fbos"]["prof"].prof if con_ao else 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        ojo = self.ojo()

        def _cuerpo(modo, modelo=identidad, ao=False):
            p = g["cuerpo"].usar()
            self._uniformes_comunes(p, luz01, r_luz, res_sombras, con_sombras and modo != 3)
            p.m4("u_vp", vp)
            p.m4("u_modelo", modelo)
            p.f("u_ojo", *ojo)
            p.f("u_atras", *self.R[2])
            p.i("u_orto", 1 if self.ortografica else 0)
            p.i("u_modo", modo)
            p.i("u_prof", 1)
            p.i("u_con_ao", 1 if ao else 0)
            p.m4("u_vista", vista)
            p.m4("u_proy", proy)
            p.f("u_radio_ao", self._radio_escena(todos) * 0.07)
            p.f("u_lejos", self.distancia * 20 + 1000)
            p.f("u_z_suelo", self.z_suelo + 1e-4 * self._radio_escena(todos))
            return p

        def _material(p, m):
            a = m["acabado"]
            p.f("u_color", *rc.srgb_a_lineal(m["color"]))
            c2 = rc.srgb_a_lineal(a["color2"]) if a.get("color2") else rc.srgb_a_lineal(m["color"]) * 0.6
            p.f("u_color2", *c2)
            p.f("u_met", a["metalico"])
            p.f("u_rug", a["rugosidad"])
            p.f("u_transp", max(a["transparencia"], 1.0 - float(self.opacidad.get(m["id"], 1.0))))
            p.f("u_barniz", a["barniz"])
            p.i("u_madera", 1 if a["patron"] == "madera" else 0)

        # 3) reflejos en el suelo: los cuerpos espejados en una textura
        con_refl = bool(e["suelo"] and e["reflejos"] and opacos)
        if con_refl:
            f = self._fbo("refl", ancho, alto)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, f.id)
            GL.glViewport(0, 0, ancho, alto)
            GL.glClearColor(0, 0, 0, 0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_BLEND)
            espejo = np.identity(4)
            espejo[2, 2], espejo[2, 3] = -1.0, 2 * self.z_suelo
            p = _cuerpo(3, espejo)
            for m in opacos:
                _material(p, m)
                self._dibujar_malla(m)

        # 4) la escena (multimuestreo en el lienzo; supermuestreo con «Renderizar en el lienzo» o en el render)
        muestras = 4 if ss == 1 else 0
        escena = self._fbo("escena", W, H, muestras=muestras)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, escena.id)
        GL.glViewport(0, 0, W, H)
        GL.glClearColor(0, 0, 0, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_BLEND)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        quad = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], _F)
        if not transparente:
            p = g["fondo"].usar()
            p.m4("u_inv", np.linalg.inv(vp))
            p.i("u_tipo", 1 if e["fondo"] == "color" else 0)
            p.f("u_color", *e["color_fondo"])
            arriba, abajo, _l = self.cielo()
            p.f("u_arriba", *arriba)
            p.f("u_abajo", *abajo)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, quad)
            GL.glDrawArrays(GL.GL_QUADS, 0, 4)
        if e["suelo"] and todos:
            mn, mx = self._caja_mallas(todos)
            c = (mn + mx) / 2
            rxy = max(float(np.linalg.norm(mx[:2] - mn[:2])) / 2, self._radio_escena(todos) * 0.3)
            ext = rxy * 4.0
            z = self.z_suelo
            suelo = np.array([[c[0] - ext, c[1] - ext, z], [c[0] + ext, c[1] - ext, z], [c[0] + ext, c[1] + ext, z],
                              [c[0] - ext, c[1] + ext, z]], _F)
            p = g["suelo"].usar()
            self._uniformes_comunes(p, luz01, r_luz, res_sombras, con_sombras)
            p.m4("u_vp", vp)
            p.m4("u_modelo", identidad)
            p.f("u_centro", *c)
            p.f("u_rxy", rxy)
            p.f("u_fuerza", 0.42 * (1 - e["rugosidad_suelo"]) ** 1.5)
            p.i("u_refl", 2)
            p.i("u_con_refl", 1 if con_refl else 0)
            p.f("u_tam", W, H)
            p.f("u_desenfoque", e["rugosidad_suelo"] * 0.012 * max(W, H))
            if con_refl:
                GL.glActiveTexture(GL.GL_TEXTURE2)
                GL.glBindTexture(GL.GL_TEXTURE_2D, g["fbos"]["refl"].color)
                GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, suelo)
            GL.glDrawArrays(GL.GL_QUADS, 0, 4)
            GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        if self.aristas:
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(1.0, 1.0)
        p = _cuerpo(0, ao=con_ao)
        for m in opacos:
            _material(p, m)
            self._dibujar_malla(m)
        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glUseProgram(0)
        if self.aristas:
            GL.glColor4f(0.10, 0.11, 0.13, 1.0)
            GL.glLineWidth(1.2 * ss)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadMatrixf(proy.T.astype(_F))
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadMatrixf(vista.T.astype(_F))
            for m in opacos:
                if len(m["seg"]):
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
                    GL.glVertexPointer(3, GL.GL_FLOAT, 0, m["seg"])
                    GL.glDrawArrays(GL.GL_LINES, 0, len(m["seg"]))
        if transp:
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glDepthMask(GL.GL_FALSE)
            GL.glEnable(GL.GL_BLEND)
            orden = sorted(transp, key=lambda m: -float(np.linalg.norm(m["v"].mean(0) - ojo)))
            p = _cuerpo(1)
            for m in orden:
                _material(p, m)
                if m["acabado"]["transparencia"] < 0.02:  # cuerpo opaco que se desvanece (animación)
                    p.i("u_modo", 4)
                    GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
                    self._dibujar_malla(m)
                    continue
                p.i("u_modo", 2)                         # tinte: multiplica lo de atrás
                GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_FALSE)
                GL.glBlendFunc(GL.GL_ZERO, GL.GL_SRC_COLOR)
                self._dibujar_malla(m)
                p.i("u_modo", 1)                         # reflejo + transmisión (premultiplicado)
                GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
                GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
                self._dibujar_malla(m)
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisable(GL.GL_BLEND)
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # 5) al destino: resolver el multimuestreo o reducir el supermuestreo
        if muestras:
            res = self._fbo("resuelto", W, H)
            GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, escena.id)
            GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, res.id)
            GL.glBlitFramebuffer(0, 0, W, H, 0, 0, W, H, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
            fuente = res
        else:
            fuente = escena
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, destino)
        GL.glViewport(0, 0, ancho, alto)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_BLEND)
        p = g["reducir"].usar()
        GL.glActiveTexture(GL.GL_TEXTURE3)
        GL.glBindTexture(GL.GL_TEXTURE_2D, fuente.color)
        p.i("u_tex", 3)
        p.f("u_origen", W, H)
        p.i("u_ss", ss)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, quad)
        GL.glDrawArrays(GL.GL_QUADS, 0, 4)
        for unidad in (3, 2, 1, 0):
            GL.glActiveTexture(GL.GL_TEXTURE0 + unidad)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glUseProgram(0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        self._barrer_buffers()          # búferes de la placa: los comparte con Visor3D
        return proy, vista

    @staticmethod
    def _caja_mallas(mallas):
        return (np.min([m["caja"][0] for m in mallas], axis=0), np.max([m["caja"][1] for m in mallas], axis=0))

    def _radio_escena(self, mallas):
        if not mallas:
            return 1.0
        mn, mx = self._caja_mallas(mallas)
        return max(float(np.linalg.norm(mx - mn)) / 2, 1.0)

    def paintGL(self):
        if not self.gl_disponible():
            super().paintGL()
            return
        dpr = self.devicePixelRatioF()
        ancho, alto = max(1, int(round(self.width() * dpr))), max(1, int(round(self.height() * dpr)))
        try:
            ss = max(1, int(self.supermuestreo)) if self.alta_calidad else 1
            proy, vista = self._pintar(self.defaultFramebufferObject(), ancho, alto, True, ss)
        except Exception as e:  # noqa: BLE001 — si algo del camino GLSL falla, el lienzo sigue andando
            log.exception("Lienzo de render: %s", e)
            self.gl_error = str(e)
            self._gl = None
            GL.glUseProgram(0)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())
            GL.glViewport(0, 0, ancho, alto)
            super().paintGL()
            self.estado_render.emit(f"El render en el lienzo no está disponible ({e}); se usa la vista estándar.")
            return
        # superposiciones (selección y cursor) con la tubería fija, tapadas por los cuerpos opacos
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixf(proy.T.astype(_F))
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixf(vista.T.astype(_F))
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        if self._capas or self._hover_ent is not None:
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)
            for m in self._clasificar()[0]:
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, m["v"])
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(m["v"]))
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA, GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
        for nombre, prims in self._capas.items():
            self._dibujar_primitivas(prims, (0.15, 0.50, 1.0) if nombre == "seleccion" else (0.95, 0.66, 0.30))
        if self._hover_ent is not None:
            self._dibujar_primitivas(self._hover_ent["dibujo"], (0.45, 0.70, 1.0))
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        self.camara_cambiada.emit()

    # ------------------------------------------------------------ imagen final
    def renderizar_imagen(self, ancho, alto, supermuestreo=2, motor="gl", fondo_transparente=False, progreso=None):
        """Imagen RGBA uint8 (alto, ancho, 4) de la vista actual a la resolución pedida. motor "gl" usa el camino
        GLSL en un framebuffer propio (si no hay OpenGL cae al de CPU); "cpu" usa `render_cpu.renderizar`."""
        ancho, alto, ss = int(ancho), int(alto), max(1, int(supermuestreo))
        if ancho < 1 or alto < 1:
            raise ErrorGeometria("La imagen tiene que medir al menos 1 × 1 píxel.")
        if motor == "gl" and self.gl_disponible():
            try:
                img = self._renderizar_gl(ancho, alto, ss, fondo_transparente)
                self.ultimo_motor = "OpenGL"
                return img
            except Exception as e:  # noqa: BLE001
                log.warning("Render OpenGL falló (%s); se usa el de CPU.", e)
        self.ultimo_motor = "CPU"
        res = int(min(2048, max(512, 2 ** math.ceil(math.log2(max(ancho, alto) * ss * 1.5)))))
        return rc.renderizar(self.objetos_render(), self.camara_dict(), self.escena, ancho, alto, ss, cielo=self.cielo(),
                             fondo_transparente=fondo_transparente, z_suelo=self.z_suelo, progreso=progreso,
                             res_sombras=res)

    def _renderizar_gl(self, ancho, alto, ss, transparente):
        self.makeCurrent()
        try:
            maximo = int(GL.glGetIntegerv(GL.GL_MAX_RENDERBUFFER_SIZE))
            while ss > 1 and max(ancho, alto) * ss > maximo:
                ss -= 1
            if max(ancho, alto) > maximo:
                raise ErrorGeometria(f"La imagen supera el máximo de la placa gráfica ({maximo} px).")
            final = self._fbo("final", ancho, alto)
            res = 4096 if ss >= 3 else 2048
            self._pintar(final.id, ancho, alto, lienzo=False, ss=ss, transparente=transparente, res_sombras=res)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, final.id)
            GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
            datos = GL.glReadPixels(0, 0, ancho, alto, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
            img = np.frombuffer(datos, np.uint8).reshape(alto, ancho, 4)[::-1].copy()
            for clave in ("final", "escena", "prof", "refl", "resuelto"):
                f = self._gl["fbos"].pop(clave, None)
                if f is not None:
                    f.borrar()
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())
        finally:
            self.doneCurrent()
        self.update()
        if transparente:
            a = img[..., 3:].astype(np.float64) / 255.0
            rgb = np.where(a > 0, img[..., :3] / np.maximum(a, 1e-6), 0)
            img[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
        else:
            img[..., 3] = 255
        return img


# =============================================================== íconos propios
def _icono_pintado(funcion, tam=32):
    ico = QIcon()
    for escala in (1, 2):
        pm = QPixmap(tam * escala, tam * escala)
        pm.setDevicePixelRatio(escala)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(tam / 32, tam / 32)
        funcion(p)
        p.end()
        ico.addPixmap(pm)
    return ico


def _esfera(p, cx, cy, r, base, brillo=True):
    g = QRadialGradient(cx - r * 0.35, cy - r * 0.4, r * 1.4)
    g.setColorAt(0, QColor(base).lighter(170))
    g.setColorAt(0.5, QColor(base))
    g.setColorAt(1, QColor(base).darker(220))
    p.setPen(QPen(QColor(base).darker(260), 1))
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(cx, cy), r, r)
    if brillo:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 210))
        p.drawEllipse(QPointF(cx - r * 0.38, cy - r * 0.42), r * 0.18, r * 0.13)


def _d_escena(p):
    p.setPen(QPen(QColor("#e0a020"), 2))
    p.setBrush(QColor("#f6c343"))
    p.drawEllipse(QPointF(22, 9), 5, 5)
    for k in range(8):
        a = k * math.pi / 4
        p.drawLine(QPointF(22 + 7 * math.cos(a), 9 + 7 * math.sin(a)), QPointF(22 + 9 * math.cos(a), 9 + 9 * math.sin(a)))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 60))
    p.drawEllipse(QPointF(13, 27), 10, 2.5)
    _esfera(p, 12, 19, 7, "#4a9be0")


def _d_lienzo(p):
    p.setPen(QPen(QColor("#6b6b6b"), 1.5))
    p.setBrush(QColor("#f4f4f4"))
    p.drawRoundedRect(QRectF(3, 5, 26, 20), 2, 2)
    _esfera(p, 16, 15, 7, "#d64545")
    p.setPen(QPen(QColor("#2fa84f"), 2))
    p.drawLine(QPointF(10, 28), QPointF(22, 28))


def _d_galeria(p):
    for k, color in enumerate(("#bcd7ef", "#7fb3e2", "#4a9be0")):
        p.setPen(QPen(QColor("#3c6f9f"), 1))
        p.setBrush(QColor(color))
        p.drawRect(QRectF(4 + k * 4, 6 + k * 4, 18, 14))
    p.setPen(QPen(QColor("#ffffff"), 1.5))
    p.drawLine(QPointF(15, 27), QPointF(19, 21))
    p.drawLine(QPointF(19, 21), QPointF(23, 25))


def _d_camara(p):
    p.setPen(QPen(QColor("#4d4d4d"), 1.5))
    p.setBrush(QColor("#9a9a9a"))
    p.drawRoundedRect(QRectF(3, 10, 19, 14), 2, 2)
    p.drawPolygon([QPointF(22, 14), QPointF(29, 10), QPointF(29, 24), QPointF(22, 20)])
    p.setBrush(QColor("#d64545"))
    p.drawEllipse(QPointF(8, 7), 2.5, 2.5)


def _d_explosion(p, todos=False):
    for x, y, c in ((6, 6, "#9fcff5"), (18, 6, "#4a9be0"), (6, 18, "#4a9be0"), (18, 18, "#2b78c2")):
        p.setPen(QPen(QColor("#1d5a94"), 1))
        p.setBrush(QColor(c))
        p.drawRect(QRectF(x, y, 8, 8))
    p.setPen(QPen(QColor("#ef9a2a"), 1.6))
    for a, b in (((15, 15), (10, 10)), ((17, 15), (22, 10)), ((15, 17), (10, 22)), ((17, 17), (22, 22))):
        p.drawLine(QPointF(*a), QPointF(*b))
    if todos:
        p.setBrush(QColor("#ef9a2a"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(27, 27), 4, 4)


def _d_anotacion(p):
    p.setPen(QPen(QColor("#2b78c2"), 1.5))
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(10, 4, 19, 12), 2, 2)
    p.drawLine(QPointF(12, 16), QPointF(6, 26))
    p.setBrush(QColor("#d64545"))
    p.drawEllipse(QPointF(6, 26), 2.5, 2.5)
    p.drawLine(QPointF(13, 8), QPointF(26, 8))
    p.drawLine(QPointF(13, 12), QPointF(22, 12))


def _d_guion(p):
    p.setPen(QPen(QColor("#4d4d4d"), 1.5))
    p.setBrush(QColor("#9fcff5"))
    p.drawRect(QRectF(3, 7, 22, 16))
    p.setBrush(QColor("#4d4d4d"))
    for x in (5, 10, 15, 20):
        p.drawRect(QRectF(x, 8.5, 2.5, 2))
        p.drawRect(QRectF(x, 19.5, 2.5, 2))
    p.setPen(QPen(QColor("#2fa84f"), 2.5))
    p.drawLine(QPointF(26, 21), QPointF(26, 29))
    p.drawLine(QPointF(22, 25), QPointF(30, 25))


def _d_video(p):
    p.setPen(QPen(QColor("#4d4d4d"), 1.5))
    p.setBrush(QColor("#e6e6e6"))
    p.drawRect(QRectF(3, 6, 20, 20))
    p.setBrush(QColor("#2fa84f"))
    p.setPen(Qt.NoPen)
    p.drawPolygon([QPointF(9, 11), QPointF(18, 16), QPointF(9, 21)])
    p.setPen(QPen(QColor("#2b78c2"), 2.2))
    p.drawLine(QPointF(25, 10), QPointF(25, 24))
    p.drawLine(QPointF(25, 10), QPointF(21.5, 13.5))
    p.drawLine(QPointF(25, 10), QPointF(28.5, 13.5))


def _d_invertir(p):
    p.setPen(QPen(QColor("#2b78c2"), 2))
    p.drawLine(QPointF(5, 11), QPointF(27, 11))
    p.drawLine(QPointF(27, 11), QPointF(23, 7))
    p.drawLine(QPointF(5, 21), QPointF(27, 21))
    p.drawLine(QPointF(5, 21), QPointF(9, 25))


def _d_pausa(p):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#4d4d4d"))
    p.drawRect(QRectF(9, 7, 5, 18))
    p.drawRect(QRectF(18, 7, 5, 18))


_DIBUJOS = {"pausa": _d_pausa, "escena": _d_escena, "lienzo": _d_lienzo, "galeria": _d_galeria, "camara": _d_camara,
            "explosion": _d_explosion, "explosion_todos": lambda p: _d_explosion(p, True), "anotacion": _d_anotacion,
            "guion": _d_guion, "video": _d_video, "invertir": _d_invertir}
_ICONOS = {}


def icono_render(nombre):
    """Ícono de los espacios RENDERIZAR/ANIMACIÓN: los propios de acá o, si no, los de `iconos.py`."""
    if nombre not in _ICONOS:
        _ICONOS[nombre] = _icono_pintado(_DIBUJOS[nombre]) if nombre in _DIBUJOS else icono(nombre)
    return _ICONOS[nombre]


def icono_aspecto(nombre, tam=30):
    """Muestra (esfera) de un aspecto de la biblioteca."""
    color, ac = rc.aspecto(nombre)
    base = QColor.fromRgbF(*color)
    pm = QPixmap(tam * 2, tam * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r = tam / 2 - 1.5
    c = QPointF(tam / 2, tam / 2)
    if ac["transparencia"] > 0.5:
        for i in range(4):
            for j in range(4):
                p.fillRect(QRectF(i * tam / 4, j * tam / 4, tam / 4, tam / 4), QColor("#cfcfcf" if (i + j) % 2 else "#ffffff"))
    g = QRadialGradient(c.x() - r * 0.35, c.y() - r * 0.4, r * 1.5)
    if ac["metalico"] > 0.5:
        paradas = ((0, QColor("#ffffff")), (0.35, base.lighter(115)), (0.7, base.darker(170)), (1, base.lighter(130)))
    else:
        paradas = ((0, base.lighter(150)), (0.6, base), (1, base.darker(200)))
    for pos, col in paradas:
        if ac["transparencia"] > 0.5:
            col.setAlphaF(0.45)
        g.setColorAt(pos, col)
    path = QPainterPath()
    path.addEllipse(c, r, r)
    p.setPen(QPen(base.darker(250), 0.8))
    p.setBrush(QBrush(g))
    p.drawPath(path)
    if ac["patron"] == "madera":
        p.setClipPath(path)
        oscuro = QColor.fromRgbF(*ac["color2"])
        p.setPen(QPen(oscuro, 1.2))
        for k in range(-3, 4):
            p.drawArc(QRectF(c.x() - 18 + k * 4, c.y() - 30, 36, 60), 60 * 16, 60 * 16)
        p.setClipping(False)
    if ac["rugosidad"] < 0.4 or ac["barniz"] > 0:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawEllipse(QPointF(c.x() - r * 0.38, c.y() - r * 0.42), r * 0.2, r * 0.14)
    p.end()
    return QIcon(pm)


def icono_entorno(clave, tam=40):
    _n, arriba, abajo, _l = ENTORNOS[clave]
    pm = QPixmap(tam * 2, tam * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, 0, tam)
    g.setColorAt(0, QColor.fromRgbF(*arriba))
    g.setColorAt(1, QColor.fromRgbF(*abajo))
    p.setPen(QPen(QColor("#9a9a9a"), 1))
    p.setBrush(QBrush(g))
    p.drawRoundedRect(QRectF(1, 1, tam - 2, tam - 2), 3, 3)
    _esfera(p, tam / 2, tam * 0.55, tam * 0.22, "#b8bcc2")
    p.end()
    return QIcon(pm)


# =============================================================== cinta de un espacio de trabajo
SEP = "-"


class CintaEspacio(QWidget):
    """Cinta de un espacio de trabajo (como la de DIBUJO): selector «ESPACIO ▾», una pestaña y grupos con botones
    grandes y un título desplegable. Un ítem ("texto",) es un comando no implementado (grisado)."""
    ir_a_diseno = Signal()

    def __init__(self, espacio, pestana, grupos, acciones, parent=None):
        super().__init__(parent)
        self.setObjectName("cinta")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.acciones = acciones
        self.no_disponibles = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 0)
        lay.setSpacing(10)
        self.espacio = QToolButton(objectName="espacio_trabajo", text=f"{espacio}  ▾")
        self.espacio.setFixedSize(max(108, 36 + 10 * len(espacio)), 62)
        self.espacio.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.espacio)
        for nombre in ESPACIOS:
            a = menu.addAction(nombre)
            if nombre == espacio:
                a.setCheckable(True)
                a.setChecked(True)
            elif nombre == "DISEÑO":
                a.triggered.connect(self.ir_a_diseno.emit)
            else:
                a.setEnabled(False)
        self.espacio.setMenu(menu)
        lay.addWidget(self.espacio, 0, Qt.AlignVCenter)
        derecha = QVBoxLayout()
        derecha.setSpacing(0)
        fila = QHBoxLayout()
        boton = QToolButton(objectName="pestana", text=pestana, checkable=True)
        boton.setChecked(True)
        fila.addWidget(boton)
        fila.addStretch(1)
        derecha.addLayout(fila)
        filas = QHBoxLayout()
        filas.setContentsMargins(0, 0, 0, 0)
        filas.setSpacing(4)
        for n, (titulo, rapidos, items) in enumerate(grupos):
            if n:
                sep = QFrame(objectName="separador_grupo")
                sep.setFixedWidth(1)
                filas.addWidget(sep)
            filas.addWidget(self._grupo(titulo, rapidos, items))
        filas.addStretch(1)
        derecha.addLayout(filas)
        lay.addLayout(derecha, 1)

    def _accion(self, ref):
        if isinstance(ref, str):
            return self.acciones[ref]
        a = QAction(ref[0], self)
        a.setEnabled(False)
        a.setToolTip(f"<b>{ref[0]}</b><br>No disponible en {NOMBRE_APP} {VERSION}.")
        self.no_disponibles.append(a)
        return a

    def _grupo(self, titulo, rapidos, items):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(2, 2, 2, 0)
        v.setSpacing(0)
        botones = QHBoxLayout()
        botones.setSpacing(2)
        for clave in rapidos:
            b = QToolButton()
            b.setDefaultAction(self._accion(clave))
            b.setIconSize(QSize(30, 30))
            b.setFixedSize(38, 38)
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            botones.addWidget(b)
        v.addLayout(botones)
        t = QToolButton(objectName="titulo_grupo", text=f"{titulo} ▾")
        t.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(t)
        m.setToolTipsVisible(True)
        for it in items:
            if it == SEP:
                m.addSeparator()
            else:
                m.addAction(self._accion(it))
        t.setMenu(m)
        v.addWidget(t, 0, Qt.AlignHCenter)
        return w


class PanelFlotante(QFrame):
    """Diálogo flotante sobre el lienzo (a la derecha, debajo del ViewCube), como los de Fusion."""
    cerrado = Signal()

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_flotante")
        self.setFixedWidth(330)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 6)
        v.setSpacing(4)
        barra = QFrame(objectName="titulo_panel")
        h = QHBoxLayout(barra)
        h.setContentsMargins(8, 3, 4, 3)
        h.addWidget(QLabel(titulo.upper()))
        h.addStretch(1)
        cerrar = QToolButton(text="✕")
        cerrar.setToolTip("Cerrar")
        cerrar.clicked.connect(self.cerrar)
        h.addWidget(cerrar)
        v.addWidget(barra)
        self.cuerpo = QVBoxLayout()
        self.cuerpo.setContentsMargins(8, 2, 8, 2)
        self.cuerpo.setSpacing(6)
        v.addLayout(self.cuerpo, 1)

    def cerrar(self):
        self.hide()
        self.cerrado.emit()


def _seccion(texto):
    lb = QLabel(texto)
    temas.poner_rol(lb, "seccion")
    return lb


class _Deslizador(QWidget):
    """Deslizador + casilla numérica enlazados (valor real)."""
    cambiado = Signal(float)

    def __init__(self, minimo, maximo, decimales=2, sufijo="", parent=None):
        super().__init__(parent)
        self.k = 10 ** decimales
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(minimo * self.k), int(maximo * self.k))
        self.caja = QDoubleSpinBox()
        self.caja.setRange(minimo, maximo)
        self.caja.setDecimals(decimales)
        self.caja.setSingleStep({0: 1.0, 1: 0.1}.get(decimales, 0.05))
        self.caja.setSuffix(sufijo)
        self.caja.setFixedWidth(100)
        h.addWidget(self.slider, 1)
        h.addWidget(self.caja)
        self.slider.valueChanged.connect(lambda v: self._fijar(v / self.k, desde_slider=True))
        self.caja.valueChanged.connect(lambda v: self._fijar(v))
        self._bloqueo = False

    def _fijar(self, valor, desde_slider=False):
        if self._bloqueo:
            return
        self._bloqueo = True
        if desde_slider:
            self.caja.setValue(valor)
        else:
            self.slider.setValue(int(round(valor * self.k)))
        self._bloqueo = False
        self.cambiado.emit(float(valor))

    def valor(self):
        return float(self.caja.value())

    def set_valor(self, valor):
        self._bloqueo = True
        self.caja.setValue(float(valor))
        self.slider.setValue(int(round(float(valor) * self.k)))
        self._bloqueo = False


class PanelEscena(PanelFlotante):
    """CONFIGURAR › Configuración de escena [GUID-5646B2CB]: pestañas Configuración y Biblioteca de entornos."""
    escena_cambiada = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("Configuración de escena", parent)
        self._escena = rc.escena_normalizada()
        self._cargando = False
        pestanas = QTabWidget()
        self.cuerpo.addWidget(pestanas)
        conf = QWidget()
        f = QFormLayout(conf)
        f.setContentsMargins(4, 4, 4, 4)
        f.setLabelAlignment(Qt.AlignLeft)
        self.lb_entorno = QLabel()
        f.addRow(_seccion("Entorno"))
        f.addRow("Estilo actual", self.lb_entorno)
        self.brillo = _Deslizador(0.0, 4.0, 2, " ×")
        self.rotacion = _Deslizador(-180.0, 180.0, 0, "°")
        f.addRow("Brillo", self.brillo)
        f.addRow("Posición (giro)", self.rotacion)
        f.addRow(_seccion("Fondo"))
        self.fondo = QComboBox()
        self.fondo.addItem("Entorno", "entorno")
        self.fondo.addItem("Color sólido", "color")
        self.boton_color = QPushButton()
        self.boton_color.setFixedWidth(60)
        self.boton_color.clicked.connect(self._elegir_color)
        fila = QHBoxLayout()
        fila.addWidget(self.fondo, 1)
        fila.addWidget(self.boton_color)
        f.addRow("Fondo", fila)
        f.addRow(_seccion("Efectos de suelo"))
        self.suelo = QCheckBox("Plano de suelo")
        self.reflejos = QCheckBox("Reflejos")
        self.sombras = QCheckBox("Sombras")
        self.rugosidad = _Deslizador(0.0, 1.0, 2)
        f.addRow(self.suelo)
        f.addRow(self.reflejos)
        f.addRow("Rugosidad", self.rugosidad)
        f.addRow(self.sombras)
        f.addRow(_seccion("Cámara"))
        self.camara = QComboBox()
        self.camara.addItem("Perspectiva", "perspectiva")
        self.camara.addItem("Ortográfica", "ortografica")
        self.focal = _Deslizador(8.0, 300.0, 0, " mm")
        self.exposicion = _Deslizador(-6.0, 6.0, 1, " EV")
        f.addRow("Cámara", self.camara)
        f.addRow("Distancia focal", self.focal)
        f.addRow("Exposición", self.exposicion)
        f.addRow(_seccion("Efectos"))
        self.oclusion = QCheckBox("Oclusión ambiental")
        f.addRow(self.oclusion)
        pestanas.addTab(conf, "Configuración")
        bib = QWidget()
        vb = QVBoxLayout(bib)
        vb.setContentsMargins(4, 4, 4, 4)
        vb.addWidget(QLabel("Doble clic en un entorno para usarlo:"))
        self.lista_entornos = QListWidget()
        self.lista_entornos.setIconSize(QSize(40, 40))
        for clave, (nombre, *_r) in ENTORNOS.items():
            it = QListWidgetItem(icono_entorno(clave), nombre)
            it.setData(Qt.UserRole, clave)
            self.lista_entornos.addItem(it)
        self.lista_entornos.itemDoubleClicked.connect(lambda it: self._cambiar("entorno", it.data(Qt.UserRole)))
        vb.addWidget(self.lista_entornos)
        pestanas.addTab(bib, "Biblioteca de entornos")
        self.brillo.cambiado.connect(lambda v: self._cambiar("brillo", v))
        self.rotacion.cambiado.connect(lambda v: self._cambiar("rotacion", v % 360.0))
        self.fondo.currentIndexChanged.connect(lambda _i: self._cambiar("fondo", self.fondo.currentData()))
        for clave, chk in (("suelo", self.suelo), ("reflejos", self.reflejos), ("sombras", self.sombras),
                           ("oclusion", self.oclusion)):
            chk.toggled.connect(lambda v, c=clave: self._cambiar(c, bool(v)))
        self.rugosidad.cambiado.connect(lambda v: self._cambiar("rugosidad_suelo", v))
        self.camara.currentIndexChanged.connect(lambda _i: self._cambiar("camara", self.camara.currentData()))
        self.focal.cambiado.connect(lambda v: self._cambiar("focal", v))
        self.exposicion.cambiado.connect(lambda v: self._cambiar("exposicion", v))

    def set_escena(self, escena):
        self._cargando = True
        e = self._escena = rc.escena_normalizada(escena)
        self.lb_entorno.setText(ENTORNOS.get(e["entorno"], ENTORNOS["fotomaton"])[0])
        self.brillo.set_valor(e["brillo"])
        rot = e["rotacion"]
        self.rotacion.set_valor(rot - 360 if rot > 180 else rot)
        self.fondo.setCurrentIndex(self.fondo.findData(e["fondo"]))
        self.boton_color.setStyleSheet(f"background: {QColor.fromRgbF(*e['color_fondo']).name()};")
        self.boton_color.setEnabled(e["fondo"] == "color")
        self.suelo.setChecked(e["suelo"])
        self.reflejos.setChecked(e["reflejos"])
        self.reflejos.setEnabled(e["suelo"])
        self.rugosidad.set_valor(e["rugosidad_suelo"])
        self.rugosidad.setEnabled(e["suelo"] and e["reflejos"])
        self.sombras.setChecked(e["sombras"])
        self.camara.setCurrentIndex(self.camara.findData(e["camara"]))
        self.focal.set_valor(e["focal"])
        self.focal.setEnabled(e["camara"] == "perspectiva")
        self.exposicion.set_valor(e["exposicion"])
        self.oclusion.setChecked(e["oclusion"])
        for i in range(self.lista_entornos.count()):
            it = self.lista_entornos.item(i)
            it.setSelected(it.data(Qt.UserRole) == e["entorno"])
        self._cargando = False

    def _cambiar(self, clave, valor):
        if self._cargando:
            return
        e = dict(self._escena)
        e[clave] = valor
        self.set_escena(e)
        self.escena_cambiada.emit(dict(self._escena))

    def _elegir_color(self):
        c = QColorDialog.getColor(QColor.fromRgbF(*self._escena["color_fondo"]), self, "Color de fondo")
        if c.isValid():
            self._cambiar("color_fondo", [c.redF(), c.greenF(), c.blueF()])


class PanelAspecto(PanelFlotante):
    """CONFIGURAR › Aspecto [GUID-118C6889]: biblioteca por familias y los aspectos usados en el diseño.
    Elegí un aspecto y hacé clic en un cuerpo para aplicarlo (como arrastrarlo en Fusion), o usá
    «Aplicar a la selección»."""
    aplicar = Signal(str)          # nombre del aspecto → a los cuerpos seleccionados
    quitar = Signal()

    def __init__(self, parent=None):
        super().__init__("Aspecto", parent)
        fila = QHBoxLayout()
        fila.addWidget(QLabel("Aplicar a:"))
        self.aplicar_a = QComboBox()
        self.aplicar_a.addItem("Cuerpos/componentes")
        self.aplicar_a.addItem("Caras")
        self.aplicar_a.model().item(1).setEnabled(False)
        self.aplicar_a.setToolTip("Aplicar aspectos a caras sueltas no está disponible.")
        fila.addWidget(self.aplicar_a, 1)
        self.cuerpo.addLayout(fila)
        self.cuerpo.addWidget(_seccion("En este diseño"))
        self.en_diseno = QListWidget()
        self.en_diseno.setIconSize(QSize(24, 24))
        self.en_diseno.setMaximumHeight(74)
        self.cuerpo.addWidget(self.en_diseno)
        self.cuerpo.addWidget(_seccion("Biblioteca"))
        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setIconSize(QSize(26, 26))
        self.arbol.setMinimumHeight(170)
        familias = {}
        for nombre, datos in rc.BIBLIOTECA_ASPECTOS.items():
            cat = datos["categoria"]
            if cat not in familias:
                familias[cat] = QTreeWidgetItem(self.arbol, [cat])
            hoja = QTreeWidgetItem(familias[cat], [nombre])
            hoja.setIcon(0, icono_aspecto(nombre))
            hoja.setData(0, Qt.UserRole, nombre)
        for cat in ("Metal", "Plástico"):
            if cat in familias:
                familias[cat].setExpanded(True)
        self.cuerpo.addWidget(self.arbol, 1)
        self.ayuda = QLabel("Elegí un aspecto y hacé clic en un cuerpo para aplicarlo.")
        self.ayuda.setWordWrap(True)
        temas.poner_rol(self.ayuda, "tenue")
        self.cuerpo.addWidget(self.ayuda)
        botones = QHBoxLayout()
        self.b_aplicar = QPushButton("Aplicar a la selección")
        self.b_aplicar.setObjectName("boton_primario")
        self.b_quitar = QPushButton("Quitar aspecto")
        botones.addWidget(self.b_aplicar)
        botones.addWidget(self.b_quitar)
        self.cuerpo.addLayout(botones)
        self.b_aplicar.clicked.connect(lambda: self.aplicar.emit(self.elegido()) if self.elegido() else None)
        self.b_quitar.clicked.connect(self.quitar.emit)
        self.en_diseno.itemClicked.connect(lambda it: self._seleccionar(it.data(Qt.UserRole)))

    def elegido(self):
        it = self.arbol.currentItem()
        return it.data(0, Qt.UserRole) if it is not None else None

    def _seleccionar(self, nombre):
        for i in range(self.arbol.topLevelItemCount()):
            fam = self.arbol.topLevelItem(i)
            for j in range(fam.childCount()):
                if fam.child(j).data(0, Qt.UserRole) == nombre:
                    self.arbol.setCurrentItem(fam.child(j))
                    return

    def set_usados(self, usados):
        """usados: {nombre del aspecto: cantidad de cuerpos}."""
        self.en_diseno.clear()
        for nombre, n in sorted(usados.items()):
            it = QListWidgetItem(f"{nombre}  ({n})")
            if nombre in rc.BIBLIOTECA_ASPECTOS:
                it.setIcon(icono_aspecto(nombre))
            it.setData(Qt.UserRole, nombre)
            self.en_diseno.addItem(it)


# =============================================================== diálogos
PRESETS = [("Web (1024 × 768)", 1024, 768), ("HD (1280 × 720)", 1280, 720), ("Full HD (1920 × 1080)", 1920, 1080),
           ("Cuadrado (1080 × 1080)", 1080, 1080), ("Impresión (3000 × 2000)", 3000, 2000),
           ("Tamaño de la ventana", 0, 0), ("Personalizado", -1, -1)]
CALIDADES = [("Borrador (1×)", 1), ("Estándar (2×)", 2), ("Final (3×)", 3)]


class DialogoRenderizar(QDialog):
    """RENDERIZAR › Renderizar [GUID-AFA42779] (renderizador local) y Capturar imagen [GUID-BF31CE62]."""

    def __init__(self, parent, tam_ventana, ruta_defecto, captura=False):
        super().__init__(parent)
        self.setWindowTitle("Capturar imagen" if captura else "Configuración de render")
        self.tam_ventana = tam_ventana
        f = QFormLayout(self)
        self.preset = QComboBox()
        for texto, w, h in PRESETS:
            self.preset.addItem(texto, (w, h))
        self.ancho, self.alto = QSpinBox(), QSpinBox()
        for s in (self.ancho, self.alto):
            s.setRange(16, 8000)
            s.setSuffix(" px")
        self.bloquear = QCheckBox("Bloquear relación de aspecto")
        self.bloquear.setChecked(True)
        tam = QHBoxLayout()
        tam.addWidget(self.ancho)
        tam.addWidget(QLabel("×"))
        tam.addWidget(self.alto)
        f.addRow("Tamaño", self.preset)
        f.addRow("", tam)
        f.addRow("", self.bloquear)
        self.motor = QComboBox()
        self.motor.addItem("Local — OpenGL (rápido)", "gl")
        self.motor.addItem("Local — CPU (software, sin placa de video)", "cpu")
        self.calidad = QComboBox()
        for texto, ss in CALIDADES:
            self.calidad.addItem(texto, ss)
        self.calidad.setCurrentIndex(1)
        self.transparente = QCheckBox("Fondo transparente")
        f.addRow("Renderizador", self.motor)
        f.addRow("Calidad", self.calidad)
        f.addRow("", self.transparente)
        self.ruta = QLineEdit(str(ruta_defecto))
        examinar = QToolButton(text="…")
        examinar.clicked.connect(self._examinar)
        fila = QHBoxLayout()
        fila.addWidget(self.ruta, 1)
        fila.addWidget(examinar)
        f.addRow("Guardar en", fila)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Capturar" if captura else "Renderizar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        f.addRow(botones)
        self._relacion = 4 / 3
        self.preset.currentIndexChanged.connect(self._preset)
        self.ancho.valueChanged.connect(lambda v: self._mantener("ancho", v))
        self.alto.valueChanged.connect(lambda v: self._mantener("alto", v))
        self.preset.setCurrentIndex(5 if captura else 2)
        self._preset()

    def _preset(self):
        w, h = self.preset.currentData()
        if w == 0:
            w, h = self.tam_ventana
        if w > 0:
            self._bloqueado = True
            self.ancho.setValue(w)
            self.alto.setValue(h)
            self._bloqueado = False
            self._relacion = w / max(h, 1)
        manual = self.preset.currentData()[0] < 0
        self.ancho.setEnabled(manual)
        self.alto.setEnabled(manual)
        self.bloquear.setEnabled(manual)

    def _mantener(self, cual, valor):
        if getattr(self, "_bloqueado", False):
            return
        if self.bloquear.isChecked():
            self._bloqueado = True
            if cual == "ancho":
                self.alto.setValue(max(16, round(valor / self._relacion)))
            else:
                self.ancho.setValue(max(16, round(valor * self._relacion)))
            self._bloqueado = False
        else:
            self._relacion = self.ancho.value() / max(self.alto.value(), 1)

    def _examinar(self):
        ruta, _f = QFileDialog.getSaveFileName(self, "Guardar imagen", self.ruta.text(), "Imagen PNG (*.png)")
        if ruta:
            self.ruta.setText(ruta if ruta.lower().endswith(".png") else ruta + ".png")

    def valores(self):
        return {"ancho": self.ancho.value(), "alto": self.alto.value(), "motor": self.motor.currentData(),
                "supermuestreo": self.calidad.currentData(), "fondo_transparente": self.transparente.isChecked(),
                "ruta": self.ruta.text().strip()}


class DialogoLienzo(QDialog):
    """RENDERIZAR EN EL LIENZO › Configuración [RND-IN-CANVAS-SETTINGS]."""

    def __init__(self, parent, supermuestreo, oclusion):
        super().__init__(parent)
        self.setWindowTitle("Configuración del render en el lienzo")
        f = QFormLayout(self)
        self.calidad = QComboBox()
        for texto, ss in CALIDADES:
            self.calidad.addItem(texto, ss)
        self.calidad.setCurrentIndex(max(0, self.calidad.findData(supermuestreo)))
        self.oclusion = QCheckBox("Oclusión ambiental")
        self.oclusion.setChecked(oclusion)
        f.addRow("Calidad (supermuestreo)", self.calidad)
        f.addRow("", self.oclusion)
        nota = QLabel("Más calidad = más lento al orbitar. El render final se configura en RENDERIZAR.")
        nota.setWordWrap(True)
        f.addRow(nota)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


def imagen_a_qimage(img):
    img = np.ascontiguousarray(img, np.uint8)
    h, w = img.shape[:2]
    q = QImage(img.data, w, h, 4 * w, QImage.Format_RGBA8888)
    return q.copy()


class VisorImagen(QDialog):
    """Visor de la Galería: la imagen a tamaño de la ventana y «Guardar como…»."""

    def __init__(self, parent, render):
        super().__init__(parent)
        self.render = render
        self.setWindowTitle(f"{render['nombre']} — {render['ancho']} × {render['alto']}")
        v = QVBoxLayout(self)
        area = QScrollArea()
        area.setAlignment(Qt.AlignCenter)
        lb = QLabel()
        pm = QPixmap.fromImage(imagen_a_qimage(render["imagen"]))
        lb.setPixmap(pm.scaled(1200, 760, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                     if pm.width() > 1200 or pm.height() > 760 else pm)
        area.setWidget(lb)
        v.addWidget(area, 1)
        info = QLabel(f"{render['motor']} · {render['segundos']:.1f} s" + (f" · {render['ruta']}" if render.get("ruta") else ""))
        temas.poner_rol(info, "tenue")
        v.addWidget(info)
        b = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Save).setText("Guardar como…")
        b.accepted.connect(self._guardar)
        b.rejected.connect(self.reject)
        v.addWidget(b)
        self.resize(min(pm.width() + 40, 1240), min(pm.height() + 90, 860))

    def _guardar(self):
        ruta, _f = QFileDialog.getSaveFileName(self, "Guardar imagen", self.render.get("ruta") or
                                               f"{self.render['nombre']}.png", "Imagen PNG (*.png)")
        if ruta:
            try:
                rc.guardar_png(self.render["imagen"], ruta)
            except ErrorGeometria as e:
                QMessageBox.warning(self, "Guardar imagen", str(e))


class GaleriaRender(QFrame):
    """RENDERIZAR › Galería de renders [GUID-8C205185]: miniaturas de los renders de la sesión."""
    abrir = Signal(int)
    guardar = Signal(int)
    volver = Signal(int)
    borrar = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("galeria_render")
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 4, 8, 4)
        titulo = QLabel("GALERÍA DE\nRENDERS")
        temas.poner_rol(titulo, "encabezado")
        h.addWidget(titulo)
        self.lista = QListWidget()
        self.lista.setViewMode(QListWidget.IconMode)
        self.lista.setFlow(QListWidget.LeftToRight)
        self.lista.setWrapping(False)
        self.lista.setIconSize(QSize(120, 72))
        self.lista.setFixedHeight(112)
        self.lista.setMovement(QListWidget.Static)
        self.lista.setSpacing(4)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu)
        self.lista.itemDoubleClicked.connect(lambda it: self.abrir.emit(self.lista.row(it)))
        h.addWidget(self.lista, 1)
        self.vacio = QLabel("Los renders de esta sesión aparecen acá (RENDERIZAR › Renderizar).")
        temas.poner_rol(self.vacio, "tenue")
        h.addWidget(self.vacio)

    def actualizar(self, renders):
        self.lista.clear()
        for r in renders:
            pm = QPixmap.fromImage(imagen_a_qimage(r["imagen"])).scaled(120, 72, Qt.KeepAspectRatio,
                                                                        Qt.SmoothTransformation)
            it = QListWidgetItem(QIcon(pm), f"{r['nombre']}\n{r['ancho']}×{r['alto']}")
            it.setToolTip(f"{r['nombre']} — {r['motor']}, {r['segundos']:.1f} s. Doble clic para abrir.")
            self.lista.addItem(it)
        self.vacio.setVisible(not renders)
        self.lista.setVisible(bool(renders))

    def _menu(self, pos):
        it = self.lista.itemAt(pos)
        if it is None:
            return
        i = self.lista.row(it)
        m = QMenu(self)
        m.addAction("Abrir", lambda: self.abrir.emit(i))
        m.addAction("Guardar como…", lambda: self.guardar.emit(i))
        m.addAction("Volver a renderizar", lambda: self.volver.emit(i))
        m.addSeparator()
        m.addAction("Eliminar de la galería", lambda: self.borrar.emit(i))
        m.exec(self.lista.mapToGlobal(pos))


# =============================================================== ventana
GRUPOS_RENDER = [
    ("CONFIGURAR", ["aspecto", "escena"], ["aspecto", "escena", SEP, ("Calcomanía",), ("Mapeo de texturas",)]),
    ("RENDERIZAR EN EL LIENZO", ["lienzo", "capturar"], ["lienzo", "config_lienzo", "capturar"]),
    ("RENDERIZAR", ["renderizar"], ["renderizar", "galeria"]),
    ("TERMINAR RENDERIZAR", ["terminar"], ["terminar"]),
]


class _Oyente:
    """Suscripción al documento que no mantiene viva la ventana (el documento no tiene «desuscribir»)."""

    def __init__(self, ventana):
        self.ref = weakref.ref(ventana)

    def __call__(self):
        v = self.ref()
        if v is not None:
            try:
                v._modelo_cambio()
            except RuntimeError:     # el objeto de Qt ya se destruyó
                pass


class VentanaRender(QMainWindow):
    """Espacio de trabajo RENDERIZAR para el documento `doc` (ver el docstring del módulo)."""
    cambiado = Signal()

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        app = QApplication.instance()
        if app is not None and not app.styleSheet():
            temas.aplicar_a_app(app)
        self.doc = doc
        self.setWindowTitle(f"{doc.nombre} — Renderizar — {NOMBRE_APP}")
        self.resize(1400, 900)
        self.renders = []                  # galería de la sesión
        self.seleccion = []                # ids de cuerpos elegidos en el lienzo
        self._programado = self._pendiente = False
        self.lienzo = LienzoRender()
        self.area = AreaVisor(self.lienzo)
        self.acciones = self._crear_acciones()
        self.cinta = CintaEspacio("RENDERIZAR", "RENDERIZAR", GRUPOS_RENDER, self.acciones, self)
        self.cinta.ir_a_diseno.connect(self.close)
        self.galeria = GaleriaRender(self)
        self.galeria.abrir.connect(self.abrir_render)
        self.galeria.guardar.connect(self.guardar_render)
        self.galeria.volver.connect(self.volver_a_renderizar)
        self.galeria.borrar.connect(self._borrar_render)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.cinta)
        lay.addWidget(self.area, 1)
        lay.addWidget(self.galeria)
        self.setCentralWidget(central)
        self.panel_escena = PanelEscena()
        self.panel_escena.escena_cambiada.connect(self.set_escena)
        self.panel_escena.cerrado.connect(lambda: self._panel_cerrado(self.panel_escena))
        self.panel_aspecto = PanelAspecto()
        self.panel_aspecto.aplicar.connect(lambda nombre: self.aplicar_aspecto(nombre, self.seleccion))
        self.panel_aspecto.quitar.connect(lambda: self.quitar_aspecto(self.seleccion))
        self.panel_aspecto.cerrado.connect(lambda: self._panel_cerrado(self.panel_aspecto))
        for p in (self.panel_escena, self.panel_aspecto):
            p.hide()
        self.lienzo.set_filtro({"cuerpo"})
        self.lienzo.entidad_elegida.connect(self._clic_cuerpo)
        self.lienzo.clic_vacio.connect(lambda: self.seleccionar([]))
        self.lienzo.estado_render.connect(self.indicar)
        self.panel_escena.set_escena(self.lienzo.escena)
        self.galeria.actualizar(self.renders)
        doc.suscribir(_Oyente(self))
        self.actualizar()
        QTimer.singleShot(0, self.lienzo, self.lienzo.encuadrar)   # con contexto: no corre si el lienzo ya no existe
        self.indicar("Elegí un cuerpo y un aspecto (CONFIGURAR › Aspecto); ajustá la escena y RENDERIZAR.")

    # ------------------------------------------------------------ acciones
    def _crear_acciones(self):
        definicion = [
            ("aspecto", "Aspecto", "aspecto", self.mostrar_aspecto, False),
            ("escena", "Configuración de escena", "escena", self.mostrar_escena, False),
            ("lienzo", "Renderizar en el lienzo", "lienzo", self.alternar_lienzo, True),
            ("config_lienzo", "Configuración del render en el lienzo…", "configurar", self.configurar_lienzo, False),
            ("capturar", "Capturar imagen…", "captura", self.dialogo_capturar, False),
            ("renderizar", "Renderizar…", "render", self.dialogo_renderizar, False),
            ("galeria", "Galería de renders", "galeria", lambda: self.galeria.setVisible(not self.galeria.isVisible()),
             False),
            ("terminar", "Terminar renderizar", "terminar", self.close, False),
        ]
        acciones = {}
        for clave, texto, ico, funcion, marcable in definicion:
            a = QAction(icono_render(ico), texto, self)
            a.setToolTip(texto.rstrip("…"))
            a.setCheckable(marcable)
            a.triggered.connect(funcion)
            acciones[clave] = a
        return acciones

    def indicar(self, texto):
        self.statusBar().showMessage(texto)

    # ------------------------------------------------------------ modelo
    def actualizar(self):
        self._programado = self._pendiente = False
        estado = self.doc.estado_final
        self.lienzo.cargar(estado, self.doc.propiedades)
        self.seleccion = [c for c in self.seleccion if c in self.lienzo.objetos]
        self._resaltar()
        usados = {}
        for o in self.lienzo.objetos.values():
            nombre = o["acabado"].get("nombre") or rc.ASPECTO_DEFECTO
            usados[nombre] = usados.get(nombre, 0) + 1
        self.panel_aspecto.set_usados(usados)
        self.setWindowTitle(f"{self.doc.nombre} — Renderizar — {NOMBRE_APP}")

    def _modelo_cambio(self):
        if not self.isVisible():
            self._pendiente = True
            return
        if not self._programado:
            self._programado = True
            QTimer.singleShot(0, self.actualizar)

    def showEvent(self, e):
        super().showEvent(e)
        if self._pendiente:
            self.actualizar()

    # ------------------------------------------------------------ selección y aspectos
    def _clic_cuerpo(self, hit):
        cid = hit.get("cuerpo")
        nombre = self.panel_aspecto.elegido() if not self.panel_aspecto.isHidden() else None
        if nombre:
            self.aplicar_aspecto(nombre, [cid])
            self.seleccionar([cid])
            return
        if QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            sel = [c for c in self.seleccion if c != cid] + ([] if cid in self.seleccion else [cid])
        else:
            sel = [cid]
        self.seleccionar(sel)

    def seleccionar(self, ids):
        self.seleccion = [c for c in ids if c in self.lienzo.objetos]
        self._resaltar()
        if self.seleccion:
            nombres = ", ".join(self.lienzo.objetos[c]["nombre"] for c in self.seleccion)
            self.indicar(f"Seleccionado: {nombres}")

    def _resaltar(self):
        prims = [("tris", m["v"], None, 0.30) for m in self.lienzo._mallas if m["id"] in self.seleccion]
        self.lienzo.set_capa("seleccion", prims)

    def aplicar_aspecto(self, nombre, ids=None):
        """Aplica un aspecto de la biblioteca a los cuerpos (todos si `ids` está vacío)."""
        ids = [c for c in (ids or list(self.lienzo.objetos)) if c in self.doc.estado_final.cuerpos]
        if not ids:
            self.indicar("Elegí un cuerpo en el lienzo.")
            return
        color, acabado = rc.aspecto(nombre)
        self.doc.set_propiedad(ids, "acabado", acabado)
        self.doc.set_propiedad(ids, "apariencia", color)
        self.actualizar()
        self.indicar(f"Aspecto «{nombre}» aplicado a {len(ids)} cuerpo(s).")
        self.cambiado.emit()

    def quitar_aspecto(self, ids=None):
        ids = [c for c in (ids or []) if c in self.doc.estado_final.cuerpos]
        if not ids:
            self.indicar("Elegí los cuerpos a los que querés quitarles el aspecto.")
            return
        self.doc.set_propiedad(ids, "acabado", None)
        self.doc.set_propiedad(ids, "apariencia", None)
        self.actualizar()
        self.cambiado.emit()

    # ------------------------------------------------------------ escena y paneles
    def _mostrar_panel(self, panel):
        for p in (self.panel_escena, self.panel_aspecto):
            if p is not panel:
                p.hide()
        self.area.set_panel(panel)          # cambia el padre (eso lo oculta): mostrar después
        panel.show()
        self.area.reubicar()

    def _panel_cerrado(self, panel):
        if self.area.panel is panel:
            self.area.set_panel(None)

    def mostrar_escena(self):
        self.panel_escena.set_escena(self.lienzo.escena)
        self._mostrar_panel(self.panel_escena)

    def mostrar_aspecto(self):
        self._mostrar_panel(self.panel_aspecto)

    def set_escena(self, escena):
        self.lienzo.set_escena(escena)
        if not self.panel_escena.isHidden():
            self.panel_escena.set_escena(self.lienzo.escena)
        self.cambiado.emit()

    def alternar_lienzo(self, activo=None):
        """RENDERIZAR EN EL LIENZO › Renderizar en el lienzo [GUID-C8057393]: supermuestreo y oclusión."""
        activo = (not self.lienzo.alta_calidad) if activo is None else bool(activo)
        self.acciones["lienzo"].setChecked(activo)
        self.lienzo.alta_calidad = activo
        self.lienzo.update()
        if activo:
            if not self.lienzo.gl_disponible():
                self.indicar("Sin OpenGL: el render en el lienzo no está disponible (RENDERIZAR usa la CPU).")
            else:
                self.indicar(f"Render en el lienzo: supermuestreo {self.lienzo.supermuestreo}×"
                             f"{', oclusión ambiental' if self.lienzo.escena['oclusion'] else ''}.")
        else:
            self.indicar("Render en el lienzo desactivado.")

    def configurar_lienzo(self):
        d = DialogoLienzo(self, self.lienzo.supermuestreo, self.lienzo.escena["oclusion"])
        if d.exec() == QDialog.Accepted:
            self.lienzo.supermuestreo = d.calidad.currentData()
            e = dict(self.lienzo.escena)
            e["oclusion"] = d.oclusion.isChecked()
            self.set_escena(e)
            self.panel_escena.set_escena(self.lienzo.escena)

    # ------------------------------------------------------------ renderizar
    def _ruta_defecto(self, sufijo="render"):
        base = Path(self.doc.ruta).parent if getattr(self.doc, "ruta", None) else Path.home()
        n = len(self.renders) + 1
        nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.doc.nombre).strip() or "render"
        return base / f"{nombre}_{sufijo}{n}.png"

    def _tam_ventana(self):
        return max(16, self.lienzo.width()), max(16, self.lienzo.height())

    def dialogo_renderizar(self):
        d = DialogoRenderizar(self, self._tam_ventana(), self._ruta_defecto())
        if d.exec() == QDialog.Accepted:
            self.renderizar(**d.valores())

    def dialogo_capturar(self):
        d = DialogoRenderizar(self, self._tam_ventana(), self._ruta_defecto("captura"), captura=True)
        if d.exec() == QDialog.Accepted:
            v = d.valores()
            self.renderizar(**v, a_galeria=False)

    def renderizar(self, ancho=1920, alto=1080, motor="gl", supermuestreo=2, fondo_transparente=False, ruta=None,
                   a_galeria=True, camara=None, escena=None):
        """Genera la imagen final; la guarda en PNG si hay `ruta` y la suma a la Galería. Devuelve el dict del
        render ({"nombre", "imagen", "ancho", "alto", "motor", "segundos", "escena", "camara", "ruta"})."""
        cam_previa, esc_previa = self.lienzo.camara_dict(), self.lienzo.escena
        if camara:
            self.lienzo.aplicar_camara(camara)
        if escena:
            self.lienzo.set_escena(escena)
        progreso = None
        dlg = None
        if self.isVisible():
            dlg = QProgressDialog("Renderizando…", "Cancelar", 0, 100, self)
            dlg.setWindowTitle("Renderizar")
            dlg.setWindowModality(Qt.WindowModal)
            dlg.setMinimumDuration(300)

            def progreso(f):
                dlg.setValue(int(f * 100))
                QApplication.processEvents()
                return not dlg.wasCanceled()
        t0 = time.perf_counter()
        try:
            img = self.lienzo.renderizar_imagen(ancho, alto, supermuestreo, motor, fondo_transparente, progreso)
        except rc.RenderCancelado:
            self.indicar("Render cancelado.")
            return None
        except (ErrorGeometria, MemoryError) as e:
            self.indicar(f"No se pudo renderizar: {e}")
            if self.isVisible():
                QMessageBox.warning(self, "Renderizar", str(e))
            return None
        finally:
            if dlg is not None:
                dlg.close()
            if camara:
                self.lienzo.aplicar_camara(cam_previa)
            if escena:
                self.lienzo.set_escena(esc_previa)
        segundos = time.perf_counter() - t0
        usado = self.lienzo.ultimo_motor or "CPU"
        render = {"nombre": f"Render {len(self.renders) + 1}" if a_galeria else "Captura", "imagen": img,
                  "ancho": int(ancho), "alto": int(alto), "motor": f"Local ({usado}, {supermuestreo}×)",
                  "segundos": segundos, "escena": dict(escena or esc_previa), "camara": camara or cam_previa,
                  "supermuestreo": supermuestreo, "fondo_transparente": fondo_transparente, "ruta": ruta or None}
        if ruta:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
                rc.guardar_png(img, ruta)
            except (ErrorGeometria, OSError) as e:
                render["ruta"] = None
                self.indicar(f"No se pudo guardar la imagen: {e}")
        if a_galeria:
            self.renders.append(render)
            self.galeria.actualizar(self.renders)
        self.indicar(f"{render['nombre']}: {ancho} × {alto} en {segundos:.1f} s ({usado})"
                     + (f" — guardado en {render['ruta']}" if render["ruta"] else ""))
        return render

    def abrir_render(self, i):
        VisorImagen(self, self.renders[i]).exec()

    def guardar_render(self, i, ruta=None):
        r = self.renders[i]
        if ruta is None:
            ruta, _f = QFileDialog.getSaveFileName(self, "Guardar imagen", r.get("ruta") or f"{r['nombre']}.png",
                                                   "Imagen PNG (*.png)")
        if ruta:
            rc.guardar_png(r["imagen"], ruta)
            r["ruta"] = ruta
            self.indicar(f"Guardado: {ruta}")

    def volver_a_renderizar(self, i):
        """Galería › Volver a renderizar [RND-RERENDER-IMAGE]: misma cámara, escena y tamaño."""
        r = self.renders[i]
        return self.renderizar(r["ancho"], r["alto"], "gl", r["supermuestreo"], r["fondo_transparente"], None,
                               camara=r["camara"], escena=r["escena"])

    def _borrar_render(self, i):
        del self.renders[i]
        self.galeria.actualizar(self.renders)

    # ------------------------------------------------------------ persistencia
    def a_dict(self):
        """Escena, cámara y opciones del lienzo (JSON) para guardarlas con el documento."""
        cam = self.lienzo.camara_dict()
        return {"version": 1, "escena": dict(self.lienzo.escena), "camara": cam,
                "lienzo": {"alta_calidad": bool(self.lienzo.alta_calidad), "supermuestreo": int(self.lienzo.supermuestreo)}}

    def desde_dict(self, datos):
        datos = datos or {}
        self.set_escena(datos.get("escena"))
        self.panel_escena.set_escena(self.lienzo.escena)
        lz = datos.get("lienzo") or {}
        self.lienzo.supermuestreo = int(lz.get("supermuestreo", 2))
        self.acciones["lienzo"].setChecked(bool(lz.get("alta_calidad", False)))
        self.lienzo.alta_calidad = bool(lz.get("alta_calidad", False))
        if datos.get("camara"):
            self.lienzo.aplicar_camara(datos["camara"])
