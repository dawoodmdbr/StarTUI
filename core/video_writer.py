"""
Shared video writing backend.

- Encodes at a fixed PLAYBACK_FPS so videos stay smooth regardless of how
  many source photos there are (frames are stretched/repeated to fill the
  chosen duration).
- Resizes by target height only, preserving each image's native aspect
  ratio (no letterboxing/pillarboxing).
- Prefers piping frames to ffmpeg for H.264 encoding, which plays reliably
  everywhere (browsers, QuickTime, phones). Falls back to OpenCV's built-in
  writer (mp4v codec) if ffmpeg isn't installed on the system.
"""

import shutil
import subprocess

import cv2
import numpy as np

PLAYBACK_FPS = 30


def output_frame_count(duration):
    """Total encoded frames for a given duration at PLAYBACK_FPS."""
    return max(1, round(PLAYBACK_FPS * duration))


def _target_size(w, h, target_height):
    """Scale to target_height, preserving aspect ratio. None = native size."""
    if target_height is None or target_height == h:
        return w, h
    scale = target_height / h
    new_w = int(round(w * scale / 2) * 2)   # even dims required for yuv420p
    new_h = int(round(target_height / 2) * 2)
    return new_w, new_h


def _frame_schedule(num_images, duration):
    """
    Map each output frame (at PLAYBACK_FPS) to a source image index, so a
    small number of source photos still plays back smoothly for the full
    chosen duration. Always non-decreasing, so accumulation can be done
    incrementally in a single pass.
    """
    total_frames = output_frame_count(duration)
    return [min(num_images - 1, int(i * num_images / total_frames)) for i in range(total_frames)]


def write_video(images, output_path, duration, target_height=None, accumulate=False, progress_callback=None):
    """
    Write a video from a sequence of images, stretched/repeated to fill
    `duration` seconds at a smooth constant frame rate.

    target_height: resize to this height, preserving aspect ratio (None = native).
    accumulate=True builds a growing star trail (max-blend) as frames advance.
    """
    schedule = _frame_schedule(len(images), duration)

    if shutil.which("ffmpeg"):
        _write_with_ffmpeg(images, output_path, schedule, target_height, accumulate, progress_callback)
    else:
        _write_with_opencv(images, output_path, schedule, target_height, accumulate, progress_callback)


def _resize_if_needed(frame, out_w, out_h):
    h, w = frame.shape[:2]
    if (w, h) == (out_w, out_h):
        return frame
    interp = cv2.INTER_AREA if out_h < h else cv2.INTER_LINEAR
    return cv2.resize(frame, (out_w, out_h), interpolation=interp)


def _write_with_ffmpeg(images, output_path, schedule, target_height, accumulate, progress_callback):
    first = cv2.imread(str(images[0]))
    h, w = first.shape[:2]
    out_w, out_h = _target_size(w, h, target_height)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{out_w}x{out_h}", "-r", str(PLAYBACK_FPS),
        "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    cache = {}
    trail = None
    total = len(schedule)

    for out_i, src_i in enumerate(schedule, start=1):
        if src_i not in cache:
            frame = cv2.imread(str(images[src_i]))
            if accumulate:
                trail = frame if trail is None else np.maximum(trail, frame)
                frame_out = trail.copy()
            else:
                frame_out = frame
            cache[src_i] = _resize_if_needed(frame_out, out_w, out_h)

        proc.stdin.write(cache[src_i].tobytes())
        if progress_callback:
            progress_callback(out_i, total)

    proc.stdin.close()
    proc.wait()


def _write_with_opencv(images, output_path, schedule, target_height, accumulate, progress_callback):
    first = cv2.imread(str(images[0]))
    h, w = first.shape[:2]
    out_w, out_h = _target_size(w, h, target_height)

    video = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), PLAYBACK_FPS, (out_w, out_h)
    )

    cache = {}
    trail = None
    total = len(schedule)

    for out_i, src_i in enumerate(schedule, start=1):
        if src_i not in cache:
            frame = cv2.imread(str(images[src_i]))
            if accumulate:
                trail = frame if trail is None else np.maximum(trail, frame)
                frame_out = trail.copy()
            else:
                frame_out = frame
            cache[src_i] = _resize_if_needed(frame_out, out_w, out_h)

        video.write(cache[src_i])
        if progress_callback:
            progress_callback(out_i, total)

    video.release()