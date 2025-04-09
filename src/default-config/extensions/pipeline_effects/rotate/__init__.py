"""TBA"""
from PySide6.QtWidgets import QWidget

from modules.pipeline_plugin.gui import Input, Combobox, Widget
from modules.pipeline_plugin.types import glUniform1i
import cv2
import numpy as np


effect_name: str = "Fix: Rotate"
effect_name_format: str = "Rotate {mode}"
effect_id: str = "rotate"

supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "shader.vert"
fragment_shader_src: str = "shader.frag"

ROTATE_MODES: dict[str, int] = {
    "RGB Channels": 0,
    "Hue": 1
}

register_gui_inputs: dict[str, Input[int]] = {
    "mode": Input("Rotate Mode", glUniform1i, Combobox(ROTATE_MODES), default=0)
}

def update_gui(gui_widgets: dict[str, QWidget | Widget]) -> None:
    """Called whenever the gui updates"""
    ...

def apply_transform_cpu(img: np.ndarray, mode: int) -> np.ndarray:
    img = img.astype(np.float32) / 255.0

    if mode == 0:  # Full (RGB): rotate channels R → G → B
        img = img[..., [1, 2, 0]]  # G, B, R
    elif mode == 1:  # Hue rotation +90°
        bgr = img[..., ::-1]
        hsv = cv2.cvtColor(bgr, cv2.COLOR_RGB2HSV_FULL) / [360.0, 1.0, 1.0]
        hsv[..., 0] = np.mod(hsv[..., 0] + 0.25, 1.0)  # +90° in range [0,1]
        hsv = hsv * [360.0, 1.0, 1.0]
        rgb = cv2.cvtColor(hsv.astype(np.float32), cv2.COLOR_HSV2RGB_FULL)
        img = rgb[..., ::-1]
    return (img * 255).astype(np.uint8)
