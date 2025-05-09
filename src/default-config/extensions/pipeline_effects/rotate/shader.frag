#version 330 core
uniform sampler2D texture1;
uniform int mode;

in vec2 vTex;
out vec4 FragColor;

vec3 rgb2hsv(vec3 c) {
    float cmax = max(max(c.r, c.g), c.b);
    float cmin = min(min(c.r, c.g), c.b);
    float diff = cmax - cmin;

    float h = 0.0;
    if (diff == 0.0) h = 0.0;
    else if (cmax == c.r) h = mod((60.0 * ((c.g - c.b) / diff) + 360.0), 360.0);
    else if (cmax == c.g) h = mod((60.0 * ((c.b - c.r) / diff) + 120.0), 360.0);
    else if (cmax == c.b) h = mod((60.0 * ((c.r - c.g) / diff) + 240.0), 360.0);

    float s = (cmax == 0.0) ? 0.0 : diff / cmax;
    float v = cmax;

    return vec3(h / 360.0, s, v);
}

vec3 hsv2rgb(vec3 c) {
    float h = c.x * 6.0;
    float s = c.y;
    float v = c.z;

    int i = int(h);
    float f = h - float(i);
    float p = v * (1.0 - s);
    float q = v * (1.0 - s * f);
    float t = v * (1.0 - s * (1.0 - f));

    if (i == 0) return vec3(v, t, p);
    else if (i == 1) return vec3(q, v, p);
    else if (i == 2) return vec3(p, v, t);
    else if (i == 3) return vec3(p, q, v);
    else if (i == 4) return vec3(t, p, v);
    else return vec3(v, p, q);
}

void main() {
    vec4 color = texture(texture1, vTex); // texture(texture1, vec2(vTex.x, 1.0 - vTex.y))
    vec3 result = color.rgb;

    if (mode == 0) {  // RGB channel rotate: G, B, R > R, G, B
        result = vec3(color.b, color.r, color.g);
    }
    else if (mode == 1) {  // Hue invert
        vec3 hsv = rgb2hsv(result);
        hsv.x = mod(hsv.x + 0.5 * (1.0 / 180.0) * 90.0, 1.0);  // +90 cv2s degrees in GLSL units
        result = hsv2rgb(hsv);
    } else {  // Unknown mode — GREEN output
        result = vec3(0.0, 1.0, 0.0);
    }

    FragColor = vec4(result, color.a);
}
