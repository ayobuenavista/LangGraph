"""Tools available to the Graphics Agent."""

from __future__ import annotations

import colorsys
import json

from langchain_core.tools import tool


@tool
def generate_color_palette(
    base_hex: str = "#6366F1",
    steps: int = 10,
    mode: str = "monochromatic",
) -> str:
    """Generate an accessible color palette as CSS custom properties.

    Args:
        base_hex: Base color in hex format.
        steps: Number of shades to generate.
        mode: 'monochromatic', 'complementary', or 'analogous'.
    """
    r = int(base_hex[1:3], 16) / 255
    g = int(base_hex[3:5], 16) / 255
    b = int(base_hex[5:7], 16) / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    shades: list[dict] = []
    for i in range(steps):
        factor = i / max(steps - 1, 1)
        if mode == "monochromatic":
            new_v = 0.15 + factor * 0.80
            nr, ng, nb = colorsys.hsv_to_rgb(h, s, new_v)
        elif mode == "complementary":
            offset_h = (h + 0.5 * factor) % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(offset_h, s, v)
        else:  # analogous
            offset_h = (h - 0.083 + 0.167 * factor) % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(offset_h, s, v)

        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(nr * 255), int(ng * 255), int(nb * 255)
        )
        shade_name = (i + 1) * (1000 // steps)
        shades.append({"name": f"--color-brand-{shade_name}", "value": hex_color})

    css_lines = [":root {"]
    for shade in shades:
        css_lines.append(f"  {shade['name']}: {shade['value']};")
    css_lines.append("}")
    return "\n".join(css_lines)


@tool
def check_contrast_ratio(fg_hex: str, bg_hex: str) -> str:
    """Check WCAG 2.1 contrast ratio between foreground and background colors.

    Returns the ratio and whether it passes AA / AAA for normal and large text.
    """
    def relative_luminance(hex_color: str) -> float:
        r = int(hex_color[1:3], 16) / 255
        g = int(hex_color[3:5], 16) / 255
        b = int(hex_color[5:7], 16) / 255

        def linearize(c: float) -> float:
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)

    return json.dumps({
        "foreground": fg_hex,
        "background": bg_hex,
        "ratio": round(ratio, 2),
        "aa_normal": ratio >= 4.5,
        "aa_large": ratio >= 3.0,
        "aaa_normal": ratio >= 7.0,
        "aaa_large": ratio >= 4.5,
    })


@tool
def generate_svg_icon(
    icon_name: str,
    size: int = 24,
    color: str = "currentColor",
) -> str:
    """Generate a simple SVG icon for common app elements.

    Supported icons: chart-line, chart-bar, chart-pie, arrow-up, arrow-down,
    wallet, token, refresh, settings, search, filter, grid, list.
    """
    paths = {
        "chart-line": "M3 17l4-4 4 4 8-10",
        "chart-bar": "M4 20h3v-8H4zm6 0h3v-14h-3zm6 0h3v-10h-3z",
        "chart-pie": "M12 2a10 10 0 100 20 10 10 0 000-20zm0 2v8l6.93 4a8 8 0 10-6.93-12z",
        "arrow-up": "M12 19V5m-7 7l7-7 7 7",
        "arrow-down": "M12 5v14m7-7l-7 7-7-7",
        "wallet": "M3 7a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7zm14 4h2v2h-2v-2z",
        "token": "M12 2a10 10 0 100 20 10 10 0 000-20zm-1 5h2v2h-2V7zm0 4h2v6h-2v-6z",
        "refresh": "M4 12a8 8 0 018-8v4l5-5-5-5v4a10 10 0 100 20 10 10 0 006-2l-1.5-1.5A8 8 0 014 12z",
        "settings": "M12 8a4 4 0 100 8 4 4 0 000-8zm-9 3h2a7 7 0 010 2H3zm18 0h-2a7 7 0 010 2h2z",
        "search": "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
        "filter": "M3 4h18l-7 8v6l-4 2V12L3 4z",
        "grid": "M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z",
        "list": "M4 6h16M4 12h16M4 18h16",
    }

    path_d = paths.get(icon_name, paths["chart-line"])
    is_filled = icon_name in ("chart-bar", "chart-pie", "filter", "grid")
    fill = color if is_filled else "none"
    stroke = "none" if is_filled else color

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{path_d}"/></svg>'
    )


@tool
def generate_tailwind_theme(brand_config: str = "") -> str:
    """Generate a Tailwind CSS theme extension for the app.

    If brand_config is empty, uses the default brand guide.
    """
    theme = {
        "colors": {
            "brand": {
                "primary": "#6366F1",
                "accent": "#22D3EE",
                "success": "#10B981",
                "danger": "#EF4444",
                "warning": "#F59E0B",
            },
            "surface": {
                "900": "#0F172A",
                "800": "#1E293B",
                "700": "#334155",
                "600": "#475569",
            },
            "text": {
                "primary": "#F8FAFC",
                "secondary": "#94A3B8",
                "muted": "#64748B",
            },
        },
        "fontFamily": {
            "sans": ["Inter", "system-ui", "sans-serif"],
            "mono": ["JetBrains Mono", "monospace"],
        },
        "borderRadius": {
            "card": "0.75rem",
            "button": "0.5rem",
            "badge": "9999px",
        },
        "boxShadow": {
            "card": "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
            "glow-primary": "0 0 15px rgba(99, 102, 241, 0.3)",
            "glow-accent": "0 0 15px rgba(34, 211, 238, 0.3)",
        },
    }

    lines = [
        "// tailwind.config.ts — extend section",
        "// Auto-generated by Graphics Agent",
        f"export const appTheme = {json.dumps(theme, indent=2)};",
    ]
    return "\n".join(lines)


GRAPHICS_TOOLS = [
    generate_color_palette,
    check_contrast_ratio,
    generate_svg_icon,
    generate_tailwind_theme,
]
