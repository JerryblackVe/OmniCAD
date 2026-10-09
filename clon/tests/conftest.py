# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# Permite `import omnicad` corriendo pytest desde cualquier carpeta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
