"""Star trail image generation via max-value stacking."""

import cv2
import numpy as np


def _read_image(path):
    """cv2.imread that fails loudly instead of silently returning None
    for a missing or corrupted file (also keeps type checkers happy)."""
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError(f"Could not read image: {path}")
    return frame


def generate_star_trail(images, output_path, progress_callback=None):
    """
    Stack a sequence of images using max-value blending to produce
    a single star trail image at native resolution.
    """
    result = _read_image(images[0])
    if progress_callback:
        progress_callback(1, len(images))

    for i, image_path in enumerate(images[1:], start=2):
        img = _read_image(image_path)
        result = np.maximum(result, img)
        if progress_callback:
            progress_callback(i, len(images))

    cv2.imwrite(str(output_path), result)
    return output_path