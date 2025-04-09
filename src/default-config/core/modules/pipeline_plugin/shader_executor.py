import concurrent
import os
import numpy as np
from PySide6.QtGui import QImage, QOpenGLContext, QSurfaceFormat, QOffscreenSurface
from OpenGL.GL import *
from .loader import PipelineEffectModule

import ctypes
import collections.abc as _a
import typing as _ty

from aplustools.package.timid import TimidTimer


class PersistentGLContext:
    def __init__(self):
        self.surface_format = QSurfaceFormat()
        self.surface_format.setVersion(3, 3)
        self.surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

        self.context = QOpenGLContext()
        self.context.setFormat(self.surface_format)
        self.context.create()

        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.surface_format)
        self.surface.create()

        self._valid = self.surface.isValid() and self.context.isValid()
        if self._valid:
            self.context.makeCurrent(self.surface)
            self._init_vao_vbo()

    def _init_vao_vbo(self):
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        verts = np.array([
            -1, -1, 0, 0,
             1, -1, 1, 0,
            -1,  1, 0, 1,
             1,  1, 1, 1
        ], dtype=np.float32)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, False, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, 16, ctypes.c_void_p(8))

    def make_current(self):
        if not self._valid:
            print("[GLContext] Context or surface is no longer valid, reinitializing.")
            self.__init__()  # Dangerous but effective quick fix
        else:
            print(self.surface.isValid(), self.context.isValid())
            self.context.makeCurrent(self.surface)

    def cleanup(self):
        print("CLEANUP")
        glDeleteBuffers(1, [self.vbo])
        glDeleteVertexArrays(1, [self.vao])
        self.context.doneCurrent()


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


_shared_gl_context = None
_shader_cache = None
_flip_shader_module = PipelineEffectModule(
    "flip_shader",
    type("flip_shader", (), {  # type: ignore
        "effect_name": "Flip Shader",
        "effect_name_format": "Flip Shader",
        "effect_id": "flip_shader",
        "supports_cpu": False,
        "supports_opengl": True,
        "register_gui_inputs": {},
        "vertex_shader_src": "./flip_shader.vert",
        "fragment_shader_src": "./flip_shader.frag",
        "update_gui": lambda _: None,
        "apply_transform_cpu": None
    }),
    os.path.dirname(__file__)
)


def get_shared_gl_context():
    global _shared_gl_context
    if _shared_gl_context is None:
        _shared_gl_context = PersistentGLContext()
    return _shared_gl_context


def get_shared_gl_context(force_new=False):
    global _shared_gl_context, _shader_cache
    if force_new or _shared_gl_context is None:
        _shared_gl_context = PersistentGLContext()
        _shader_cache = ShaderCache()  # <- force clear!
    return _shared_gl_context


def get_shader_cache():
    global _shader_cache
    if _shader_cache is None:
        _shader_cache = ShaderCache()
    return _shader_cache


