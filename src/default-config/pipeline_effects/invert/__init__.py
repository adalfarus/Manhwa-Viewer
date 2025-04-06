"""TBA"""
from modules.pipeline_plugin.gui import Input, Combobox
from modules.pipeline_plugin.types import glUniform1iType
import cv2
import numpy as np


effect_name: str = "Invert"
effect_id: str = "invert"

supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "invert.vert"
fragment_shader_src: str = "invert.frag"

INVERT_MODES: dict[str, int] = {
    "Full (RGB)": 0,
    "Brightness": 1,
    "Saturation": 2,
    "Red Only": 3,
    "Green Only": 4,
    "Blue Only": 5
}

register_gui_inputs: dict[str, Input[int]] = {
    "mode": Input("Invert Mode", glUniform1iType, Combobox(INVERT_MODES), default=0)
}

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
    elif mode == 3:  # Red
        img[..., 2] = 1.0 - img[..., 2]
    elif mode == 4:  # Green
        img[..., 1] = 1.0 - img[..., 1]
    elif mode == 5:  # Blue
        img[..., 0] = 1.0 - img[..., 0]
    return (img * 255).astype(np.uint8)
