def rgb01_to_rgb255(rgb):
    return tuple(int(c * 255) for c in rgb)


def rgb_to_255(rgb):
    return rgb01_to_rgb255(rgb)


def rgb255_to_hex(rgb255):
    return '{:02X}{:02X}{:02X}'.format(*rgb255)


def hex_to_rgb255(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb255_to_rgb01(rgb255):
    return tuple(c / 255 for c in rgb255)


def decimal_to_rgb255(color_decimal):
    blue = color_decimal & 255
    green = (color_decimal >> 8) & 255
    red = (color_decimal >> 16) & 255
    return (red, green, blue)


def rgb255_to_decimal(rgb255):
    red, green, blue = rgb255
    return (red << 16) + (green << 8) + blue


def rgb01_to_decimal(rgb01):
    rgb255 = rgb01_to_rgb255(rgb01)
    return rgb255_to_decimal(rgb255)


def print_rgb_background(text, r, g, b):
    print(f"\033[48;2;{r};{g};{b}m{text}\033[0m")