def run_opengl_pipeline_batch(
    image_files: list[str],
    input_folder: str,
    cache_folder: str,
    pipeline: list[tuple],
    progress_signal: _ty.Callable[[int], None] | None = None
):
    # 0.15 sec
    pipeline.append((_flip_shader_module, {}))
    shared_gl_context = get_shared_gl_context(force_new=True)
    shared_gl_context.make_current()
    shader_cache = get_shader_cache()

    images = []
    textures = []
    all_textures = []

    glBindVertexArray(shared_gl_context.vao)  # Bind VAO once before draw

    # Upload all images (0.6 sec)
    for filename in image_files:
        path = os.path.join(input_folder, filename)
        qimg = QImage(path).convertToFormat(QImage.Format_RGBA8888)
        if qimg.isNull():
            continue

        width, height = qimg.width(), qimg.height()
        img_data = qimg.bits().tobytes()

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        images.append((filename, width, height))
        textures.append(tex)
        all_textures.append(tex)

    # Apply shaders
    processed = []  # 0.6 sec
    for idx, ((filename, width, height), tex_in) in enumerate(zip(images, textures)):
        tex_ping = tex_in
        tex_pong = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_pong)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        all_textures.append(tex_pong)

        read_tex = tex_ping
        write_tex = tex_pong

        fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        for step_idx, (module, settings) in enumerate(pipeline):
            module: PipelineEffectModule
            program = shader_cache.load_shader_program(module.shader_paths["vert"], module.shader_paths["frag"])
            glUseProgram(program)

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, read_tex)
            glUniform1i(glGetUniformLocation(program, "texture1"), 0)

            # Send settings
            preprocessing_funcs = module.get_preprocessing_funcs()
            gl_types = module.get_gl_types()
            for name, val in settings.items():
                loc = glGetUniformLocation(program, name)
                if loc == -1:
                    print(f"[SHADER WARNING] Could not get location of uniform {name}, maybe you didn't define it?")
                    continue

                preprocessing_func = preprocessing_funcs[name]
                val = preprocessing_func(val)

                gl_type: str = gl_types.get(name, "Unknown")

                try:
                    if gl_type == "int":
                        glUniform1i(loc, int(val))
                    elif gl_type == "float":
                        glUniform1f(loc, float(val))
                    elif gl_type == "vec2":
                        glUniform2f(loc, *val)
                    elif gl_type == "vec3":
                        glUniform3f(loc, *val)
                    elif gl_type == "vec4":
                        glUniform4f(loc, *val)
                    elif gl_type == "ivec2":
                        glUniform2i(loc, *val)
                    elif gl_type == "ivec3":
                        glUniform3i(loc, *val)
                    elif gl_type == "ivec4":
                        glUniform4i(loc, *val)
                    elif gl_type == "mat2":
                        glUniformMatrix2fv(loc, 1, False, val)
                    elif gl_type == "mat3":
                        glUniformMatrix3fv(loc, 1, False, val)
                    elif gl_type == "mat4":
                        glUniformMatrix4fv(loc, 1, False, val)
                    elif gl_type == "sampler1D":
                        glActiveTexture(GL_TEXTURE0 + 1)
                        glBindTexture(GL_TEXTURE_1D, val)
                        glUniform1i(loc, 1)
                    elif gl_type == "sampler2D":
                        glActiveTexture(GL_TEXTURE0 + 1)
                        glBindTexture(GL_TEXTURE_2D, val)
                        glUniform1i(loc, 1)
                    elif gl_type == "sampler3D":
                        glActiveTexture(GL_TEXTURE0 + 1)
                        glBindTexture(GL_TEXTURE_3D, val)
                        glUniform1i(loc, 1)
                    elif gl_type == "sampler2DArray":
                        glActiveTexture(GL_TEXTURE0 + 1)
                        glBindTexture(GL_TEXTURE_2D_ARRAY, val)
                        glUniform1i(loc, 1)
                    elif gl_type == "samplerCube":
                        glActiveTexture(GL_TEXTURE0 + 1)
                        glBindTexture(GL_TEXTURE_CUBE_MAP, val)
                        glUniform1i(loc, 1)
                    else:
                        print(f"[SHADER WARNING] Unsupported GL type '{gl_type}' for uniform '{name}'")

                except Exception as e:
                    print(f"[SHADER ERROR] Failed to send uniform '{name}' of type '{gl_type}': {e}")

            # Bind framebuffer
            glBindFramebuffer(GL_FRAMEBUFFER, fbo)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, write_tex, 0)

            # Check framebuffer completeness
            if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
                print("[OpenGL Error] Framebuffer not complete!")
                continue

            glViewport(0, 0, width, height)
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

            # Swap
            read_tex, write_tex = write_tex, read_tex

        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, read_tex, 0)
        glReadBuffer(GL_COLOR_ATTACHMENT0)
        result = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
        qresult = QImage(result, width, height, QImage.Format_RGBA8888).mirrored(False, True)
        processed.append((filename, qresult))

        glDeleteTextures([tex_pong])
        glDeleteFramebuffers(1, [fbo])

        if progress_signal:
            progress_signal.emit(int(100 * (idx + 1) / len(images)))
        yield

    glDeleteTextures(all_textures)

    start = TimidTimer()
    # Fast saving with cv2? Need to try out
    # import cv2

    def save_image(args):
        filename, qimg = args
        qimg.save(os.path.join(cache_folder, filename))
        # path = os.path.join(cache_folder, filename)
        # width, height = qimg.width(), qimg.height()
        # ptr = qimg.bits()
        # ptr.setsize(qimg.byteCount())
        # arr = np.array(ptr).reshape((height, width, 4))
        # cv2.imwrite(path, cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(save_image, processed)

    # for filename, qimg in processed:  # 5.3 seconds
    #     qimg.save(os.path.join(cache_folder, filename))
    print("Image saving done", start.end())

    yield True
