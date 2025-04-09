#version 330 core

in vec2 vTex;
out vec4 FragColor;

uniform sampler2D glyph_atlas;  // Glyph strip (1 x glyph_size)
uniform int glyph_size;         // Width/height of each glyph (assumed square)
uniform int chars_length;       // Number of glyphs in atlas
uniform int mode;               // 0 = BW, 1 = Luminance mask, 2 = Color mask
uniform int subtract_glyphs;    // If enabled, subtract glyph instead of add

// Compute luminance
float getLuminance(vec3 color) {
    return dot(color, vec3(0.114, 0.587, 0.299));
}

void main() {
    vec2 texSize = vec2(textureSize(texture1, 0));
    vec2 pixelCoord = vTex * texSize;

    // Compute which cell we are in
    ivec2 cell = ivec2(pixelCoord) / glyph_size;
    ivec2 cellOrigin = cell * glyph_size;

    // Get center of cell for sampling
    vec2 sampleUV = (vec2(cellOrigin) + vec2(glyph_size) / 2.0) / texSize;

    // Sample original image and compute luminance
    vec3 base_color = texture(texture1, sampleUV).rgb;
    float luminance = getLuminance(base_color);

    // Convert luminance to glyph index
    int glyph_index = int(clamp(luminance * float(chars_length - 1), 0.0, float(chars_length - 1)));

    // Calculate glyph UV (atlas is horizontal strip)
    float atlasWidth = float(glyph_size * chars_length);
    float gx = float(glyph_index * glyph_size) + mod(pixelCoord.x, float(glyph_size));
    float gy = mod(pixelCoord.y, float(glyph_size));
    vec2 glyph_uv = vec2(gx / atlasWidth, gy / float(glyph_size));

    // Sample the glyph
    float glyph_sample = texture(glyph_atlas, glyph_uv).r;
    if (subtract_glyphs == 1) {
        glyph_sample = 1.0 - glyph_sample;
    }

    if (mode == 0) {
        // B/W ASCII
        FragColor = vec4(vec3(glyph_sample), 1.0);
    }
    else if (mode == 1) {
        // Luminance mask
        FragColor = vec4(vec3(luminance * glyph_sample), 1.0);
    }
    else if (mode == 2) {
        // Color mask
        FragColor = vec4(base_color * glyph_sample, 1.0);
    }
    else {
        // Unknown mode fallback (bright red)
        FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
}
