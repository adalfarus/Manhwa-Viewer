#version 330 core
layout(location = 0) in vec2 pos;
layout(location = 1) in vec2 tex;
out vec2 vTex;
void main() {
    vTex = vec2(tex.x, 1.0 - tex.y);  // Flip happens here
    gl_Position = vec4(pos, 0.0, 1.0);
}
