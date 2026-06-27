"""Video selector — pure functions for classifying scanned files into categories."""

from dataclasses import dataclass, field
from pathlib import PurePosixPath

SUBTITLE_EXTENSIONS = frozenset({".srt", ".ass", ".ssa", ".sub", ".sup", ".idx"})
COVER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp"})


@dataclass
class SelectedFiles:
    selected_videos: list[dict] = field(default_factory=list)
    excluded_files: list[dict] = field(default_factory=list)
    subtitle_files: list[dict] = field(default_factory=list)
    cover_files: list[dict] = field(default_factory=list)
    other_files: list[dict] = field(default_factory=list)


def select_files(scanned: list[dict], config: dict) -> SelectedFiles:
    """Classify scanned files into video, excluded, subtitle, cover, and other categories."""
    result = SelectedFiles()
    video_exts = set(config.get("video_extensions", []))
    min_size = config.get("minimum_video_size_mb", 100) * 1024 * 1024
    exclude_kw = [kw.lower() for kw in config.get("excluded_filename_keywords", [])]

    for file_info in scanned:
        name = file_info["name"]
        ext = PurePosixPath(name).suffix.lower()
        lower_name = name.lower()

        if any(keyword in lower_name for keyword in exclude_kw):
            result.excluded_files.append(file_info)
        elif ext in video_exts and file_info["size"] >= min_size:
            result.selected_videos.append({**file_info, "video_type": "main"})
        elif ext in video_exts:
            result.excluded_files.append(file_info)
        elif ext in SUBTITLE_EXTENSIONS:
            result.subtitle_files.append(file_info)
        elif ext in COVER_EXTENSIONS:
            result.cover_files.append(file_info)
        else:
            result.other_files.append(file_info)

    return result
