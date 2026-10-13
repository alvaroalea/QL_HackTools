#!/usr/bin/env python3
"""
Convierte una imagen a un volcado de pantalla Sinclair QL (.scr).

Formatos:
  256x256  -> MODE 8, 8 colores, 32768 bytes
  512x256  -> MODE 4, 4 colores, 32768 bytes

Dependencia:
  python3 -m pip install Pillow

Uso:
  python3 png2qlscr.py imagen.png salida.scr
  python3 png2qlscr.py imagen.png              # genera imagen.scr

La imagen debe tener exactamente uno de los tamaños admitidos. Los colores
se ajustan a la paleta fija del QL mediante distancia RGB; no se guarda
ninguna cabecera en el .scr.
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "Falta Pillow. Instálalo con: python3 -m pip install Pillow"
    )

WIDTH_MODE8 = 256
WIDTH_MODE4 = 512
HEIGHT = 256
SCREEN_BYTES = 32768

# Colores QL en el orden de sus códigos: 0 negro, 1 azul, 2 rojo,
# 3 magenta, 4 verde, 5 cian, 6 amarillo, 7 blanco.
QL_PALETTE = [
    (0, 0, 0),        # 0 negro
    (0, 0, 255),      # 1 azul
    (255, 0, 0),      # 2 rojo
    (255, 0, 255),    # 3 magenta
    (0, 255, 0),      # 4 verde
    (0, 255, 255),    # 5 cian
    (255, 255, 0),    # 6 amarillo
    (255, 255, 255),  # 7 blanco
]

# En MODE 4 solo se dispone de los componentes R y G:
# negro, rojo, verde y amarillo.
MODE4_CODES = (0, 2, 4, 6)


def nearest_color(rgb, allowed_codes):
    """Devuelve el código de color QL más cercano en distancia RGB."""
    r, g, b = rgb
    return min(
        allowed_codes,
        key=lambda code: (
            (r - QL_PALETTE[code][0]) ** 2
            + (g - QL_PALETTE[code][1]) ** 2
            + (b - QL_PALETTE[code][2]) ** 2
        ),
    )


def image_to_codes(image, allowed_codes):
    """Convierte la imagen RGB en una matriz plana de códigos de color QL."""
    rgb_image = image.convert("RGB")
    return [
        nearest_color(rgb_image.getpixel((x, y)), allowed_codes)
        for y in range(rgb_image.height)
        for x in range(rgb_image.width)
    ]


def encode_mode4(codes):
    """
    MODE 4: 512x256, 4 colores, 2 bits por píxel.

    Cada grupo de 8 píxeles ocupa dos bytes:
      byte 1: un bit G por píxel, de izquierda a derecha (bit 7 a bit 0)
      byte 2: un bit R por píxel, de izquierda a derecha (bit 7 a bit 0)

    En los códigos de color QL, R corresponde al bit 1 y G al bit 2.
    """
    out = bytearray()
    width = WIDTH_MODE4

    for y in range(HEIGHT):
        row = codes[y * width:(y + 1) * width]
        for x in range(0, width, 8):
            green_byte = 0
            red_byte = 0
            for i, code in enumerate(row[x:x + 8]):
                bit = 7 - i
                if code & 4:       # componente verde
                    green_byte |= 1 << bit
                if code & 2:       # componente rojo
                    red_byte |= 1 << bit
            out.append(green_byte)
            out.append(red_byte)

    return bytes(out)


def encode_mode8(codes):
    """
    MODE 8: 256x256, 8 colores.

    Cada grupo de 4 píxeles ocupa dos bytes. Para cada píxel se guardan
    dos bits intercalados por byte:
      byte 1: G,F,G,F,G,F,G,F (F=flash, siempre 0)
      byte 2: R,B,R,B,R,B,R,B

    Los píxeles se codifican de izquierda a derecha, usando primero los
    bits más significativos. La salida ocupa 32768 bytes.
    """
    out = bytearray()
    width = WIDTH_MODE8

    for y in range(HEIGHT):
        row = codes[y * width:(y + 1) * width]
        for x in range(0, width, 4):
            green_flash_byte = 0
            red_blue_byte = 0

            for i, code in enumerate(row[x:x + 4]):
                green_bit = 7 - 2 * i
                flash_bit = 6 - 2 * i
                red_bit = 7 - 2 * i
                blue_bit = 6 - 2 * i

                if code & 4:  # G
                    green_flash_byte |= 1 << green_bit
                # Flash desactivado: flash_bit queda a cero.
                if code & 2:  # R
                    red_blue_byte |= 1 << red_bit
                if code & 1:  # B
                    red_blue_byte |= 1 << blue_bit

            out.append(green_flash_byte)
            out.append(red_blue_byte)

    return bytes(out)


def convert(input_path, output_path):
    try:
        with Image.open(input_path) as source:
            source.load()
            image = source.convert("RGB")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"No se puede abrir la imagen: {exc}")

    size = image.size
    if size == (WIDTH_MODE8, HEIGHT):
        mode = 8
        allowed = tuple(range(8))
        encoder = encode_mode8
    elif size == (WIDTH_MODE4, HEIGHT):
        mode = 4
        allowed = MODE4_CODES
        encoder = encode_mode4
    else:
        raise SystemExit(
            f"Tamaño no válido: {size[0]}x{size[1]}. "
            "Se requiere 256x256 (MODE 8) o 512x256 (MODE 4)."
        )

    codes = image_to_codes(image, allowed)
    data = encoder(codes)

    if len(data) != SCREEN_BYTES:
        raise SystemExit(
            f"Error interno: se generaron {len(data)} bytes; "
            f"se esperaban {SCREEN_BYTES}."
        )

    output_path = Path(output_path)
    try:
        output_path.write_bytes(data)
    except OSError as exc:
        raise SystemExit(f"No se puede escribir el archivo: {exc}")

    used = sorted(set(codes))
    print(f"Entrada:  {input_path}")
    print(f"Modo QL:  MODE {mode}")
    print(f"Tamaño:   {image.width}x{image.height}")
    print(f"Colores:  {len(used)} usados (códigos QL: {', '.join(map(str, used))})")
    print(f"Salida:   {output_path} ({len(data)} bytes, sin cabecera)")


def main():
    parser = argparse.ArgumentParser(
        description="Convierte una imagen a un volcado de pantalla Sinclair QL .scr."
    )
    parser.add_argument("entrada", help="Imagen de entrada compatible con Pillow")
    parser.add_argument(
        "salida",
        nargs="?",
        help="Archivo .scr de salida (por defecto, mismo nombre que la entrada)",
    )
    args = parser.parse_args()

    input_path = Path(args.entrada)
    output_path = Path(args.salida) if args.salida else input_path.with_suffix(".scr")
    convert(input_path, output_path)


if __name__ == "__main__":
    main()
