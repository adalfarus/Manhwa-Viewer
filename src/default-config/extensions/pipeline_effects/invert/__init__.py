"""TBA"""
from PySide6.QtWidgets import QWidget

from modules.pipeline_plugin.gui import Input, Combobox, Widget
from modules.pipeline_plugin.types import glUniform1i
import cv2
import numpy as np


effect_name: str = "Fix: Invert"
effect_name_format: str = "Invert {mode}"
effect_id: str = "invert"

supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "shader.vert"
fragment_shader_src: str = "shader.frag"

INVERT_MODES: dict[str, int] = {
    "Full (RGB)": 0,
    "Brightness": 1,
    "Saturation": 2,
    "Hue": 3,
    "Red Only": 4,
    "Green Only": 5,
    "Blue Only": 6
}

register_gui_inputs: dict[str, Input[int]] = {
    "mode": Input("Invert Mode", glUniform1i, Combobox(INVERT_MODES), default=0)
}

def update_gui(gui_widgets: dict[str, QWidget | Widget]) -> None:
    """Called whenever the gui updates"""
    ...

def apply_transform_cpu(img: np.ndarray, mode: int) -> np.ndarray:
    img = img.astype(np.float32) / 255.0
    if mode == 0:
        img = 1.0 - img
    elif mode == 1:  # Brightness invert (HSV)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv[..., 2] = 1.0 - hsv[..., 2]
        img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif mode == 2:  # Saturation invert
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv[..., 1] = 1.0 - hsv[..., 1]
        img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif mode == 3:  # Hue invert
        # Convert manually using float32 HSV
        bgr = img[..., ::-1]  # BGR to RGB
        hsv = cv2.cvtColor(bgr, cv2.COLOR_RGB2HSV_FULL) / [360.0, 1.0, 1.0]

        hsv[..., 0] = (hsv[..., 0] + 0.5) % 1.0  # Invert hue
        hsv = hsv * [360.0, 1.0, 1.0]

        rgb = cv2.cvtColor(hsv.astype(np.float32), cv2.COLOR_HSV2RGB_FULL)
        img = rgb[..., ::-1]  # RGB to BGR again
    elif mode == 4:  # Red
        img[..., 2] = 1.0 - img[..., 2]
    elif mode == 5:  # Green
        img[..., 1] = 1.0 - img[..., 1]
    elif mode == 6:  # Blue
        img[..., 0] = 1.0 - img[..., 0]
    return (img * 255).astype(np.uint8)
