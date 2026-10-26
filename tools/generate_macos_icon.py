"""Regenerate the original TrustBench icon; optional authoring dependency: Pillow."""

from pathlib import Path

from PIL.Image import new
from PIL.ImageDraw import Draw


def generate_icon(destination: Path):
    image = new("RGBA", (1024, 1024))
    draw = Draw(image)
    draw.rounded_rectangle((32, 32, 992, 992), radius=210, fill="#142C46")
    draw.rounded_rectangle((226, 548, 354, 790), radius=28, fill="#46D8D0")
    draw.rounded_rectangle((448, 420, 576, 790), radius=28, fill="#46D8D0")
    draw.rounded_rectangle((670, 292, 798, 790), radius=28, fill="#46D8D0")
    draw.line([(228, 470), (448, 334), (602, 346), (786, 202)], fill="white", width=42,
              joint="curve")
    for x, y in ((228, 470), (448, 334), (602, 346), (786, 202)):
        draw.ellipse((x-29, y-29, x+29, y+29), fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="ICNS")


if __name__ == "__main__":
    generate_icon(Path(__file__).resolve().parents[1] / "macos" / "TrustBench.icns")
