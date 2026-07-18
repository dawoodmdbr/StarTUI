"""Timelapse video generation at native image resolution."""

import cv2


def generate_timelapse(images, output_path, fps, progress_callback=None):
    """
    Write a timelapse video from a sequence of images, using the
    native resolution of the first image.
    """
    first_frame = cv2.imread(str(images[0]))
    h, w = first_frame.shape[:2]

    video = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h)
    )

    for i, image_path in enumerate(images, start=1):
        frame = cv2.imread(str(image_path))
        video.write(frame)
        if progress_callback:
            progress_callback(i, len(images))

    video.release()
    return output_path
