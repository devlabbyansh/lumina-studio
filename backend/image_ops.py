"""
image_ops.py - High-performance OpenCV image processing engine.
Implements modern computer vision filters, transformations, background removal,
color adjustments, and vector SVG conversion.
"""

import os
import cv2
import numpy as np


def get_image_metadata(filepath):
    """Extract width, height, channel count, and file size from an image."""
    try:
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        h, w = img.shape[:2]
        c = img.shape[2] if len(img.shape) > 2 else 1
        size_bytes = os.path.getsize(filepath)
        return {
            "width": w,
            "height": h,
            "channels": c,
            "size_kb": round(size_bytes / 1024, 1),
            "aspect_ratio": f"{w}:{h}",
            "has_alpha": c == 4
        }
    except Exception as err:
        print(f"[image_ops] Failed to read metadata: {err}")
        return None


def calculate_histogram(filepath, bins=64):
    """Calculate downsampled R, G, B channel histograms for visualization."""
    try:
        img = cv2.imread(filepath, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # BGR channels
        hist_b = cv2.calcHist([img], [0], None, [bins], [0, 256]).flatten()
        hist_g = cv2.calcHist([img], [1], None, [bins], [0, 256]).flatten()
        hist_r = cv2.calcHist([img], [2], None, [bins], [0, 256]).flatten()

        max_val = max(hist_b.max(), hist_g.max(), hist_r.max(), 1.0)
        return {
            "r": (hist_r / max_val * 100).round(1).tolist(),
            "g": (hist_g / max_val * 100).round(1).tolist(),
            "b": (hist_b / max_val * 100).round(1).tolist(),
        }
    except Exception as err:
        print(f"[image_ops] Failed to calculate histogram: {err}")
        return None


# -----------------------------------------------------------------------------
# Background Removal (AI & Color Key)
# -----------------------------------------------------------------------------

def apply_remove_bg_smart(img, margin_pct=3):
    """
    Intelligent foreground segmentation using adaptive color-sampling and iterative GrabCut.
    Safely preserves clothing, bodies, hair, and chairs without stripping dark attire.
    Returns a 4-channel BGRA image with clean, feathered transparency.
    """
    has_alpha = len(img.shape) == 3 and img.shape[2] == 4
    if has_alpha:
        bgr = img[:, :, :3].copy()
    elif len(img.shape) == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        bgr = img.copy()

    h, w = bgr.shape[:2]

    # Convert to Lab color space for perceptually uniform color distance
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab).astype(np.float32)

    # Multi-scale optimization: compute GrabCut on max 800px dimension for speed and responsiveness
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
        bgr_small = cv2.resize(bgr, (sw, sh), interpolation=cv2.INTER_AREA)
        lab_small = cv2.resize(lab, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        scale = 1.0
        sh, sw = h, w
        bgr_small = bgr
        lab_small = lab

    # Multi-region background sampling along perimeter strips
    border_w = max(4, int(sw * (margin_pct / 100.0)))
    border_h = max(4, int(sh * (margin_pct / 100.0)))

    top_strip = lab_small[0:border_h, :]
    left_strip = lab_small[:, 0:border_w]
    right_strip = lab_small[:, max(0, sw - border_w):sw]
    c_size = max(6, int(min(sh, sw) * 0.08))
    tl_corner = lab_small[0:c_size, 0:c_size].reshape(-1, 3)
    tr_corner = lab_small[0:c_size, max(0, sw - c_size):sw].reshape(-1, 3)

    bg_samples = np.vstack([
        top_strip.reshape(-1, 3),
        left_strip.reshape(-1, 3),
        right_strip.reshape(-1, 3),
        tl_corner,
        tr_corner
    ])

    # K-Means clustering (K=2) on background samples to model studio lighting gradients
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, _, centers = cv2.kmeans(bg_samples, 2, None, criteria, 5, cv2.KMEANS_PP_CENTERS)

    # Compute Euclidean distance in Lab space to nearest background cluster
    d0 = np.linalg.norm(lab_small - centers[0], axis=2)
    d1 = np.linalg.norm(lab_small - centers[1], axis=2)
    min_bg_dist = np.minimum(d0, d1)

    # Determine dynamic color threshold based on background variation
    bg_std = float(np.std(bg_samples, axis=0).mean())
    thresh_bg = max(18.0, min(bg_std * 2.2, 38.0))

    # Initialize GrabCut mask
    # 0=GC_BGD (Definite BG), 1=GC_FGD (Definite FG), 2=GC_PR_BGD (Probable BG), 3=GC_PR_FGD (Probable FG)
    mask = np.full((sh, sw), cv2.GC_PR_BGD, dtype=np.uint8)

    # Outer perimeter (top, left, right) are definite background
    mask[0:border_h, :] = cv2.GC_BGD
    mask[:, 0:border_w] = cv2.GC_BGD
    mask[:, max(0, sw - border_w):sw] = cv2.GC_BGD

    # Bottom corners: only mark as background if they match background color
    bot_size = max(5, int(sw * 0.08))
    bot_l = (min_bg_dist[max(0, sh - border_h):sh, 0:bot_size] < thresh_bg)
    bot_r = (min_bg_dist[max(0, sh - border_h):sh, max(0, sw - bot_size):sw] < thresh_bg)
    mask[max(0, sh - border_h):sh, 0:bot_size][bot_l] = cv2.GC_BGD
    mask[max(0, sh - border_h):sh, max(0, sw - bot_size):sw][bot_r] = cv2.GC_BGD

    # Foreground candidate pixels: distinctly differ from background
    fg_candidates = (min_bg_dist > thresh_bg)
    mask[fg_candidates] = cv2.GC_PR_FGD

    # Central subject bias: ensure central core is treated as probable foreground
    cx1, cx2 = int(sw * 0.18), int(sw * 0.82)
    cy1, cy2 = int(sh * 0.12), int(sh * 0.88)
    inner_fg = (min_bg_dist[cy1:cy2, cx1:cx2] > thresh_bg * 0.70)
    mask[cy1:cy2, cx1:cx2][inner_fg] = cv2.GC_PR_FGD

    # Fail-safe sample guarantees: Ensure GrabCut always has both FG and BG samples
    if not np.any((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)):
        mask[cy1:cy2, cx1:cx2] = cv2.GC_PR_FGD
    if not np.any((mask == cv2.GC_BGD) | (mask == cv2.GC_PR_BGD)):
        mask[0:border_h, :] = cv2.GC_BGD

    # Models for GrabCut
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        # Run GrabCut iterative graph-cut segmentation
        cv2.grabCut(bgr_small, mask, None, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_MASK)
        # Extract foreground: 1 (GC_FGD) or 3 (GC_PR_FGD)
        alpha_small = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    except Exception as e:
        # Fallback to adaptive Lab color distance alpha thresholding
        alpha_small = np.where(min_bg_dist > thresh_bg, 255, 0).astype(np.uint8)

    # Morphological hole-closing: Prevents hollow clothing, black shirts, hair, or shadows inside subject
    close_ksize = max(5, int(min(sh, sw) * 0.02))
    if close_ksize % 2 == 0:
        close_ksize += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_ksize, close_ksize))
    alpha_small = cv2.morphologyEx(alpha_small, cv2.MORPH_CLOSE, kernel)

    # Contour filtering: keep all large connected components (subject, chair, clothing)
    # and discard tiny background noise flecks
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(alpha_small, connectivity=8)
    if num_labels > 1:
        min_area = (sh * sw) * 0.005  # At least 0.5% of total image area
        clean_mask = np.zeros_like(alpha_small)
        for label_idx in range(1, num_labels):
            area = stats[label_idx, cv2.CC_STAT_AREA]
            if area >= min_area:
                clean_mask[labels == label_idx] = 255
        if np.sum(clean_mask) > 0:
            alpha_small = clean_mask

    # Scale alpha mask back to original resolution if downscaled
    if scale != 1.0:
        alpha = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        alpha = alpha_small

    # Soft anti-aliasing on cutout perimeter
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

    # Return 4-channel BGRA with original image colors preserved
    b, g, r = cv2.split(bgr)
    return cv2.merge([b, g, r, alpha])


