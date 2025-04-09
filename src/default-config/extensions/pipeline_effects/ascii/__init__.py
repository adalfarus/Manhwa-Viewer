"""TBA"""
import os

from PySide6.QtWidgets import QWidget, QCheckBox, QComboBox

from modules.pipeline_plugin.gui import Input, KeyboardInput, Combobox, NoGui, Checkbox, Widget
from modules.pipeline_plugin.types import glUniform1i, glTexture2D
import cv2
import numpy as np

import collections.abc as _a
import typing as _ty
import types as _ts


effect_name: str = "Stylize: Convert to ASCII"
effect_name_format: str = "{mode} ASCII Mask"
effect_id: str = "ascii"

supports_opengl: bool = True
supports_cpu: bool = True
vertex_shader_src: str = "shader.vert"
fragment_shader_src: str = "shader.frag"

# === Config ===
GLYPH_SIZE = 7
FONT_ATLAS_SIZE = 112  # 112x112
GLYPH_COUNT_PER_ROW = round(FONT_ATLAS_SIZE / GLYPH_SIZE)
GLYPH_ATLAS_PATH = os.path.join(os.path.dirname(__file__), "atlas.png")
ASCII_TEXTURE_ATLAS = None  # type: np.ndarray | None
ASCII_GLYPH_LOOKUP = ""     # type: str

def is_ascii(x: str) -> str:
    """Valid, readable ascii or ß"""
    return "".join([c for c in x if 31 < ord(c) < 129 or c == 223])

