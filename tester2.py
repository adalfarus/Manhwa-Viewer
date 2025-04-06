from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QScrollArea, QFileDialog
)
from PySide6.QtGui import QImage, QPixmap, QOpenGLContext
from PySide6.QtCore import Qt
from PySide6.QtGui import QOffscreenSurface, QSurfaceFormat
from OpenGL.GL import *
import sys
import numpy as np


VERT_SRC = """
#version 330 core
layout(location = 0) in vec2 pos;
layout(location = 1) in vec2 tex;
out vec2 vTex;
void main() {
    vTex = tex;
    gl_Position = vec4(pos, 0.0, 1.0);
}
"""

FRAG_SRC = """
#version 330 core
in vec2 vTex;
out vec4 FragColor;
uniform sampler2D texture1;
void main() {
    vec4 color = texture(texture1, vec2(vTex.x, 1.0 - vTex.y)); // flip vertically
    float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    FragColor = vec4(vec3(gray), 1.0);
}
"""


def build_shader_program():
    def compile_shader(src, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, src)
        glCompileShader(shader)
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        return shader

    program = glCreateProgram()
    vs = compile_shader(VERT_SRC, GL_VERTEX_SHADER)
    fs = compile_shader(FRAG_SRC, GL_FRAGMENT_SHADER)
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)
    return program


def apply_shader_to_image(qimage: QImage) -> QImage:
    width, height = qimage.width(), qimage.height()

    # Setup offscreen surface and context
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

    context = QOpenGLContext()
    context.setFormat(fmt)
    context.create()

    surface = QOffscreenSurface()
    surface.setFormat(fmt)
    surface.create()

    context.makeCurrent(surface)

    # Convert image to RGBA
    image = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    img_data = image.bits().tobytes()

    # Setup FBO
    fbo_tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, fbo_tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, fbo_tex, 0)

    glViewport(0, 0, width, height)
    glClearColor(0, 0, 0, 1)
    glClear(GL_COLOR_BUFFER_BIT)

    # Upload source texture
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # Render quad
    program = build_shader_program()
    glUseProgram(program)

    verts = np.array([
        -1, -1, 0, 0,
         1, -1, 1, 0,
        -1,  1, 0, 1,
         1,  1, 1, 1
    ], dtype=np.float32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, False, 16, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, False, 16, ctypes.c_void_p(8))

    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Read pixels back into QImage
    buffer = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
    result = QImage(buffer, width, height, QImage.Format.Format_RGBA8888)
    result = result.mirrored(False, True)

    # Cleanup
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])
    glDeleteTextures([tex, fbo_tex])
    glDeleteFramebuffers(1, [fbo])
    glDeleteProgram(program)

    context.doneCurrent()
    return result


class ShaderImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GL Shader Image Viewer")

        self.viewer = QLabel()
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.viewer)

        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)

        apply_btn = QPushButton("Apply Shader")
        apply_btn.clicked.connect(self.apply_shader)

        layout = QVBoxLayout()
        layout.addWidget(scroll)
        layout.addWidget(load_btn)
        layout.addWidget(apply_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.original_image = None

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image")
        if path:
            self.original_image = QImage(path)
            self.viewer.setPixmap(QPixmap.fromImage(self.original_image))

    def apply_shader(self):
        if self.original_image:
            result = apply_shader_to_image(self.original_image)
            self.viewer.setPixmap(QPixmap.fromImage(result))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShaderImageViewer()
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec())
