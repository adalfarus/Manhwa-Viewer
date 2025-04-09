from PySide6.QtWidgets import QWidget

from modules.pipeline_plugin.gui import Input, ColorPicker, Slider, Combobox, Widget
from modules.pipeline_plugin.types import glUniform1f, glUniform3f, glUniform1i
import numpy as np
import cv2

effect_name = "Color: Tint"
effect_name_format = "Tint {mode} {color} {intensity:.2f}"
effect_id = "tint_shader"

supports_opengl = True
supports_cpu = True
vertex_shader_src = "shader.vert"
fragment_shader_src = "shader.frag"

TINT_MODES = {
    "RGB": 0,
    "Brightness": 1,
    "Saturation": 2,
    "Hue Shift": 3
}

register_gui_inputs = {
    "mode": Input("Mode", glUniform1i, Combobox(TINT_MODES), default=0),
    "color": Input("Tint Color", glUniform3f, ColorPicker(), default=(1.0, 0.0, 0.0)),  # Red by default
    "intensity": Input("Intensity {n:.2f}", glUniform1f, Slider(0.0, 1.0, 0.01, float), default=0.5)
}

def update_gui(gui_widgets: dict[str, QWidget | Widget]) -> None:
    """Called whenever the gui updates"""
    ...

def apply_transform_cpu(img: np.ndarray, mode: int, color: tuple[float, float, float], intensity: float) -> np.ndarray:
    img = img.astype(np.float32) / 255.0
    tint = np.array(color[::-1], dtype=np.float32)  # RGB -> BGR because of cv2

    if mode == 0:  # RGB Blend
        result = (1.0 - intensity) * img + intensity * tint
    elif mode == 1:  # Brightness
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        v_tint = np.dot(tint, [0.114, 0.587, 0.299])
        hsv[..., 2] = (1.0 - intensity) * hsv[..., 2] + intensity * v_tint
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif mode == 2:  # Saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv[..., 1] = (1.0 - intensity) * hsv[..., 1] + intensity * 1.0  # Assume full sat for tint
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif mode == 3:  # Hue Shift
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        target_hue = (cv2.cvtColor(np.uint8([[tint * 255]]), cv2.COLOR_BGR2HSV)[0, 0, 0]) / 180.0
        hsv[..., 0] = (1.0 - intensity) * hsv[..., 0] + intensity * target_hue * 180.0
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    else:
        result = img

    return np.clip(result * 255, 0, 255).astype(np.uint8)
