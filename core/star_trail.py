"""Star trail image generation via max-value stacking."""

import cv2
import numpy as np


def generate_star_trail(images, output_path, progress_callback=None):
    """
    Stack a sequence of images using max-value blending to produce
    a single star trail image at native resolution.
    """
    result = cv2.imread(str(images[0]))
    if progress_callback:
        progress_callback(1, len(images))

    for i, image_path in enumerate(images[1:], start=2):
        img = cv2.imread(str(image_path))
        result = np.maximum(result, img)
        if progress_callback:
            progress_callback(i, len(images))

    cv2.imwrite(str(output_path), result)
    return output_path
