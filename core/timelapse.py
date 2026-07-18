"""Timelapse video generation, native aspect ratio, smooth playback."""

from core.video_writer import write_video


def generate_timelapse(images, output_path, duration, target_height=None, progress_callback=None):
    """
    Write a timelapse video from a sequence of images, stretched to fill
    `duration` seconds at a smooth constant frame rate. target_height
    resizes preserving aspect ratio (None = native resolution).
    """
    write_video(
        images, output_path, duration,
        target_height=target_height, accumulate=False,
        progress_callback=progress_callback,
    )
    return output_path