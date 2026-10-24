import math

def hex_to_rgb(hex_code: str):
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c*2 for c in hex_code])
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def relative_luminance(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def contrast_ratio(hex1: str, hex2: str) -> float:
    lum1 = relative_luminance(hex_to_rgb(hex1))
    lum2 = relative_luminance(hex_to_rgb(hex2))
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)

for c in ["#475569", "#64748B", "#94A3B8", "#78889B"]:
    print(c, "on #1E293B:", contrast_ratio(c, "#1E293B"))
    print(c, "on #0B0F19:", contrast_ratio(c, "#0B0F19"))
