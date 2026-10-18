# -*- coding: utf-8 -*-
"""Compatibilidad del importador SAB; la implementación geométrica vive en el núcleo."""
import sys

from ..nucleo import acis_occ

sys.modules[__name__] = acis_occ