def string_to_texture(glyphs: str) -> int:
    """Preprocess glyph string into a usable lookup texture"""
    global ASCII_TEXTURE_ATLAS, ASCII_GLYPH_LOOKUP

    if not glyphs:
        return 0

    # Load pre-made atlas
    atlas = cv2.imread(GLYPH_ATLAS_PATH, cv2.IMREAD_GRAYSCALE)
    if atlas is None or atlas.shape != (FONT_ATLAS_SIZE, FONT_ATLAS_SIZE):
        print("[Error] Font atlas missing or incorrect size")
        return 0

    glyph_textures = []
    for ch in glyphs:
        ascii_code = ord(ch)
        row = (ascii_code // GLYPH_COUNT_PER_ROW) - 1
        col = ascii_code % GLYPH_COUNT_PER_ROW

        x0 = col * GLYPH_SIZE
        y0 = row * GLYPH_SIZE

        glyph_crop = atlas[y0:y0 + GLYPH_SIZE, x0:x0 + GLYPH_SIZE]
        glyph_textures.append(glyph_crop)

    # Store in global
    ASCII_TEXTURE_ATLAS = np.hstack(glyph_textures)
    ASCII_GLYPH_LOOKUP = glyphs
    # save_path = os.path.join(os.path.dirname(__file__), "texture_flat.png")  # Debug
    # cv2.imwrite(save_path, ASCII_TEXTURE_ATLAS)
    return len(glyphs)

def get_from_global_texture(_: np.ndarray | None) -> np.ndarray:
    """Return stacked glyph texture from global state"""
    global ASCII_TEXTURE_ATLAS
    return ASCII_TEXTURE_ATLAS if ASCII_TEXTURE_ATLAS is not None else np.zeros((1, 7, 7), dtype=np.uint8)


ASCII_MODES = {
    "B/W": 0,  # (black and white)
    "Luminance": 1,  # (use white as mask for original images
    "Color": 2  # (use white as mask for original image)
}

register_gui_inputs: dict[str, Input] = {
    "chars_length": Input("Characters", glUniform1i, KeyboardInput(False, "", is_ascii), default=" .:-=+*#", preprocessing_func=string_to_texture),
    "mode": Input("ASCII Mode", glUniform1i, Combobox(ASCII_MODES), default=1),
    "texture": Input("", glTexture2D, NoGui(), default=None, preprocessing_func=get_from_global_texture),  # As this is executed after writing the global texture
    "glyph_size": Input("", glUniform1i, NoGui(), default=-1, preprocessing_func=lambda _: GLYPH_SIZE),
    "subtract_glyphs": Input("", glUniform1i, Checkbox("Subtract Glyphs"), default=0),
    "sub_glyph_shading": Input("", glUniform1i, Checkbox("Sub-Glyph Shading"), default=0)
}

def _compute_luminance(tile):
    """Compute perceived brightness."""
    if len(tile.shape) == 3:
        return np.dot(tile[..., :3], [0.114, 0.587, 0.299])
    else:
        return tile.astype(np.float32)

def update_gui(gui_widgets: dict[str, QWidget | Widget]) -> None:
    """Called whenever the gui updates"""
    mode_combobox: QComboBox = gui_widgets["mode"]  # type: ignore
    sub_glyph_shading_checkbox: QCheckBox = gui_widgets["sub_glyph_shading"]  # type: ignore
    sub_glyph_shading_checkbox.setEnabled(mode_combobox.currentIndex() != 0)

def apply_transform_cpu(img: np.ndarray, chars_length: int, mode: int, texture: np.ndarray, glyph_size: int,
                        subtract_glyphs: _ty.Literal[0, 1], sub_glyph_shading: _ty.Literal[0, 1]) -> np.ndarray:
    """
    If chars length < 1, the preprocessing failed.
    """
    if chars_length < 1 or glyph_size <= 0 or texture.ndim != 2:
        return img  # error occurred

    # Invert texture for subtractive mode
    if subtract_glyphs:
        texture = 255 - texture

    h, w = img.shape[:2]
    rows = h // glyph_size
    cols = w // glyph_size

    # Step 1: Convert to luminance
    if img.ndim == 3 and img.shape[2] == 3:
        luminance = np.dot(img[..., :3], [0.114, 0.587, 0.299])
    else:
        luminance = img.copy()

    # Step 2: Quantize luminance to chars_length levels
    quantized = ((luminance / 255.0) * (chars_length - 1)).astype(np.uint8)

    # Step 3: Downscale to grid (1 value per glyph)
    downscaled = cv2.resize(quantized, (cols, rows), interpolation=cv2.INTER_AREA)

    # Prepare output
    base_value = 0 if not subtract_glyphs else 255
    output = np.full((rows * glyph_size, cols * glyph_size, 3), base_value, dtype=np.uint8)

    for y in range(rows):
        for x in range(cols):
            idx = int(downscaled[y, x])
            x0, y0 = x * glyph_size, y * glyph_size
            x1, y1 = x0 + glyph_size, y0 + glyph_size

            # Step 4: Retrieve the glyph slice from atlas texture
            glyph_start = idx * glyph_size
            glyph = texture[:, glyph_start:glyph_start + glyph_size]
            if glyph.ndim == 3:
                glyph = glyph[..., 0]
            glyph_mask = glyph.astype(np.float32) / 255.0
            if glyph_mask.shape != (glyph_size, glyph_size):
                continue

            # Step 5: Apply final effect based on mode
            if mode == 0:  # Black & white ASCII
                glyph_rgb = np.repeat(glyph[..., None], 3, axis=-1)
                output[y0:y1, x0:x1] = glyph_rgb
            elif mode == 1:  # Luminance mask
                if sub_glyph_shading:
                    tile = luminance[y0:y1, x0:x1]
                    if tile.shape != (glyph_size, glyph_size):
                        tile = cv2.resize(tile, (glyph_size, glyph_size), interpolation=cv2.INTER_AREA)
                    tile_rgb = np.repeat(tile[..., None], 3, axis=-1)
                    blended = tile_rgb * glyph_mask[..., None]
                else:
                    avg = np.mean(luminance[y0:y1, x0:x1])
                    blended = np.full((glyph_size, glyph_size, 3), avg, dtype=np.float32) * glyph_mask[..., None]

                output[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
            elif mode == 2:  # Color mask
                if sub_glyph_shading:
                    tile = img[y0:y1, x0:x1]
                    if tile.shape[:2] != (glyph_size, glyph_size):
                        tile = cv2.resize(tile, (glyph_size, glyph_size), interpolation=cv2.INTER_AREA)
                    result = tile.astype(np.float32) * glyph_mask[..., None]
                else:
                    avg_color = np.mean(img[y0:y1, x0:x1].reshape(-1, 3), axis=0)
                    result = np.full((glyph_size, glyph_size, 3), avg_color, dtype=np.float32) * glyph_mask[..., None]

                output[y0:y1, x0:x1] = np.clip(result, 0, 255).astype(np.uint8)

    return output
