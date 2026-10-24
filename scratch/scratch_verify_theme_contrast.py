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

themes = {
    "Professional Light": {
        "pairs": [
            ("text_primary on surface", "#0F172A", "#FFFFFF", 4.5),
            ("text_secondary on surface", "#475569", "#FFFFFF", 4.5),
            ("text_primary on bg", "#0F172A", "#F8FAFC", 4.5),
            ("text_on_accent on accent", "#FFFFFF", "#B45309", 4.5),
            ("sidebar_text on sidebar_bg", "#94A3B8", "#0F172A", 4.5),
            ("sidebar_active_text on sidebar_active", "#FFFFFF", "#B45309", 4.5),
            ("success on surface", "#15803D", "#FFFFFF", 4.5),
            ("success on success_soft", "#15803D", "#DCFCE7", 4.5),
            ("warning on surface", "#B45309", "#FFFFFF", 4.5),
            ("warning on warning_soft", "#92400E", "#FEF3C7", 4.5),
            ("danger on surface", "#B91C1C", "#FFFFFF", 4.5),
            ("danger on danger_soft", "#B91C1C", "#FEE2E2", 4.5),
            ("info on surface", "#1D4ED8", "#FFFFFF", 4.5),
            ("info on info_soft", "#1D4ED8", "#DBEAFE", 4.5),
            ("table_header_text on table_header_bg", "#1E293B", "#F1F5F9", 4.5),
            ("border on surface (UI element)", "#CBD5E1", "#FFFFFF", 1.5)
        ]
    },
    "Professional Dark": {
        "pairs": [
            ("text_primary on surface", "#F8FAFC", "#1E293B", 4.5),
            ("text_secondary on surface", "#CBD5E1", "#1E293B", 4.5),
            ("text_primary on bg", "#F8FAFC", "#0B0F19", 4.5),
            ("text_on_accent on accent", "#0B0F19", "#F59E0B", 4.5),
            ("sidebar_text on sidebar_bg", "#CBD5E1", "#0B0F19", 4.5),
            ("sidebar_active_text on sidebar_active", "#0B0F19", "#F59E0B", 4.5),
            ("success on surface", "#4ADE80", "#1E293B", 4.5),
            ("success on success_soft", "#86EFAC", "#064E3B", 4.5),
            ("warning on surface", "#FBBF24", "#1E293B", 4.5),
            ("warning on warning_soft", "#FDE68A", "#451A03", 4.5),
            ("danger on surface", "#F87171", "#1E293B", 4.5),
            ("danger on danger_soft", "#FECACA", "#450A0A", 4.5),
            ("info on surface", "#60A5FA", "#1E293B", 4.5),
            ("info on info_soft", "#93C5FD", "#172554", 4.5),
            ("table_header_text on table_header_bg", "#F8FAFC", "#0F172A", 4.5),
        ]
    },
    "Classic Navy": {
        "pairs": [
            ("text_primary on surface", "#1B1B18", "#FBFBF9", 4.5),
            ("text_secondary on surface", "#4D473B", "#FBFBF9", 4.5),
            ("text_primary on bg", "#1B1B18", "#EAEAE4", 4.5),
            ("text_on_accent on accent", "#FFFFFF", "#2C3E63", 4.5),
            ("sidebar_text on sidebar_bg", "#DDE2EB", "#2C3E63", 4.5),
            ("sidebar_active_text on sidebar_active", "#FFFFFF", "#A6822E", 3.0),
            ("success on surface", "#1E5E36", "#FBFBF9", 4.5),
            ("success on success_soft", "#144A29", "#E3EDE5", 4.5),
            ("warning on surface", "#8D6510", "#FBFBF9", 4.5),
            ("warning on warning_soft", "#725008", "#F7F0DF", 4.5),
            ("danger on surface", "#8B1E2D", "#FBFBF9", 4.5),
            ("danger on danger_soft", "#721422", "#F9E8EB", 4.5),
            ("info on surface", "#1E4E79", "#FBFBF9", 4.5),
            ("info on info_soft", "#143C60", "#E6EFF7", 4.5),
            ("table_header_text on table_header_bg", "#1B1B18", "#F1F1EB", 4.5),
        ]
    }
}

all_passed = True
for theme_name, data in themes.items():
    print(f"Checking theme: {theme_name}")
    for desc, c1, c2, req in data["pairs"]:
        cr = contrast_ratio(c1, c2)
        passed = cr >= req
        if not passed:
            all_passed = False
            print(f"  [FAIL] {desc}: {cr:.2f}:1 (Required: {req}:1) [{c1} vs {c2}]")
        else:
            print(f"  [PASS] {desc}: {cr:.2f}:1 (Required: {req}:1)")

print(f"\nOverall Contrast Test Result: {'ALL PASSED' if all_passed else 'FAILURES FOUND'}")
