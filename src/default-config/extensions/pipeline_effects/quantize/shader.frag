#version 330 core
in vec2 vTex;
out vec4 FragColor;

uniform sampler2D texture1;
uniform int levels;

void main() {
    vec4 color = texture(texture1, vTex);

    // Convert [0.0, 1.0] to [0, 255]
    vec3 color255 = floor(color.rgb * 255.0);

    // Apply posterization logic
    int factor = 256 / levels;
    color255 = floor(color255 / float(factor)) * float(factor);

    // Back to [0.0, 1.0]
    vec3 result = color255 / 255.0;

    FragColor = vec4(result, 1.0);
}
