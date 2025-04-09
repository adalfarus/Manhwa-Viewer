"""TBA"""
from abc import abstractmethod as _abstractmethod, ABCMeta as _ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


class ShaderObject(metaclass=_ABCMeta): pass


class ShaderInput(ShaderObject):
    def __init__(self, name: str) -> None:
        self.name: str = name


_GLSLScalar = _ty.Literal["float", "int", "uint", "bool"]
_GLSLVector = _ty.Literal[
    "vec2", "vec3", "vec4",
    "ivec2", "ivec3", "ivec4",
    "uvec2", "uvec3", "uvec4"
]
_GLSLMatrix = _ty.Literal["mat2", "mat3", "mat4"]

class SSBO(ShaderObject):
    def __init__(self, name: str, dtype: _ty.Literal[_GLSLScalar, _GLSLVector, _GLSLMatrix], size: int,
                 layout: _ty.Literal["std430", "std140"] = "std430") -> None:
        self.name: str = name
        self.dtype: _ty.Literal[_GLSLScalar, _GLSLVector, _GLSLMatrix] = dtype
        self.size: int = size
        self.layout: _ty.Literal["std430", "std140"] = layout


class Shader(metaclass=_ABCMeta):
    def __init__(self, abs_shader_path: str, inputs: list[ShaderObject]) -> None:
        self.abs_shader_path: str = abs_shader_path
        self.inputs: list[ShaderObject] = inputs


class ComputeShader(Shader): pass
class VertexShader(Shader): pass
class FragmentShader(Shader): pass


class ShaderPipeline:
    def __init__(self, *shaders: Shader) -> None:
        self.shaders: tuple[Shader, ...] = shaders
