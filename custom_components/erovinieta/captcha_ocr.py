"""Pillow-based captcha OCR for erovinieta.ro.

Uses template matching against pre-built character templates to solve
simple text captchas. No external ML dependencies required — only Pillow
(which is bundled with Home Assistant).

Typical accuracy: ~94% per-character, ~77% full-captcha (before i/l fix).
With i/l dot-detection heuristic, accuracy improves to ~95%+ per-character.
With 5 retries the overall success rate exceeds 99.9%.
"""

from __future__ import annotations

import base64
import io
import logging
import zlib

from PIL import Image

_LOGGER = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

NORM_W = 20  # Normalized character width (pixels)
NORM_H = 28  # Normalized character height (pixels)
PIXEL_COUNT = NORM_W * NORM_H  # 560 pixels per template
PIXEL_BYTES = (PIXEL_COUNT + 7) // 8  # 70 bytes packed
BINARIZE_THRESHOLD = 128
MIN_SEGMENT_WIDTH = 3  # Ignore segments narrower than this (noise)
MAX_GAP_MERGE = 3  # Merge segments separated by ≤ this many columns

# ── Compressed template data ──────────────────────────────────────────────────
# Binary format (zlib-compressed, base64-encoded):
#   Header: num_letters (1 byte)
#   Per letter:
#     letter (1 byte ASCII)
#     median_h (1 byte) — median original height of this letter
#     median_w (1 byte) — median original width of this letter
#     num_exemplars (1 byte)
#     avg template: PIXEL_BYTES bytes (average of all samples, binarized)
#     exemplar templates: num_exemplars * PIXEL_BYTES bytes each
#
# Built from 200 captchas labeled with ddddocr, 831 character samples,
# 24 letters (a-z minus j which had only 1 sample).

_TEMPLATE_DATA_B64 = (
    "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"
    "A9mgw9A="
)


# ── Template loading ──────────────────────────────────────────────────────────


def _unpack_pixels(data: bytes, offset: int) -> list[int]:
    """Unpack PIXEL_BYTES bytes into a list of 0/1 pixel values."""
    pixels = []
    for i in range(PIXEL_COUNT):
        byte_idx = offset + i // 8
        bit_idx = 7 - i % 8
        pixels.append((data[byte_idx] >> bit_idx) & 1)
    return pixels


def _load_templates() -> dict[str, dict]:
    """Decompress and parse the embedded template data.

    Returns dict mapping letter -> {
        "avg": list[int],        # average template (560 pixels, 0/1)
        "exemplars": list[list[int]],  # up to 8 exemplar templates
        "median_h": int,         # median original height
        "median_w": int,         # median original width
    }
    """
    raw = zlib.decompress(base64.b64decode(_TEMPLATE_DATA_B64))
    num_letters = raw[0]
    offset = 1
    templates: dict[str, dict] = {}

    for _ in range(num_letters):
        letter = chr(raw[offset])
        median_h = raw[offset + 1]
        median_w = raw[offset + 2]
        num_exemplars = raw[offset + 3]
        offset += 4

        avg = _unpack_pixels(raw, offset)
        offset += PIXEL_BYTES

        exemplars = []
        for _ in range(num_exemplars):
            ex = _unpack_pixels(raw, offset)
            offset += PIXEL_BYTES
            exemplars.append(ex)

        templates[letter] = {
            "avg": avg,
            "exemplars": exemplars,
            "median_h": median_h,
            "median_w": median_w,
        }

    return templates


# Module-level cache (loaded once on first use)
_TEMPLATES: dict[str, dict] | None = None


def _get_templates() -> dict[str, dict]:
    """Return cached templates, loading them on first call."""
    global _TEMPLATES  # noqa: PLW0603
    if _TEMPLATES is None:
        _TEMPLATES = _load_templates()
    return _TEMPLATES


# ── Image processing ──────────────────────────────────────────────────────────


def _binarize(img: Image.Image) -> tuple[int, int, list[int]]:
    """Convert a PIL Image to binary pixel array (1=black, 0=white)."""
    gray = img.convert("L")
    w, h = gray.size
    pixels = list(gray.getdata())
    return w, h, [1 if p < BINARIZE_THRESHOLD else 0 for p in pixels]


