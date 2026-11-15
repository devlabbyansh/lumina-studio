"""
nlp.py - Natural language parsing for image processing commands.
Extracts transformation intent, directional modes, and parameters from text prompts.
"""

import re


def parse_prompt(prompt):
    """Parse user command string into an action dict with extracted parameters."""
    if not prompt or not isinstance(prompt, str):
        return None

    p = prompt.lower().strip()

    # 1. Undo & Reset
    if any(k in p for k in ["undo", "go back", "revert last", "step back"]):
        return {"action": "undo", "params": {}}

    if any(k in p for k in ["reset", "revert", "start over", "original state", "back to original"]):
        return {"action": "reset", "params": {}}

    # 2. AI Background Remover & Color Keying
    if (("background" in p or "bg" in p) and any(w in p for w in ["remove", "cut", "isolate", "extract", "delete", "clear", "strip", "transparent", "erase"])) or any(k in p for k in ["cutout", "cut out", "crop background"]):
        if "white" in p:
            return {"action": "remove_bg_color", "params": {"color": "white"}}
        elif "black" in p or "dark" in p:
            return {"action": "remove_bg_color", "params": {"color": "black"}}
        elif "green" in p:
            return {"action": "remove_bg_color", "params": {"color": "green"}}
        return {"action": "remove_bg", "params": {}}

    # 3. Format Conversion (PNG / JPG / SVG)
    if any(k in p for k in ["make svg", "convert to svg", "vectorize", "svg format", "to svg", "vector format", "trace vector"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        colors = numbers[0] if numbers else 8
        return {"action": "vectorize", "params": {"colors": min(max(2, colors), 16)}}

    if any(k in p for k in ["make png", "convert to png", "save as png", "png format", "to png", "transparent png"]):
        return {"action": "make_png", "params": {}}

    if any(k in p for k in ["make jpg", "convert to jpg", "save as jpg", "jpg format", "to jpg", "convert to jpeg", "make jpeg", "to jpeg"]):
        return {"action": "make_jpg", "params": {}}

    # 2. Saturation / Vibrance (New)
    if any(k in p for k in ["saturation", "vibrance", "saturate", "vibrant", "boost color", "pop colors"]):
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        factor = 1.6
        if any(d in p for d in ["desaturate", "less color", "mute", "muted"]):
            factor = 0.5
        elif numbers:
            factor = numbers[0] if numbers[0] <= 5 else numbers[0] / 100.0
        return {"action": "saturation", "params": {"factor": factor}}

    # 3. Gamma / Shadow Recovery (New)
    if any(k in p for k in ["gamma", "lift shadows", "shadow recovery", "shadows"]):
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        gamma_val = numbers[0] if numbers else 1.4
        return {"action": "gamma", "params": {"gamma": gamma_val}}

    # 4. Color Splash / Selective Color (New)
    if any(k in p for k in ["splash", "color splash", "selective color", "keep only", "isolate color"]):
        target_color = "red"
        if "blue" in p or "cyan" in p:
            target_color = "blue"
        elif "green" in p or "emerald" in p:
            target_color = "green"
        elif "yellow" in p or "gold" in p:
            target_color = "yellow"
        return {"action": "color_splash", "params": {"color": target_color}}

    # 5. Colormap / False Color (New)
    if any(k in p for k in ["colormap", "color map", "false color", "heat map", "thermal"]):
        cm = "ocean"
        if "autumn" in p: cm = "autumn"
        elif "inferno" in p or "fire" in p: cm = "inferno"
        elif "bone" in p: cm = "bone"
        elif "turbo" in p: cm = "turbo"
        elif "twilight" in p: cm = "twilight"
        elif "pink" in p: cm = "pink"
        elif "jet" in p: cm = "jet"
        return {"action": "colormap", "params": {"colormap": cm}}

    # 6. Neon Edge Glow (New)
    if any(k in p for k in ["glow", "neon", "neon edges", "edge glow", "glowing outline"]):
        return {"action": "edge_glow", "params": {}}

    # 7. Posterize / Pop-Art (New)
    if any(k in p for k in ["posterize", "pop art", "8-bit", "quantize", "retro color", "color levels"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        levels = numbers[0] if numbers else 4
        return {"action": "posterize", "params": {"levels": min(max(2, levels), 12)}}

    # 8. Solarize (New)
    if any(k in p for k in ["solarize", "solarization", "sabattier"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        thresh = numbers[0] if numbers else 128
        return {"action": "solarize", "params": {"threshold": thresh}}

    # 9. Median Blur / Noise Filter (New)
    if any(k in p for k in ["median", "median blur", "salt and pepper", "grain noise", "remove speckles"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        ksize = numbers[0] if numbers else 7
        return {"action": "median_blur", "params": {"ksize": ksize}}

    # 10. Sharpen
    if any(k in p for k in ["sharpen", "sharp", "clarity", "crisp", "make it sharp"]):
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        strength = min(max(0.5, numbers[0]), 3.5) if numbers else 1.5
        return {"action": "sharpen", "params": {"strength": strength}}

    # 11. Cartoon
    if any(k in p for k in ["cartoon", "cartoonify", "comic", "anime", "illustration", "toon"]):
        return {"action": "cartoon", "params": {}}

    # 12. 3D Emboss
    if any(k in p for k in ["emboss", "relief", "3d relief", "stamped", "embossed"]):
        return {"action": "emboss", "params": {}}

    # 13. Vignette
    if any(k in p for k in ["vignette", "dark edges", "border shadow", "cinematic border"]):
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        intensity = 0.7
        if numbers:
            intensity = numbers[0] / 100.0 if numbers[0] > 1 else numbers[0]
        return {"action": "vignette", "params": {"intensity": min(max(0.2, intensity), 0.95)}}

    # 14. Temperature (Warm / Cool)
    if any(k in p for k in ["warm", "golden hour", "warmth", "sunset tone"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        return {"action": "temperature", "params": {"mode": "warm", "intensity": numbers[0] if numbers else 30}}

    if any(k in p for k in ["cool", "cold", "blue tone", "cyberpunk tone", "icy"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        return {"action": "temperature", "params": {"mode": "cool", "intensity": numbers[0] if numbers else 30}}

    # 15. CLAHE (Adaptive Contrast)
    if any(k in p for k in ["clahe", "adaptive histogram", "enhance lighting", "fix lighting", "dynamic range"]):
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        return {"action": "clahe", "params": {"clip_limit": numbers[0] if numbers else 2.5}}

    # 16. Denoise / Smooth
    if any(k in p for k in ["denoise", "noise reduction", "smooth skin", "smooth image", "bilateral"]):
        return {"action": "denoise", "params": {}}

    # 17. Grayscale
    if any(k in p for k in ["gray", "grey", "grayscale", "black and white", "b&w", "monochrome"]):
        return {"action": "grayscale", "params": {}}

    # 18. Sepia
    if any(k in p for k in ["sepia", "vintage", "retro", "old photo"]):
        return {"action": "sepia", "params": {}}

    # 19. Pencil Sketch
    if any(k in p for k in ["sketch", "pencil sketch", "drawing", "pencil"]):
        return {"action": "sketch", "params": {}}

    # 20. Canny Edges
    if any(k in p for k in ["edge", "edges", "canny", "outline", "detect edge"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        low, high = 100, 200
        if len(numbers) >= 2:
            low, high = numbers[0], numbers[1]
        elif len(numbers) == 1:
            low = numbers[0]
            high = min(low * 2, 255)
        return {"action": "edges", "params": {"low": low, "high": high}}

    # 21. Invert
    if any(k in p for k in ["invert", "negative", "inverse", "opposite colors"]):
        return {"action": "invert", "params": {}}

    # 22. Blur
    if any(k in p for k in ["blur", "blurry", "gaussian blur", "smooth", "soften"]):
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        ksize = numbers[0] if numbers else 15
        if ksize % 2 == 0:
            ksize += 1
        return {"action": "blur", "params": {"ksize": max(1, ksize)}}

    # 23. Rotate
    if any(k in p for k in ["rotate", "turn"]):
        angle = 90
        numbers = [int(s) for s in re.findall(r"\b-?\d+\b", p)]
        if numbers:
            angle = numbers[0]
        elif any(d in p for d in ["ccw", "counter", "left", "-90"]):
            angle = -90
        elif any(d in p for d in ["upside", "180"]):
            angle = 180
        return {"action": "rotate", "params": {"angle": angle}}

    # 24. Flip
    if any(k in p for k in ["flip", "mirror"]):
        mode = "horizontal"
        if any(v in p for v in ["vertical", "upside", "y-axis"]):
            mode = "vertical"
        elif "both" in p:
            mode = "both"
        return {"action": "flip", "params": {"mode": mode}}

    # 25. Brightness
    if any(k in p for k in ["bright", "brightness", "dark", "darken", "light", "lighten", "dim"]):
        numbers = [int(s) for s in re.findall(r"[-+]?\b\d+\b", p)]
        val = 40
        if any(d in p for d in ["dark", "dim", "decrease"]):
            val = -abs(numbers[0]) if numbers else -40
        elif numbers:
            val = abs(numbers[0])
        return {"action": "brightness", "params": {"val": val}}

    # 26. Contrast
    if "contrast" in p:
        numbers = [float(s) for s in re.findall(r"\b\d+(?:\.\d+)?\b", p)]
        factor = 1.3
        if any(l in p for l in ["decrease", "less", "low", "lower"]):
            factor = 1.0 - (numbers[0] / 100.0) if numbers and numbers[0] > 10 else 0.7
        elif numbers:
            factor = 1.0 + (numbers[0] / 100.0) if numbers[0] > 10 else numbers[0]
        return {"action": "contrast", "params": {"factor": factor}}

    # 27. Threshold
    if "threshold" in p or "binary" in p:
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        val = min(max(0, numbers[0]), 255) if numbers else 127
        return {"action": "threshold", "params": {"val": val}}

    # 28. Resize
    if any(k in p for k in ["resize", "scale", "shrink", "enlarge"]):
        dims = re.findall(r"\b(\d+)\s*[xX,]\s*(\d+)\b", p)
        pct = re.findall(r"\b(\d+)\s*(?:%|percent)\b", p)
        if dims:
            return {"action": "resize", "params": {"width": int(dims[0][0]), "height": int(dims[0][1])}}
        elif pct:
            return {"action": "resize", "params": {"percent": int(pct[0])}}
        else:
            numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
            if numbers and numbers[0] <= 5000:
                return {"action": "resize", "params": {"width": numbers[0]}}

    # 29. Crop
    if "crop" in p or "cut" in p:
        numbers = [int(s) for s in re.findall(r"\b\d+\b", p)]
        if len(numbers) >= 4:
            return {"action": "crop", "params": {"x1": numbers[0], "y1": numbers[1], "x2": numbers[2], "y2": numbers[3]}}

        area = "center"
        for d in ["top left", "top right", "bottom left", "bottom right", "top", "bottom", "left", "right"]:
            if d in p:
                area = d.replace(" ", "_")
                break

        pct = 50
        if numbers:
            pct = min(max(10, numbers[0]), 99)
        return {"action": "crop", "params": {"area_type": area, "percent": pct}}

    return None

