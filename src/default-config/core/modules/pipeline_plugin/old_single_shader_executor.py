import os
import numpy as np
from PySide6.QtGui import QImage, QOpenGLContext, QSurfaceFormat
from PySide6.QtGui import QOffscreenSurface
from OpenGL.GL import *

import collections.abc as _a
import typing as _ty
import types as _ts


class ShaderCache:
    def __init__(self):
        self._cache: dict[tuple[str, str], int] = {}

    def load_shader_program(self, vert_path: str, frag_path: str) -> int:
        key = (vert_path, frag_path)
        if key in self._cache:
            return self._cache[key]

        with open(vert_path, "r") as vf, open(frag_path, "r") as ff:
            vert_src = vf.read()
            frag_src = ff.read()

        program = self._compile_program(vert_src, frag_src)
        self._cache[key] = program
        return program

    def _compile_program(self, vertex_src: str, fragment_src: str) -> int:
        def compile_shader(src: str, shader_type: int) -> int:
            shader = glCreateShader(shader_type)
            glShaderSource(shader, src)
            glCompileShader(shader)
            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader).decode())
            return shader

        vs = compile_shader(vertex_src, GL_VERTEX_SHADER)
        fs = compile_shader(fragment_src, GL_FRAGMENT_SHADER)
        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        if not glGetProgramiv(program, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(program).decode())

        glDeleteShader(vs)
        glDeleteShader(fs)
        return program


# GLOBAL SHADER CACHE
shader_cache = None  # will be initialized on first use


def run_opengl_pipeline_batch(
    image_files: list[str],
    input_folder: str,
    cache_folder: str,
    pipeline: list[tuple],
    progress_signal: _ty.Callable[[int], None] | None = None
):
    global shader_cache
    shader_cache = ShaderCache()
    if shader_cache is None:
        shader_cache = ShaderCache()

    surface_format = QSurfaceFormat()
    surface_format.setVersion(3, 3)
    surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

    context = QOpenGLContext()
    context.setFormat(surface_format)
    context.create()

    surface = QOffscreenSurface()
    surface.setFormat(surface_format)
    surface.create()

    context.makeCurrent(surface)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    verts = np.array([
        -1, -1, 0, 0,
         1, -1, 1, 0,
        -1,  1, 0, 1,
         1,  1, 1, 1
    ], dtype=np.float32)
    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, False, 16, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, False, 16, ctypes.c_void_p(8))

    for i, filename in enumerate(image_files):
        try:
            path = os.path.join(input_folder, filename)
            img = QImage(path).convertToFormat(QImage.Format.Format_RGBA8888)
            if img.isNull():
                continue

            width, height = img.width(), img.height()
            img_data = img.bits().tobytes()

            tex_in = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_in)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            tex_out = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_out)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            fbo = glGenFramebuffers(1)
            glBindFramebuffer(GL_FRAMEBUFFER, fbo)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex_out, 0)

            glViewport(0, 0, width, height)

            active_texture = tex_in
            for module, settings in pipeline:
                program = shader_cache.load_shader_program(module.shader_paths["vert"], module.shader_paths["frag"])
                glUseProgram(program)

                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, active_texture)
                glUniform1i(glGetUniformLocation(program, "texture1"), 0)

                for name, val in settings.items():
                    loc = glGetUniformLocation(program, name)
                    if loc == -1:
                        continue
                    if isinstance(val, float):
                        glUniform1f(loc, val)
                    elif isinstance(val, int):
                        glUniform1i(loc, val)
                    elif isinstance(val, tuple):
                        if len(val) == 2:
                            glUniform2f(loc, *val)
                        elif len(val) == 3:
                            glUniform3f(loc, *val)

                glBindFramebuffer(GL_FRAMEBUFFER, fbo)
                glClearColor(0, 0, 0, 1)
                glClear(GL_COLOR_BUFFER_BIT)
                glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

                active_texture = tex_out  # Output becomes next input

            # Read result
            result_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
            result_img = QImage(result_data, width, height, QImage.Format_RGBA8888).mirrored(False, True)
            result_img.save(os.path.join(cache_folder, filename))

            glDeleteTextures([tex_in, tex_out])
            glDeleteFramebuffers(1, [fbo])

            if progress_signal:
                progress_signal.emit(int(100 * (i + 1) / len(image_files)))
            yield
        except Exception as e:
            print(f"[OpenGL Error] Failed to process {filename}: {e}")
            yield

    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])
    context.doneCurrent()
    yield True
