def rgb01_to_rgb255(rgb):
    # Function to convert RBG color from 0-1 scale to 0-255 scale
    return tuple(int(c * 255) for c in rgb)
# Example usage:
# rgb01_to_255(list(set_fill_color)[0])


def rgb255_to_hex(rgb255):
    # Function to convert RGB color from 0-255 scale to hexadecimal string
    return '{:02X}{:02X}{:02X}'.format(*rgb255)
# Example usage:
# rgb255 = (0, 102, 33)
# rgb255_to_hex(rgb255)  # Output: 006621


def hex_to_rgb255(hex_color):
    # Function to convert hexadecimal color string to RGB tuple in 0-255 scale
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
# Example usage:
# hex_color = "006621"
# print(hex_to_rgb(hex_color))  # Output: (0, 102, 33)


def rgb255_to_rgb01(rgb255):
    # Function to convert RGB from 0-255 scale to 0-1 scale
    return tuple(c / 255 for c in rgb255)
# Example usage:
# rgb255 = (0, 102, 33)
# print(rgb255_to_rgb01(rgb255))  # Output: (0.0, 0.4, 0.12941176470588237)


def decimal_to_rgb255(color_decimal):
    # Convert color in decimal to RGB tuple
    blue = color_decimal & 255
    green = (color_decimal >> 8) & 255
    red = (color_decimal >> 16) & 255
    return (red, green, blue)
# Example usage:
# decimal_color = 32768
# print(decimal_to_rgb255(decimal_color))


def rgb255_to_decimal(rgb255):
    # Convert RGB tuple to decimal color
    red, green, blue = rgb255
    return (red << 16) + (green << 8) + blue
# Example usage:
# rgb255 = (0, 102, 33)
# print(rgb255_to_decimal(rgb255))
# Output: 26145


def rgb01_to_decimal(rgb01):
    # Convert RGB tuple in 0-1 scale to decimal color
    rgb255 = rgb01_to_rgb255(rgb01)
    return rgb255_to_decimal(rgb255)
# Example usage:
# rgb01 = (0, 0.4, 0.12941176470588237)
# print(rgb01_to_decimal(rgb01))


def print_rgb_background(text, r, g, b):
    """Prints text with a custom RGB background color."""
    # ANSI escape code for 24-bit RGB background color
    # \033[48;2;R;G;Bm sets the background color
    # \033[0m resets all formatting
    print(f"\033[48;2;{r};{g};{b}m{text}\033[0m")

# Example usage:
# print_rgb_background("Hello, RGB Background!", 255, 0, 0)  # Red
