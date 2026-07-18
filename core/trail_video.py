"""Star trail timelapse: video where trails accumulate frame by frame."""

from core.video_writer import write_video


def generate_trail_video(images, output_path, duration, target_height=None, progress_callback=None):
    """
    Write a video where each frame accumulates a growing star trail,
    stretched to fill `duration` seconds at a smooth constant frame rate.
    target_height resizes preserving aspect ratio (None = native resolution).
    """
    write_video(
        images, output_path, duration,
        target_height=target_height, accumulate=True,
        progress_callback=progress_callback,
    )
    return output_path