"""Filename policy — pure functions for building video file names."""

import re
from pathlib import PurePosixPath


def disc_number(file_name: str) -> int | None:
    """Try to extract a disc/part number from a filename.

    Looks for patterns like CD1, CD2, -cd1, _cd2, Disc1, disc01, etc.
    """
    match = re.search(r"(?:cd|disc|part)[_\-\s]?(\d+)", file_name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def build_video_name(
    movie_code: str,
    original_name: str,
    index: int,
    total: int,
    template: str,
) -> str:
    """Build a video filename from template and metadata.

    For multi-file sets where the template lacks {disc}, appends -CD{n}.
    """
    ext = PurePosixPath(original_name).suffix
    if total <= 1:
        return template.replace("{code}", movie_code).replace("{ext}", ext)

    number = disc_number(original_name) or (index + 1)
    name = template.replace("{code}", movie_code).replace("{ext}", ext).replace("{disc}", str(number))
    if "{disc}" not in template:
        path = PurePosixPath(name)
        return f"{path.stem}-CD{number}{path.suffix}"
    return name
