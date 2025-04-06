from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QSurfaceFormat, QImage
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import *
from PySide6.QtOpenGL import *
from OpenGL.GL import *  # This gives you glClearColor, glDrawArrays, etc.
import sys
import numpy as np


vertex_shader_src = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texCoords;
out vec2 vTexCoords;
void main() {
    vTexCoords = texCoords;
    gl_Position = vec4(position, 0.0, 1.0);
}
"""

fragment_shader_src = """
#version 330 core
in vec2 vTexCoords;
out vec4 FragColor;
uniform sampler2D texture1;

void main() {
    vec4 color = texture(texture1, vec2(vTexCoords.x, 1.0 - vTexCoords.y));
    float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    FragColor = vec4(vec3(gray), 1.0); // grayscale output
}
"""


class GLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.texture_id = None
        self.program = None

    def initializeGL(self):
        self.makeCurrent()
        glClearColor(0.1, 0.1, 0.1, 1.0)

        # Compile shader
        self.program = glCreateProgram()
        self._add_shader(vertex_shader_src, GL_VERTEX_SHADER)
        self._add_shader(fragment_shader_src, GL_FRAGMENT_SHADER)
        glLinkProgram(self.program)
        glUseProgram(self.program)

        # Setup geometry
        quad_vertices = np.array([
            -1, -1,  0, 0,
             1, -1,  1, 0,
            -1,  1,  0, 1,
             1,  1,  1, 1
        ], dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, quad_vertices.nbytes, quad_vertices, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(8))

        # Load texture
        self.texture_id = self._load_texture("example.jpg")  # Replace with your image path

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.program)
        glBindVertexArray(self.vao)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    def _add_shader(self, source, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        glAttachShader(self.program, shader)

    def _load_texture(self, path):
        image = QImage(path)
        image = image.convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = image.width(), image.height()

        ptr = image.bits()
        data = ptr[: width * height * 4]  # Slice the memoryview directly

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return tex


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenGL Shader Example")
        self.setGeometry(100, 100, 800, 600)
        self.gl_widget = GLWidget()
        self.setCentralWidget(self.gl_widget)


if __name__ == "__main__":
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
