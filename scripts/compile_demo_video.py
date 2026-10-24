"""
Compiles demo screenshots into a smooth, high-resolution demo walkthrough video and animated GIF
using ffmpeg.
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "docs" / "assets"
VIDEO_OUT = BASE_DIR / "docs" / "ClaimSense_AI_Demo.mp4"
GIF_OUT = ASSETS_DIR / "ClaimSense_AI_Demo.gif"

def create_video():
    # Sequence of screens to show
    screens = [
        ASSETS_DIR / "demo_workbench.png",
        ASSETS_DIR / "demo_adjudication.png",
        ASSETS_DIR / "demo_observability.png",
        ASSETS_DIR / "demo_trust.png",
        ASSETS_DIR / "demo_audit.png",
        ASSETS_DIR / "demo_evals.png",
    ]
    
    # Verify all exist
    for s in screens:
        if not s.exists():
            raise FileNotFoundError(f"Missing screen: {s}")

    # Build input files text for ffmpeg concat demuxer
    # Each image shown for 4 seconds
    concat_file = BASE_DIR / "scratch" / "ffmpeg_concat.txt"
    concat_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(concat_file, "w") as f:
        for s in screens:
            f.write(f"file '{s.resolve()}'\n")
            f.write("duration 4.0\n")
        # repeat last frame
        f.write(f"file '{screens[-1].resolve()}'\n")

    print("Generating MP4 video...")
    cmd_mp4 = [
        "/opt/homebrew/bin/ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "24",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(VIDEO_OUT)
    ]
    subprocess.run(cmd_mp4, check=True)
    print(f"✅ Generated demo video at: {VIDEO_OUT} ({os.path.getsize(VIDEO_OUT)} bytes)")

    print("Generating animated GIF preview...")
    cmd_gif = [
        "/opt/homebrew/bin/ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-r", "10",
        str(GIF_OUT)
    ]
    subprocess.run(cmd_gif, check=True)
    print(f"✅ Generated demo GIF at: {GIF_OUT} ({os.path.getsize(GIF_OUT)} bytes)")

if __name__ == "__main__":
    create_video()
