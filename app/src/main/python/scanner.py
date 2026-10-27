import json
import os

def scan_cache(root):
    """返回 [[标题, 视频路径, 音频路径], ...]"""
    tasks = []
    for dirpath, _, filenames in os.walk(root):
        if "entry.json" not in filenames:
            continue
        entry_path = os.path.join(dirpath, "entry.json")
        try:
            with open(entry_path, "r", encoding="utf-8-sig") as f:
                meta = json.load(f)
        except Exception:
            continue

        title = (meta.get("title") or os.path.basename(dirpath)).replace("/", "_")[:76]
        page = meta.get("page_data") or {}
        part = (page.get("part") or "").replace("/", "_")[:40]
        if part:
            title = f"{title}_{part}"

        video = audio = None
        for dp, _, fs in os.walk(dirpath):
            for f in fs:
                if f == "video.m4s" and video is None:
                    video = os.path.join(dp, f)
                elif f == "audio.m4s" and audio is None:
                    audio = os.path.join(dp, f)

        if video and audio:
            tasks.append([title, video, audio])
    return tasks