def apply_remove_bg_color(img, color="white", tolerance=45):
    """
    Chroma-key / color-key background removal for solid backgrounds (e.g. white, black, green).
    Returns 4-channel BGRA image with background keyed to transparent.
    """
    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif len(img.shape) == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        bgr = img

    tol = int(tolerance)
    col_str = str(color).lower()

    if col_str in ("black", "dark"):
        # Dark pixels become transparent
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        alpha = cv2.threshold(gray, tol, 255, cv2.THRESH_BINARY)[1]
    elif col_str in ("green", "greenscreen"):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 60, 60]), np.array([85, 255, 255]))
        alpha = cv2.bitwise_not(mask)
    else:  # Default: white / light background
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        alpha = cv2.threshold(gray, 255 - tol, 255, cv2.THRESH_BINARY_INV)[1]

    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    b, g, r = cv2.split(bgr)
    return cv2.merge([b, g, r, alpha])


# -----------------------------------------------------------------------------
# SVG Vectorization
# -----------------------------------------------------------------------------

def convert_to_svg(filepath, num_colors=8, max_dimension=600):
    """
    Vectorize a raster image into scalable SVG paths using color quantization and polygonal contour tracing.
    """
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Could not read image file.")

    has_alpha = len(img.shape) == 3 and img.shape[2] == 4
    if has_alpha:
        b, g, r, a = cv2.split(img)
        rgb = cv2.merge([r, g, b])
        alpha_mask = a
    else:
        if len(img.shape) == 2:
            rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        alpha_mask = None

    h, w = rgb.shape[:2]
    # Scale down for efficient polygon approximation if needed
    if max(h, w) > max_dimension:
        scale = max_dimension / float(max(h, w))
        target_w, target_h = max(1, int(w * scale)), max(1, int(h * scale))
        rgb_small = cv2.resize(rgb, (target_w, target_h), interpolation=cv2.INTER_AREA)
        alpha_small = cv2.resize(alpha_mask, (target_w, target_h), interpolation=cv2.INTER_NEAREST) if alpha_mask is not None else None
    else:
        rgb_small = rgb
        alpha_small = alpha_mask
        scale = 1.0

    sh, sw = rgb_small.shape[:2]

    # Smooth colors to reduce polygon complexity
    smoothed = cv2.bilateralFilter(rgb_small, d=7, sigmaColor=50, sigmaSpace=50)

    # K-means color clustering
    pixel_data = smoothed.reshape((-1, 3)).astype(np.float32)
    k = max(2, min(int(num_colors), 16))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 1.0)
    _, labels, centers = cv2.kmeans(pixel_data, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    centers = np.uint8(centers)
    quantized = centers[labels.flatten()].reshape((sh, sw, 3))

    svg_polygons = []
    # Sort colors by luminance for proper layering
    luminances = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in centers]
    sorted_order = np.argsort(luminances)

    inv_scale = 1.0 / scale

    for idx in sorted_order:
        c = centers[idx]
        hex_color = "#{:02x}{:02x}{:02x}".format(c[0], c[1], c[2])

        mask = np.all(quantized == c, axis=-1).astype(np.uint8) * 255
        if alpha_small is not None:
            mask = cv2.bitwise_and(mask, mask, mask=(alpha_small > 30).astype(np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) < 5:
                continue
            approx = cv2.approxPolyDP(cnt, 1.2, True)
            pts = approx.reshape(-1, 2)
            if len(pts) >= 3:
                coords = " ".join(f"{round(p[0] * inv_scale, 1)},{round(p[1] * inv_scale, 1)}" for p in pts)
                svg_polygons.append(f'<polygon points="{coords}" fill="{hex_color}" stroke="{hex_color}" stroke-width="0.5"/>')

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <g id="vector-artwork">
    {''.join(svg_polygons)}
  </g>
</svg>'''
    return svg_content


# -----------------------------------------------------------------------------
# Core Filters & Transformations
# -----------------------------------------------------------------------------

def apply_grayscale(img):
    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return cv2.merge([gray_3ch[:, :, 0], gray_3ch[:, :, 1], gray_3ch[:, :, 2], img[:, :, 3]])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def apply_blur(img, ksize=15):
    ksize = int(ksize)
    if ksize % 2 == 0:
        ksize += 1
    return cv2.GaussianBlur(img, (max(1, ksize), max(1, ksize)), 0)


def apply_median_blur(img, ksize=7):
    ksize = int(ksize)
    if ksize % 2 == 0:
        ksize += 1
    return cv2.medianBlur(img, max(3, min(ksize, 31)))


def apply_rotate(img, angle=90):
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif angle in (270, -90):
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(matrix[0, 0])
        sin = np.abs(matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        matrix[0, 2] += (new_w / 2) - center[0]
        matrix[1, 2] += (new_h / 2) - center[1]
        return cv2.warpAffine(img, matrix, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)


def apply_flip(img, mode="horizontal"):
    if mode in ("horizontal", "h"):
        return cv2.flip(img, 1)
    elif mode in ("vertical", "v"):
        return cv2.flip(img, 0)
    return cv2.flip(img, -1)


def apply_canny(img, low=100, high=200):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, int(low), int(high))
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def apply_brightness_contrast(img, brightness=0, contrast=1.0):
    return cv2.convertScaleAbs(img, alpha=float(contrast), beta=int(brightness))


def apply_sepia(img):
    sepia_matrix = np.array([
        [0.131, 0.534, 0.272],
        [0.168, 0.686, 0.349],
        [0.189, 0.769, 0.393]
    ])
    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        sepia = cv2.transform(bgr, sepia_matrix)
        return cv2.merge([sepia[:, :, 0], sepia[:, :, 1], sepia[:, :, 2], img[:, :, 3]])
    return cv2.transform(img, sepia_matrix)


def apply_pencil_sketch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    inverted_blurred = 255 - blurred
    sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)


def apply_threshold(img, threshold_val=127):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, int(threshold_val), 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


def apply_invert(img):
    if len(img.shape) == 3 and img.shape[2] == 4:
        inv = cv2.bitwise_not(img[:, :, :3])
        return cv2.merge([inv[:, :, 0], inv[:, :, 1], inv[:, :, 2], img[:, :, 3]])
    return cv2.bitwise_not(img)


def apply_resize(img, width=None, height=None, percent=None):
    h, w = img.shape[:2]
    if percent:
        factor = float(percent) / 100.0
        new_w = max(1, int(w * factor))
        new_h = max(1, int(h * factor))
    elif width and height:
        new_w, new_h = max(1, int(width)), max(1, int(height))
    elif width:
        new_w = max(1, int(width))
        new_h = max(1, int(h * (new_w / w)))
    elif height:
        new_h = max(1, int(height))
        new_w = max(1, int(w * (new_h / h)))
    else:
        return img
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def apply_crop(img, area_type="center", percent=50, x1=None, y1=None, x2=None, y2=None):
    h, w = img.shape[:2]
    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
        try:
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        except (ValueError, TypeError):
            return img
    else:
        p = float(percent) / 100.0
        if area_type == "center":
            crop_w, crop_h = int(w * p), int(h * p)
            x1 = (w - crop_w) // 2
            y1 = (h - crop_h) // 2
            x2 = x1 + crop_w
            y2 = y1 + crop_h
        elif area_type == "top":
            x1, y1, x2, y2 = 0, 0, w, int(h * p)
        elif area_type == "bottom":
            x1, y1, x2, y2 = 0, int(h * (1 - p)), w, h
        elif area_type == "left":
            x1, y1, x2, y2 = 0, 0, int(w * p), h
        elif area_type == "right":
            x1, y1, x2, y2 = int(w * (1 - p)), 0, w, h
        else:
            return img

    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))
    return img[y1:y2, x1:x2]


def apply_sharpen(img, strength=1.5):
    strength = max(0.2, min(float(strength), 4.0))
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1.0 + strength * 0.5, blurred, -strength * 0.5, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def apply_emboss(img):
    kernel = np.array([
        [-2, -1, 0],
        [-1,  1, 1],
        [ 0,  1, 2]
    ])
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    embossed = cv2.filter2D(gray, -1, kernel) + 128
    embossed = np.clip(embossed, 0, 255).astype(np.uint8)
    return cv2.cvtColor(embossed, cv2.COLOR_GRAY2BGR)


def apply_cartoon(img):
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.medianBlur(gray, 7)
    edges = cv2.adaptiveThreshold(
        gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2
    )
    color = bgr
    for _ in range(2):
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.bitwise_and(color, edges_bgr)


def apply_vignette(img, intensity=0.7):
    h, w = img.shape[:2]
    intensity = max(0.1, min(float(intensity), 1.0))
    k_x = cv2.getGaussianKernel(w, w * 0.5)
    k_y = cv2.getGaussianKernel(h, h * 0.5)
    kernel = k_y * k_x.T
    mask = kernel / kernel.max()
    mask = (1.0 - intensity) + intensity * mask
    vignette = np.zeros_like(img, dtype=np.float32)
    channels = img.shape[2] if len(img.shape) > 2 else 1
    for i in range(min(3, channels)):
        vignette[:, :, i] = img[:, :, i] * mask
    if channels == 4:
        vignette[:, :, 3] = img[:, :, 3]
    return np.clip(vignette, 0, 255).astype(np.uint8)


def apply_temperature(img, mode="warm", intensity=30):
    res = img.astype(np.int16)
    intensity = max(5, min(int(intensity), 80))
    if mode == "warm":
        res[:, :, 2] += intensity         # Red
        res[:, :, 0] -= (intensity // 2)  # Blue
    else:  # cool
        res[:, :, 0] += intensity         # Blue
        res[:, :, 2] -= (intensity // 2)  # Red
    return np.clip(res, 0, 255).astype(np.uint8)


def apply_clahe(img, clip_limit=2.5):
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl, a, b))
    res_bgr = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    if len(img.shape) == 3 and img.shape[2] == 4:
        return cv2.merge([res_bgr[:, :, 0], res_bgr[:, :, 1], res_bgr[:, :, 2], img[:, :, 3]])
    return res_bgr


def apply_denoise(img):
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    denoised = cv2.bilateralFilter(bgr, d=9, sigmaColor=75, sigmaSpace=75)
    if len(img.shape) == 3 and img.shape[2] == 4:
        return cv2.merge([denoised[:, :, 0], denoised[:, :, 1], denoised[:, :, 2], img[:, :, 3]])
    return denoised


def apply_saturation(img, factor=1.5):
    factor = max(0.0, min(float(factor), 3.0))
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255)
    hsv = hsv.astype(np.uint8)
    res_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    if len(img.shape) == 3 and img.shape[2] == 4:
        return cv2.merge([res_bgr[:, :, 0], res_bgr[:, :, 1], res_bgr[:, :, 2], img[:, :, 3]])
    return res_bgr


def apply_gamma(img, gamma=1.5):
    gamma = max(0.2, min(float(gamma), 4.0))
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(img, table)


def apply_posterize(img, levels=4):
    levels = max(2, min(int(levels), 16))
    step = 256 // levels
    return (img // step) * step + (step // 2)


def apply_colormap(img, colormap="ocean"):
    cm_map = {
        "ocean": cv2.COLORMAP_OCEAN,
        "autumn": cv2.COLORMAP_AUTUMN,
        "inferno": cv2.COLORMAP_INFERNO,
        "bone": cv2.COLORMAP_BONE,
        "turbo": cv2.COLORMAP_TURBO,
        "twilight": cv2.COLORMAP_TWILIGHT,
        "pink": cv2.COLORMAP_PINK,
        "jet": cv2.COLORMAP_JET
    }
    cm_enum = cm_map.get(str(colormap).lower(), cv2.COLORMAP_OCEAN)
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(gray, cm_enum)


def apply_edge_glow(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if len(img.shape) == 3 and img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 180)
    glow = cv2.GaussianBlur(edges, (15, 15), 0)
    glow_colored = cv2.applyColorMap(glow, cv2.COLORMAP_OCEAN)
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    dark_base = cv2.convertScaleAbs(bgr, alpha=0.35, beta=0)
    return cv2.add(dark_base, glow_colored)


def apply_solarize(img, threshold=128):
    thresh = max(30, min(int(threshold), 220))
    return np.where(img > thresh, 255 - img, img)


def apply_color_splash(img, color="red"):
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) if len(img.shape) == 3 and img.shape[2] == 4 else img
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    col = str(color).lower()
    if col in ("blue", "cyan"):
        mask = cv2.inRange(hsv, np.array([90, 60, 50]), np.array([130, 255, 255]))
    elif col in ("green", "emerald"):
        mask = cv2.inRange(hsv, np.array([35, 50, 50]), np.array([85, 255, 255]))
    elif col in ("yellow", "gold"):
        mask = cv2.inRange(hsv, np.array([20, 70, 70]), np.array([35, 255, 255]))
    else:  # Red
        mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        mask = mask1 | mask2

    return np.where(mask[:, :, None] == 255, bgr, gray_bgr)


# -----------------------------------------------------------------------------
# Dispatcher Pipeline
# -----------------------------------------------------------------------------

def process_image(filepath, action, params):
    """Execute target image operation and return (processed_img, status_message)."""
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read source image at {filepath}")

    if not params:
        params = {}

    act = (action or "").lower().strip().replace("-", "_").replace(" ", "_")

    if act in ("remove_bg", "removebg", "bg_remove", "cutout", "ai_remove_bg", "remove_background"):
        res = apply_remove_bg_smart(img)
        msg = "Removed background using AI GrabCut segmentation."

    elif act in ("remove_bg_color", "key_white", "key_white_bg", "color_key", "chroma_key"):
        col = params.get("color", "white")
        tol = params.get("tolerance", 45)
        res = apply_remove_bg_color(img, color=col, tolerance=tol)
        msg = f"Removed {col} background (color keying)."

    elif act in ("make_png", "to_png", "png"):
        if len(img.shape) == 3 and img.shape[2] == 4:
            res = img
        else:
            res = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        msg = "Converted image to transparent PNG format."

    elif act in ("make_jpg", "to_jpg", "jpg", "jpeg", "make_jpeg"):
        if len(img.shape) == 3 and img.shape[2] == 4:
            b, g, r, a = cv2.split(img)
            alpha_f = a.astype(float) / 255.0
            bg = np.ones_like(b, dtype=float) * 255.0
            b_out = (b * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            g_out = (g * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            r_out = (r * alpha_f + bg * (1.0 - alpha_f)).astype(np.uint8)
            res = cv2.merge([b_out, g_out, r_out])
        else:
            res = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        msg = "Converted image to standard JPG format (white background)."

    elif act in ("vectorize", "make_svg", "to_svg", "svg", "vector"):
        num_colors = params.get("colors", 8)
        if len(img.shape) == 3 and img.shape[2] == 4:
            b, g, r, a = cv2.split(img)
            bgr = cv2.merge([b, g, r])
            has_a = True
        else:
            bgr = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            has_a = False
            a = None

        h, w = bgr.shape[:2]
        pixel_data = bgr.reshape((-1, 3)).astype(np.float32)
        k = max(2, min(int(num_colors), 16))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixel_data, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        quantized = np.uint8(centers)[labels.flatten()].reshape((h, w, 3))
        quantized = cv2.bilateralFilter(quantized, 5, 50, 50)
        if has_a and a is not None:
            qb, qg, qr = cv2.split(quantized)
            res = cv2.merge([qb, qg, qr, a])
        else:
            res = quantized
        msg = f"Vectorized into {k}-color SVG paths. Ready to export as SVG vector!"

    elif act in ("grayscale", "gray", "greyscale", "black_and_white", "bw"):
        res = apply_grayscale(img)
        msg = "Converted image to grayscale."

    elif act in ("blur", "gaussian_blur"):
        ksize = params.get("ksize", 15)
        res = apply_blur(img, ksize)
        msg = f"Applied Gaussian Blur ({ksize}px)."

    elif act in ("median_blur", "median", "clean_noise", "grain_cleaner", "noise_reduction"):
        ksize = params.get("ksize", 7)
        res = apply_median_blur(img, ksize)
        msg = f"Applied Median Filter noise cleaner ({ksize}px)."

    elif act in ("rotate", "rotate_cw", "rotate_ccw"):
        angle = params.get("angle", 90)
        if act == "rotate_ccw":
            angle = -90
        res = apply_rotate(img, angle)
        msg = f"Rotated image by {angle}°."

    elif act in ("flip", "flip_h", "flip_v", "flip_horizontal", "flip_vertical"):
        mode = "vertical" if act in ("flip_v", "flip_vertical") else params.get("mode", "horizontal")
        res = apply_flip(img, mode)
        msg = f"Flipped image {mode}ly."

    elif act in ("edges", "canny", "canny_edges", "edge_detect"):
        low = params.get("low", 100)
        high = params.get("high", 200)
        res = apply_canny(img, low, high)
        msg = f"Extracted Canny edges (low: {low}, high: {high})."

    elif act in ("brightness", "brighten", "dim"):
        val = params.get("val", 40)
        res = apply_brightness_contrast(img, brightness=val)
        dir_word = "Increased" if val >= 0 else "Decreased"
        msg = f"{dir_word} brightness by {abs(val)}."

    elif act in ("contrast", "boost_contrast"):
        factor = params.get("factor", 1.3)
        res = apply_brightness_contrast(img, contrast=factor)
        pct = round(abs(factor - 1.0) * 100)
        dir_word = "Increased" if factor >= 1.0 else "Decreased"
        msg = f"{dir_word} contrast by {pct}% ({factor}x)."

    elif act in ("sepia", "vintage", "vintage_sepia"):
        res = apply_sepia(img)
        msg = "Applied vintage sepia photo filter."

    elif act in ("sketch", "pencil_sketch", "draw", "drawing", "pencil"):
        res = apply_pencil_sketch(img)
        msg = "Transformed into a hand-drawn pencil sketch."

    elif act in ("threshold", "binary_threshold"):
        val = params.get("val", 127)
        res = apply_threshold(img, val)
        msg = f"Applied binary threshold at value {val}."

    elif act in ("invert", "negative", "invert_negative"):
        res = apply_invert(img)
        msg = "Inverted color spectrum (negative)."

    elif act in ("resize", "scale"):
        w = params.get("width")
        h = params.get("height")
        p = params.get("percent")
        res = apply_resize(img, width=w, height=h, percent=p)
        if p:
            msg = f"Rescaled dimensions to {p}%."
        else:
            msg = f"Resized to {res.shape[1]}x{res.shape[0]} px."

    elif act in ("crop", "crop_image"):
        x1, y1 = params.get("x1"), params.get("y1")
        x2, y2 = params.get("x2"), params.get("y2")
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            res = apply_crop(img, x1=x1, y1=y1, x2=x2, y2=y2)
            msg = f"Cropped region: [{x1}, {y1}] to [{x2}, {y2}]."
        else:
            area = params.get("area_type", "center")
            pct = params.get("percent", 50)
            res = apply_crop(img, area_type=area, percent=pct)
            msg = f"Cropped {area} {pct}%."

    elif act in ("sharpen", "clarity", "sharpness"):
        strength = params.get("strength", 1.5)
        res = apply_sharpen(img, strength=strength)
        msg = f"Sharpened image clarity ({strength}x)."

    elif act in ("emboss", "3d_emboss", "relief"):
        res = apply_emboss(img)
        msg = "Applied 3D tactile relief emboss filter."

    elif act in ("cartoon", "cartoonify", "anime", "illustration"):
        res = apply_cartoon(img)
        msg = "Applied cartoon illustration effect."

    elif act in ("vignette", "vignette_fx"):
        intensity = params.get("intensity", 0.7)
        res = apply_vignette(img, intensity=intensity)
        msg = "Applied photographic vignette."

    elif act in ("temperature", "warm", "cool", "golden_hour", "goldenhour", "cyberpunk", "cyberpunk_blue", "cold", "warmth", "icy"):
        if act in ("warm", "golden_hour", "goldenhour", "warmth"):
            mode = "warm"
        elif act in ("cool", "cyberpunk", "cyberpunk_blue", "cold", "icy"):
            mode = "cool"
        else:
            mode = params.get("mode", "warm")
        intensity = params.get("intensity", 30)
        res = apply_temperature(img, mode=mode, intensity=intensity)
        tone_str = "warm golden hour" if mode == "warm" else "cool cyberpunk"
        msg = f"Applied {tone_str} color temperature effect."

    elif act in ("clahe", "clahe_contrast", "adaptive_contrast", "hdr"):
        clip = params.get("clip_limit", 2.5)
        res = apply_clahe(img, clip_limit=clip)
        msg = "Enhanced adaptive dynamic contrast (CLAHE)."

    elif act in ("denoise", "smooth_skin", "smooth", "skin_smoothing"):
        res = apply_denoise(img)
        msg = "Applied bilateral noise reduction and skin smoothing."

    elif act in ("saturation", "saturate", "vibrance"):
        factor = params.get("factor", 1.5)
        res = apply_saturation(img, factor=factor)
        msg = f"Adjusted color saturation ({factor}x)."

    elif act in ("gamma", "gamma_correction"):
        val = params.get("gamma", 1.4)
        res = apply_gamma(img, gamma=val)
        msg = f"Applied gamma lighting adjustment ({val})."

    elif act in ("posterize", "8bit", "posterize_8bit", "retro"):
        levels = params.get("levels", 4)
        res = apply_posterize(img, levels=levels)
        msg = f"Posterized color palette to {levels} tonal levels."

    elif act in ("colormap", "ocean", "inferno", "plasma", "viridis"):
        cm = params.get("colormap", act if act in ("ocean", "inferno", "plasma", "viridis") else "ocean")
        res = apply_colormap(img, colormap=cm)
        msg = f"Applied '{cm}' false-color palette."

    elif act in ("edge_glow", "neon_glow", "glow", "neon"):
        res = apply_edge_glow(img)
        msg = "Applied neon edge glow lighting effect."

    elif act in ("solarize", "solarize_fx"):
        thresh = params.get("threshold", 128)
        res = apply_solarize(img, threshold=thresh)
        msg = "Applied solarize photographic effect."

    elif act in ("color_splash", "splash", "red_splash"):
        color = params.get("color", "red")
        res = apply_color_splash(img, color=color)
        msg = f"Applied selective color splash (isolating {color})."

    else:
        raise ValueError(f"Unknown operation: '{action}'.")

    return res, msg
