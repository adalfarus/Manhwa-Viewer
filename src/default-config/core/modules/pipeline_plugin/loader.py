"""TBA"""
import importlib.util
import traceback
import os

from .gui import Input

import collections.abc as _a
import typing as _ty
import types as _ts


class PipelineEffectModule:
    def __init__(self, name: str, plugin: _ts.ModuleType, base_path: str) -> None:
        self.name: str = name
        self.module: _ts.ModuleType = plugin
        self.effect_name: str = plugin.effect_name  # UI display name
        self.effect_id: str = plugin.effect_id      # used in saved pipelines
        self.cpu_supported: bool = plugin.supports_cpu
        self.gpu_supported: bool = plugin.supports_opengl
        self.register_gui_inputs: dict[str, Input] = plugin.register_gui_inputs
        self.shader_paths: dict[_ty.Literal["vert", "frag"], str] | None = {
            "vert": os.path.join(base_path, plugin.vertex_shader_src),
            "frag": os.path.join(base_path, plugin.fragment_shader_src),
        } if self.gpu_supported else None
        self.cpu_function: _ts.FunctionType | None = getattr(plugin, "apply_transform_cpu", None)


class PipelineEffectLoader:
    def __init__(self) -> None:
        self.verified_modules: dict[str, PipelineEffectModule] = {}

    def load_from_folder(self, plugins_dir: str) -> None:
        for entry in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, entry)
            if not os.path.isdir(plugin_dir):
                continue
            try:
                module = self._load_plugin(plugin_dir, entry)
                self.verified_modules[entry] = module
                print(f"[✓] Loaded effect: {entry}")
            except Exception as e:
                print(f"[✗] Failed to load '{entry}': {e}")
                traceback.print_exc()

    def _load_plugin(self, plugin_dir: str, plugin_name: str) -> PipelineEffectModule:
        init_path = os.path.join(plugin_dir, "__init__.py")
        if not os.path.isfile(init_path):
            raise FileNotFoundError(f"No __init__.py found in '{plugin_name}'")

        spec = importlib.util.spec_from_file_location(plugin_name, init_path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)

        effect_name = getattr(plugin, "effect_name", None)
        effect_id = getattr(plugin, "effect_id", None)

        if not isinstance(effect_name, str) or not isinstance(effect_id, str):
            raise ValueError("Plugin must define string 'effect_name' and 'effect_id'")

        # Validate core properties
        supports_opengl = getattr(plugin, "supports_opengl", False)
        supports_cpu = getattr(plugin, "supports_cpu", False)

        if not (supports_opengl or supports_cpu):
            raise ValueError("Plugin must support at least one of: OpenGL or CPU")

        # Validate shaders if OpenGL
        if supports_opengl:
            if not hasattr(plugin, "vertex_shader_src") or not hasattr(plugin, "fragment_shader_src"):
                raise AttributeError("OpenGL plugin must define vertex_shader_src and fragment_shader_src")
            vert_path = os.path.join(plugin_dir, plugin.vertex_shader_src)
            frag_path = os.path.join(plugin_dir, plugin.fragment_shader_src)
            if not os.path.isfile(vert_path):
                raise FileNotFoundError(f"Missing vertex shader: {vert_path}")
            if not os.path.isfile(frag_path):
                raise FileNotFoundError(f"Missing fragment shader: {frag_path}")

        # Validate GUI inputs
        if not hasattr(plugin, "register_gui_inputs") or not isinstance(plugin.register_gui_inputs, dict):
            raise AttributeError("Plugin must define 'register_gui_inputs' as a dict")

        # CPU function optional but must exist if supports_cpu is set
        if supports_cpu and not hasattr(plugin, "apply_transform_cpu"):
            raise AttributeError("CPU plugin must implement apply_transform_cpu(img, **kwargs)")

        # Return wrapped module
        return PipelineEffectModule(
            name=plugin_name,
            plugin=plugin,
            base_path=plugin_dir
        )
