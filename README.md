# StarTUI

A terminal app for turning a folder of sequential night-sky photos into star trail images, star trail videos, and timelapses.

Built with [Rich](https://github.com/Textualize/rich) and [questionary](https://github.com/tmbo/questionary).

## What it does

Drop your `.jpg` frames into `input/`, run it, and pick any combination of:

- **Star Trail Image** — a single photo where every star's path across the sky is stacked into one frame (max-value blending)
- **Star Trail Video** — a video where the star trail grows frame by frame
- **Timelapse** — a straight timelapse of the sequence

All outputs use the native resolution of your source images — no resizing or letterboxing.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
mkdir input          # add your .jpg frames here
python main.py
```

You'll be walked through:

1. Which outputs to generate (any combination)
2. Video duration in seconds (only asked if a video output is selected — applies to both)
3. A summary + confirmation
4. Per-frame progress bars while it processes

Outputs are written to `output/`:

```
output/
├── startrail.jpg
├── trail_timelapse.mp4
└── timelapse.mp4
```

## Project structure

```
StarTUI/
├── main.py              # wizard flow (prompts, progress, orchestration)
├── input/                # drop your .jpg frames here
├── core/
│   ├── star_trail.py    # max-value stacking -> single image
│   ├── timelapse.py     # straight timelapse video
│   └── trail_video.py   # accumulating star trail video
└── requirements.txt
```