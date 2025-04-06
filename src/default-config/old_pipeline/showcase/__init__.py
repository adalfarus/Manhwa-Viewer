"""TBA"""
from modules.pipeline_plugin.gui import Input, Checkbox, Slider, Spinbox, ColorPicker, NoGui
from modules.pipeline_plugin.types import glUniform1iType, glUniform1fType, glUniform3fType, glUniform2fType
import cv2


supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "invert.vert"
fragment_shader_src: str = "invert.frag"


register_gui_inputs: dict[str, Input] = {
    "myinput1": Input("MyInput 1: ", glUniform1iType, Checkbox("Turn off"), default=0),
    "input2": Input("Brightness", glUniform1fType, Slider(min_=0.0, max_=2.0, step=0.01, type_=float), default=1.0),
    "level": Input("Posterize Levels", glUniform1iType, Spinbox(min_=2, max_=16, step=1, type_=int), default=4),
    "tint": Input("Tint Color", glUniform3fType, ColorPicker(), default=(1.0, 1.0, 1.0)),
    "center": Input("Center", glUniform2fType, NoGui(), default=(0.5, 0.5))
    # ...
}


def apply_transform_cpu(img, myinput1: bool, input2: float, level: int, tint: tuple[float, float, float], center: tuple[float, float]) -> img:
    ...
