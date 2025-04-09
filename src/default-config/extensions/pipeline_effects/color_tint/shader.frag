#version 330 core

in vec2 vTex;
out vec4 FragColor;

uniform sampler2D texture1;
uniform vec3 color;       // RGB [0.0 - 1.0]
uniform float intensity;  // 0.0 - 1.0
uniform int mode;         // 0 = RGB, 1 = Brightness, 2 = Saturation, 3 = Hue

vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));

    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
    vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return c.z * mix(vec3(1.0), rgb, c.y);
}

void main() {
    vec4 tex = texture(texture1, vTex);
    vec3 result;


    if (mode == 0) {  // RGB blend
        result = mix(tex.rgb, color, intensity);
    } else if (mode == 1) {  // Brightness
        vec3 hsv = rgb2hsv(tex.rgb);
        float brightness = dot(color, vec3(0.114, 0.587, 0.299)); // match CPU
        hsv.z = mix(hsv.z, brightness, intensity);
        result = hsv2rgb(hsv);
    } else if (mode == 2) {  // Saturation
        vec3 hsv = rgb2hsv(tex.rgb);
        hsv.y = mix(hsv.y, 1.0, intensity);  // fully saturated
        result = hsv2rgb(hsv);
    } else if (mode == 3) {  // Hue shift
        vec3 hsv = rgb2hsv(tex.rgb);
        float target_hue = rgb2hsv(color).x;
        hsv.x = mix(hsv.x, target_hue, intensity);
        result = hsv2rgb(hsv);
    } else {  // Unknown mode — GREEN output
        result = vec3(0.0, 1.0, 0.0);
    }

    FragColor = vec4(result, tex.a);
}
