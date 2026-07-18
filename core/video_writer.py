"""
Shared video writing backend.

- Guarantees every source image appears in the output at least once (no
  frames silently dropped), for any duration you choose.
- Targets a minimum of MIN_SMOOTH_FPS for smooth playback: if
  num_images / duration would be lower than that, encoding fps is bumped
  up (frames get repeated/held) to keep it smooth. If you have more source
  images than duration * MIN_SMOOTH_FPS allows, fps scales up instead
  (never drops a frame) so the requested duration is still hit exactly.
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

MIN_SMOOTH_FPS = 30


def _plan(num_images, duration):
    """
    Decide how many output frames to encode and at what fps, guaranteeing
    every source image is used at least once while still landing on the
    exact requested duration.
    """
    total_frames = max(round(MIN_SMOOTH_FPS * duration), num_images)
    fps = total_frames / duration
    return total_frames, fps


def output_frame_count(duration, num_images):
    """Total encoded frames for a given duration and source image count."""
    total_frames, _ = _plan(num_images, duration)
    return total_frames


def _target_size(w, h, target_height):
    """Scale to target_height, preserving aspect ratio. None = native size."""
    if target_height is None or target_height == h:
        return w, h
    scale = target_height / h
    new_w = int(round(w * scale / 2) * 2)   # even dims required for yuv420p
    new_h = int(round(target_height / 2) * 2)
    return new_w, new_h


def _read_image(path):
    """cv2.imread that fails loudly instead of silently returning None
    for a missing or corrupted file (also keeps type checkers happy)."""
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError(f"Could not read image: {path}")
    return frame


def _frame_schedule(num_images, total_frames):
    """
    Map each output frame to a source image index. Monotonically
    non-decreasing, and guaranteed to hit every source index at least once
    whenever total_frames >= num_images (which _plan always ensures).
    """
    return [min(num_images - 1, int(i * num_images / total_frames)) for i in range(total_frames)]


def write_video(images, output_path, duration, target_height=None, accumulate=False, progress_callback=None):
    """
    Write a video from a sequence of images, using every image at least
    once, timed to land exactly on `duration` seconds.

    target_height: resize to this height, preserving aspect ratio (None = native).
    accumulate=True builds a growing star trail (max-blend) as frames advance.
    """
    total_frames, fps = _plan(len(images), duration)
    schedule = _frame_schedule(len(images), total_frames)

    if shutil.which("ffmpeg"):
        _write_with_ffmpeg(images, output_path, schedule, fps, target_height, accumulate, progress_callback)
    else:
        _write_with_opencv(images, output_path, schedule, fps, target_height, accumulate, progress_callback)


def _resize_if_needed(frame, out_w, out_h):
    h, w = frame.shape[:2]
    if (w, h) == (out_w, out_h):
        return frame
    interp = cv2.INTER_AREA if out_h < h else cv2.INTER_LINEAR
    return cv2.resize(frame, (out_w, out_h), interpolation=interp)


def _write_with_ffmpeg(images, output_path, schedule, fps, target_height, accumulate, progress_callback):
    first = _read_image(images[0])
    h, w = first.shape[:2]
    out_w, out_h = _target_size(w, h, target_height)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{out_w}x{out_h}", "-r", str(fps),
        "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    cache = {}
    trail = None
    total = len(schedule)

    for out_i, src_i in enumerate(schedule, start=1):
        if src_i not in cache:
            frame = _read_image(images[src_i])
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


def _write_with_opencv(images, output_path, schedule, fps, target_height, accumulate, progress_callback):
    first = _read_image(images[0])
    h, w = first.shape[:2]
    out_w, out_h = _target_size(w, h, target_height)

    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    video = cv2.VideoWriter(str(output_path), fourcc, fps, (out_w, out_h))

    cache = {}
    trail = None
    total = len(schedule)

    for out_i, src_i in enumerate(schedule, start=1):
        if src_i not in cache:
            frame = _read_image(images[src_i])
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