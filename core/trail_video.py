"""Star trail timelapse: video where trails accumulate frame by frame."""

import cv2
import numpy as np


def generate_trail_video(images, output_path, fps, progress_callback=None):
    """
    Write a video where each frame accumulates a growing star trail,
    using the native resolution of the first image.
    """
    first_frame = cv2.imread(str(images[0]))
    h, w = first_frame.shape[:2]

    video = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h)
    )

    trail = None
    for i, image_path in enumerate(images, start=1):
        frame = cv2.imread(str(image_path))
        trail = frame if trail is None else np.maximum(trail, frame)
        video.write(trail)
        if progress_callback:
            progress_callback(i, len(images))

    video.release()
    return output_path
