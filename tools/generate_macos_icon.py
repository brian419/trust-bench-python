"""Regenerate the original TrustBench icon; optional authoring dependency: Pillow."""

from pathlib import Path

from PIL.Image import new
from PIL.ImageDraw import Draw


def generate_icon(destination: Path):
    image = new("RGBA", (1024, 1024))
    draw = Draw(image)
    draw.rounded_rectangle((32, 32, 992, 992), radius=210, fill="#142C46")

    # Draw the TB monogram as geometry so regeneration does not depend on fonts.
    draw.rectangle((174, 300, 474, 392), fill="#46D8D0")
    draw.rectangle((278, 392, 370, 724), fill="#46D8D0")
    draw.rounded_rectangle((530, 300, 850, 524), radius=108, fill="#47617B")
    draw.rounded_rectangle((530, 500, 850, 724), radius=108, fill="#47617B")
    draw.rectangle((530, 300, 622, 724), fill="#47617B")
    draw.rounded_rectangle((622, 382, 758, 442), radius=30, fill="#142C46")
    draw.rounded_rectangle((622, 582, 758, 642), radius=30, fill="#142C46")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="ICNS")


if __name__ == "__main__":
    generate_icon(Path(__file__).resolve().parents[1] / "macos" / "TrustBench.icns")