def _segment_characters(
    w: int, h: int, binary: list[int]
) -> list[tuple[int, int]]:
    """Find character column ranges using vertical projection.

    Returns list of (x_start, x_end) tuples for each character.
    """
    # Count black pixels per column
    col_counts = []
    for x in range(w):
        count = sum(binary[y * w + x] for y in range(h))
        col_counts.append(count)

    # Find contiguous segments of columns with black pixels
    segments: list[tuple[int, int]] = []
    in_char = False
    start = 0
    for x, count in enumerate(col_counts):
        if count > 0 and not in_char:
            start = x
            in_char = True
        elif count == 0 and in_char:
            segments.append((start, x))
            in_char = False
    if in_char:
        segments.append((start, w))

    # Merge segments with small gaps (handles broken strokes)
    merged: list[tuple[int, int]] = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] <= MAX_GAP_MERGE:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(seg)

    # Filter out tiny segments (noise)
    return [(s, e) for s, e in merged if e - s >= MIN_SEGMENT_WIDTH]


def _extract_char(
    w: int, h: int, binary: list[int], x_start: int, x_end: int
) -> tuple[list[int] | None, int, int]:
    """Extract and normalize a single character from the binary image.

    Returns (normalized_pixels, orig_width, orig_height).
    normalized_pixels is None if the character is empty.
    """
    # Find tight vertical bounding box
    y_min, y_max = h, 0
    for y in range(h):
        for x in range(x_start, x_end):
            if binary[y * w + x]:
                y_min = min(y_min, y)
                y_max = max(y_max, y + 1)

    if y_min >= y_max:
        return None, 0, 0

    char_w = x_end - x_start
    char_h = y_max - y_min

    # Create cropped character image
    char_img = Image.new("L", (char_w, char_h), 255)
    char_px = char_img.load()
    for y in range(y_min, y_max):
        for x in range(x_start, x_end):
            if binary[y * w + x]:
                char_px[x - x_start, y - y_min] = 0

    # Resize to normalized dimensions
    resized = char_img.resize((NORM_W, NORM_H), Image.LANCZOS)

    # Re-binarize (Lanczos produces antialiased grayscale)
    norm_pixels = [1 if p < BINARIZE_THRESHOLD else 0 for p in resized.getdata()]

    return norm_pixels, char_w, char_h


# ── Matching ──────────────────────────────────────────────────────────────────


def _pixel_similarity(a: list[int], b: list[int]) -> float:
    """Compute pixel-wise similarity between two binary templates (0.0–1.0)."""
    matches = sum(1 for x, y in zip(a, b) if x == y)
    return matches / len(a)


def _match_character(
    norm_pixels: list[int],
    orig_w: int,
    orig_h: int,
    templates: dict[str, dict],
) -> str:
    """Match a normalized character against all templates.

    Uses a weighted combination of:
    - k-NN exemplar similarity (top-3 closest exemplars)
    - Average template similarity
    - Height/width/aspect-ratio compatibility

    Returns the best-matching letter.
    """
    best_letter = "?"
    best_score = -1.0

    for letter, td in templates.items():
        # Exemplar similarity: average of top-3 closest
        exemplar_sims = sorted(
            [_pixel_similarity(norm_pixels, ex) for ex in td["exemplars"]],
            reverse=True,
        )
        k = min(3, len(exemplar_sims))
        exemplar_score = sum(exemplar_sims[:k]) / k

        # Average template similarity
        avg_score = _pixel_similarity(norm_pixels, td["avg"])

        # Height compatibility
        h_diff = abs(orig_h - td["median_h"]) / max(td["median_h"], 1)
        h_score = max(0.0, 1.0 - h_diff * 0.5)

        # Width compatibility
        w_diff = abs(orig_w - td["median_w"]) / max(td["median_w"], 1)
        w_score = max(0.0, 1.0 - w_diff * 0.5)

        # Aspect ratio compatibility
        orig_aspect = orig_w / max(orig_h, 1)
        templ_aspect = td["median_w"] / max(td["median_h"], 1)
        aspect_diff = abs(orig_aspect - templ_aspect)
        aspect_score = max(0.0, 1.0 - aspect_diff)

        # Weighted combination
        score = (
            0.50 * exemplar_score
            + 0.30 * avg_score
            + 0.07 * h_score
            + 0.07 * w_score
            + 0.06 * aspect_score
        )

        if score > best_score:
            best_score = score
            best_letter = letter

    return best_letter


