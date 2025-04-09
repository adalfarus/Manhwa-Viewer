"""TBA"""
from PySide6.QtWidgets import QWidget

from modules.pipeline_plugin.gui import Input, Slider, Widget
from modules.pipeline_plugin.types import glUniform1i
import cv2
import numpy as np


effect_name: str = "Stylize: Quantize Colors"
effect_name_format: str = "Quantize Colors {levels} levels"
effect_id: str = "quantize"

supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "shader.vert"
fragment_shader_src: str = "shader.frag"

register_gui_inputs: dict[str, Input[int]] = {
    "levels": Input("{n} levels", glUniform1i, Slider(2, 32, 1, int), default=4)
}

def update_gui(gui_widgets: dict[str, QWidget | Widget]) -> None:
    """Called whenever the gui updates"""
    ...

def apply_transform_cpu(img: np.ndarray, levels: int) -> np.ndarray:
    """
    Reduces number of unique colors in an image. Ex: 4 levels → 64 colors.
    """
    if levels < 2:
        levels = 2  # prevent divide by zero or 1
    factor = 256 // levels
    return ((img // factor) * factor).astype(np.uint8)
