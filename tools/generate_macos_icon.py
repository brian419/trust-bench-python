"""Regenerate the original TrustBench icon; optional authoring dependency: Pillow."""

from pathlib import Path

from PIL.Image import new
from PIL.ImageDraw import Draw


def generate_icon(destination: Path):
    image = new("RGBA", (1024, 1024))
    draw = Draw(image)
    draw.rounded_rectangle((32, 32, 992, 992), radius=210, fill="#142C46")

    # Draw the TB monogram as geometry so regeneration does not depend on fonts.
    draw.rectangle((192, 230, 466, 310), fill="white")
    draw.rectangle((289, 310, 369, 594), fill="white")
    draw.rounded_rectangle((530, 230, 822, 424), radius=90, fill="white")
    draw.rounded_rectangle((530, 400, 822, 594), radius=90, fill="white")
    draw.rectangle((530, 230, 610, 594), fill="white")
    draw.rounded_rectangle((610, 302, 742, 352), radius=25, fill="#142C46")
    draw.rounded_rectangle((610, 472, 742, 522), radius=25, fill="#142C46")

    # Three result cells represent inspected test cases rather than a growth chart.
    for left, color in ((194, "#46D8D0"), (434, "#47617B"), (674, "#46D8D0")):
        draw.rounded_rectangle((left, 704, left + 156, 832), radius=26, fill=color)
    for left in (194, 674):
        draw.line([(left + 35, 765), (left + 65, 795), (left + 119, 741)],
                  fill="#142C46", width=19, joint="curve")
    draw.rounded_rectangle((475, 758, 549, 778), radius=10, fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="ICNS")


if __name__ == "__main__":
    generate_icon(Path(__file__).resolve().parents[1] / "macos" / "TrustBench.icns")