# ── i/l disambiguation ────────────────────────────────────────────────────────

# Threshold for "narrow" characters where i/l confusion can occur.
_NARROW_WIDTH_THRESHOLD = 15


def _has_dot_above(
    w: int, h: int, binary: list[int], x_start: int, x_end: int
) -> bool:
    """Detect whether a character has a dot separated from its main stroke.

    Scans the original (pre-normalization) binary image within the character's
    column range top-to-bottom, looking for the pattern:
        black rows → gap (≥2 consecutive all-white rows) → black rows

    If such a gap is found in the upper portion of the character, it indicates
    an 'i' (dot + stroke) rather than an 'l' (stroke only).
    """
    # Find the tight vertical bounding box for this character
    y_min, y_max = h, 0
    for y in range(h):
        for x in range(x_start, x_end):
            if binary[y * w + x]:
                y_min = min(y_min, y)
                y_max = max(y_max, y + 1)
                break

    if y_min >= y_max:
        return False

    char_h = y_max - y_min

    # Scan rows within bounding box, checking if each row has any black pixel
    row_has_ink = []
    for y in range(y_min, y_max):
        has_ink = any(binary[y * w + x] for x in range(x_start, x_end))
        row_has_ink.append(has_ink)

    # Look for pattern: ink → gap (≥2 white rows) → ink, in upper 60%
    upper_limit = int(char_h * 0.6)
    in_ink = False
    gap_count = 0
    found_first_ink = False

    for i in range(min(upper_limit, len(row_has_ink))):
        if row_has_ink[i]:
            if found_first_ink and gap_count >= 2:
                # Found ink, then gap, then ink again → dot above stroke
                return True
            in_ink = True
            found_first_ink = True
            gap_count = 0
        else:
            if in_ink:
                # Transitioned from ink to white
                gap_count += 1
            elif found_first_ink:
                gap_count += 1

    return False


def _disambiguate_i_l(
    letter: str,
    w: int,
    h: int,
    binary: list[int],
    x_start: int,
    x_end: int,
) -> str:
    """Post-process i/l matches using dot-above heuristic.

    Only applies to narrow characters where the template matcher picked
    'i' or 'l'. Uses the original binary image (before normalization) to
    check for a dot-stroke gap.
    """
    if letter not in ("i", "l"):
        return letter

    char_w = x_end - x_start
    if char_w > _NARROW_WIDTH_THRESHOLD:
        return letter

    has_dot = _has_dot_above(w, h, binary, x_start, x_end)
    result = "i" if has_dot else "l"

    if result != letter:
        _LOGGER.debug(
            "i/l disambiguation: '%s' -> '%s' (dot_above=%s, width=%d)",
            letter,
            result,
            has_dot,
            char_w,
        )

    return result


# ── Public API ────────────────────────────────────────────────────────────────


def solve_captcha(image_data: bytes) -> str:
    """Solve a captcha image and return the recognized text.

    Args:
        image_data: Raw image bytes (JPEG or PNG).

    Returns:
        Recognized text string (lowercase letters).

    Raises:
        ValueError: If the image cannot be processed or no characters found.
    """
    templates = _get_templates()

    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception as err:
        raise ValueError(f"Cannot open captcha image: {err}") from err

    w, h, binary = _binarize(img)
    segments = _segment_characters(w, h, binary)

    if not segments:
        raise ValueError("No characters found in captcha image")

    result = []
    for x_start, x_end in segments:
        norm_pixels, orig_w, orig_h = _extract_char(
            w, h, binary, x_start, x_end
        )
        if norm_pixels is None:
            continue

        letter = _match_character(norm_pixels, orig_w, orig_h, templates)
        letter = _disambiguate_i_l(letter, w, h, binary, x_start, x_end)
        result.append(letter)

    if not result:
        raise ValueError("Could not recognize any characters")

    text = "".join(result)
    _LOGGER.debug("Captcha OCR result: %s (%d characters)", text, len(text))
    return text
