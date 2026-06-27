"""Filename policy — pure functions for building video file names."""

import re
from pathlib import PurePosixPath

# Uncensored keywords in tags
UNCENSORED_TAG_KEYWORDS = ("破解", "无码破解", "无码")

# Suffix pattern in filename: -C, -U, -UC before extension or end of string
_SUFFIX_PATTERN = re.compile(r"-(UC|C|U)(?:\.[^.]*$|$)", re.IGNORECASE)


def derive_code_suffix(has_chinese_sub: bool, tags: list[str]) -> str:
    """Derive code suffix from magnet metadata.

    Returns:
        "-C" for Chinese subtitle only
        "-U" for uncensored only
        "-UC" for both
        "" for neither
    """
    has_uncensored = any(kw in tag for tag in tags for kw in UNCENSORED_TAG_KEYWORDS)

    if has_chinese_sub and has_uncensored:
        return "-UC"
    if has_chinese_sub:
        return "-C"
    if has_uncensored:
        return "-U"
    return ""


def derive_code_suffix_from_filename(filename: str) -> str:
    """Derive code suffix from original filename.

    Looks for -C, -U, -UC patterns in the filename.
    Returns the suffix with dash prefix, or empty string if not found.
    """
    match = _SUFFIX_PATTERN.search(filename)
    if match:
        suffix = match.group(1).upper()
        return f"-{suffix}"
    return ""


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
    code_suffix: str = "",
) -> str:
    """Build a video filename from template and metadata.

    For multi-file sets where the template lacks {disc}, appends -CD{n}.
    """
    ext = PurePosixPath(original_name).suffix
    code_with_suffix = movie_code + code_suffix

    if total <= 1:
        return template.replace("{code}", code_with_suffix).replace("{ext}", ext)

    number = disc_number(original_name) or (index + 1)
    name = template.replace("{code}", code_with_suffix).replace("{ext}", ext).replace("{disc}", str(number))
    if "{disc}" not in template:
        path = PurePosixPath(name)
        return f"{path.stem}-CD{number}{path.suffix}"
    return name
