import os
import sys
import json
import time
import shutil
import shlex
import logging
import subprocess
from pathlib import Path

# ---------- 可配置常量（支持环境变量覆盖） ----------
CACHE_ROOT = os.environ.get(
    "BILI_CACHE_ROOT",
    "/storage/emulated/0/Android/data/tv.danmaku.bili/download",
)
TEMP_DIR = os.environ.get(
    "BILI_TEMP_DIR",
    "/storage/emulated/0/Download/bili_cache_tmp",
)
OUTPUT_DIR = os.environ.get(
    "BILI_OUTPUT_DIR",
    "/storage/emulated/0/Movies/BiliMerge",
)

DRY_RUN = "--dry-run" in sys.argv

DANGEROUS_PATHS = {"/", "/storage", "/sdcard", "/storage/emulated", "/storage/emulated/0"}


# ---------- 日志 ----------
def setup_logging():
    handlers = [logging.StreamHandler()]
    for log_dir in (OUTPUT_DIR, TEMP_DIR):
        try:
            os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(Path(log_dir) / "merge.log", encoding="utf-8"))
            break
        except Exception:
            continue
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=handlers,
    )


log = logging.info


# ---------- 存储权限 ----------
def has_storage_permission():
    """通过真实写入测试判断存储权限，比 os.access 可靠"""
    try:
        probe_dir = Path("/storage/emulated/0/Download")
        if not probe_dir.exists():
            return False
        probe = probe_dir / ".termux_perm_probe"
        probe.write_text("x")
        probe.unlink()
        return True
    except Exception:
        return False


def request_storage_permission(timeout=30):
    if shutil.which("termux-setup-storage") is None:
        log("未找到 termux-setup-storage，无法自动申请存储权限。")
        log("请在 Termux 中手动执行：termux-setup-storage")
        return False

    log("需要存储权限，正在弹出系统授权窗口，请点「允许」…")
    try:
        subprocess.Popen(
            ["termux-setup-storage"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log(f"触发授权失败：{e}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if has_storage_permission():
            log("存储权限已获得。")
            return True
        time.sleep(1)

    log("等待存储权限超时，请手动授予后重试。")
    return False


def ensure_storage_permission():
    if has_storage_permission():
        return True
    return request_storage_permission()


# ---------- 基础检测 ----------
def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        log("未检测到 ffmpeg，可能是未安装或未在 Termux 内执行？")
        return False
    try:
        r = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            log("ffmpeg 存在但无法运行，可能依赖缺失。请重装：pkg install ffmpeg")
            return False
    except Exception as e:
        log(f"ffmpeg 检查失败：{e}")
        return False
    return True


def can_read_cache():
    """普通用户视角：(可读, 普通用户视角下存在)"""
    p = Path(CACHE_ROOT)
    if not p.exists():
        return False, False
    try:
        items = os.listdir(p)
        for name in items[:3]:
            sub = p / name
            if sub.is_dir():
                try:
                    os.listdir(sub)
                except Exception:
                    return False, True
        return True, True
    except Exception:
        return False, True


def check_output_writable():
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        test = Path(OUTPUT_DIR) / ".write_test"
        test.write_text("test")
        test.unlink()
        return True
    except Exception as e:
        log(f"输出目录无权限读写！：{OUTPUT_DIR}（{e}）")
        return False


# ---------- 提权执行器 ----------
def detect_privileged_executor():
    """返回可用执行器前缀：['su','-c'] / ['rish','-c'] / None"""
    log("正在检测 root / rish（如弹出授权请点允许）…")
    try:
        r = subprocess.run(["su", "-c", "id"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and "uid=0" in r.stdout:
            return ["su", "-c"]
    except Exception:
        pass

    if shutil.which("rish") is not None:
        try:
            r = subprocess.run(["rish", "-c", "id"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return ["rish", "-c"]
            else:
                log("rish 已安装但调用失败，请先在 Termux 中运行一次 `rish` 完成初始化。")
        except Exception:
            log("rish 已安装但调用异常，请先在 Termux 中运行一次 `rish` 完成初始化。")

    return None


def path_exists_as_privileged(executor):
    """用提权执行器检查缓存目录是否存在"""
    cmd = f'test -e {shlex.quote(CACHE_ROOT)} && echo YES || echo NO'
    try:
        r = subprocess.run(executor + [cmd], capture_output=True, text=True, timeout=20)
        return r.returncode == 0 and "YES" in r.stdout
    except Exception:
        return False


# ---------- 临时目录清理 ----------
def clean_temp():
    p = Path(TEMP_DIR)
    try:
        resolved = str(p.resolve())
    except Exception:
        resolved = TEMP_DIR
    if resolved in DANGEROUS_PATHS:
        log(f"危险路径，拒绝删除：{p}")
        return
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
        log(f"临时目录已清理！：{TEMP_DIR}")
    else:
        log("临时目录是干净的")


# ---------- 复制缓存 ----------
def copy_cache_direct():
    if Path(TEMP_DIR).exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    try:
        shutil.copytree(CACHE_ROOT, TEMP_DIR, dirs_exist_ok=True)
        return True
    except Exception as e:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        log(f"复制缓存失败：{e}")
        return False


def copy_cache_with_executor(executor):
    if Path(TEMP_DIR).exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    cmd = (
        f'mkdir -p {shlex.quote(TEMP_DIR)} && '
        f'cp -a {shlex.quote(CACHE_ROOT + "/.")} {shlex.quote(TEMP_DIR + "/")} && '
        f'chmod -R 777 {shlex.quote(TEMP_DIR)}'
    )
    try:
        r = subprocess.run(executor + [cmd], capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            log(f"复制缓存失败：{r.stderr.strip()[-300:]}")
            return False
    except Exception as e:
        log(f"复制缓存失败：{e}")
        return False
    return True


def check_copied_cache(root):
    p = Path(root)
    if not p.exists():
        log(f"缓存目录不存在！：{root}")
        return False
    if next(p.rglob("entry.json"), None) is None:
        log("目录里没找到有效 B 站缓存，可能是 B 站版本未受到支持？")
        return False
    return True


# ---------- 刷新相册 ----------
def refresh_gallery():
    if shutil.which("termux-media-scan") is None:
        log("未安装 termux-media-scan，相册可能稍后自动扫描 Movies 目录。")
        return

    for args in (["-r", OUTPUT_DIR], [OUTPUT_DIR]):
        try:
            r = subprocess.run(
                ["termux-media-scan"] + args,
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                log("已广播相册刷新。")
                return
        except Exception as e:
            log(f"刷新相册失败：{e}")
            return

    log("termux-media-scan 返回非零，相册可能稍后自动刷新。")


# ---------- 合成 ----------
def make_title(meta, folder):
    title = (meta.get("title") or folder.name or "untitled").replace("/", "_")[:76]
    page = meta.get("page_data") or {}
    part = (page.get("part") or "").replace("/", "_")[:40]
    if part:
        title = f"{title}_{part}"
    return title or "untitled"


def unique_output_path(title):
    out = Path(OUTPUT_DIR) / f"{title}.mp4"
    n = 1
    while out.exists():
        out = Path(OUTPUT_DIR) / f"{title}_{n}.mp4"
        n += 1
    return out


def find_media(folder):
    video = next(folder.rglob("video.m4s"), None) or next(folder.rglob("*.blv"), None)
    audio = next(folder.rglob("audio.m4s"), None)
    return video, audio


def merge_all(source_root):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    entries = list(Path(source_root).rglob("entry.json"))
    total = len(entries)
    if total == 0:
        log("未找到任何 entry.json，无法合成。")
        return

    log(f"共发现 {total} 个缓存条目，开始处理…")
    count = 0
    failed = []

    for i, entry in enumerate(entries, 1):
        folder = entry.parent
        log(f"[{i}/{total}] {folder.name}")

        try:
            with open(entry, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            log(f"  跳过（entry.json 读取失败）：{e}")
            failed.append((folder.name, f"entry.json 读取失败：{e}"))
            continue

        title = make_title(meta, folder)

        video, audio = find_media(folder)
        if not video or not audio:
            missing = []
            if not video:
                missing.append("视频")
            if not audio:
                missing.append("音频")
            log(f"  跳过（缺 {'、'.join(missing)} 文件）")
            failed.append((title, f"缺 {'、'.join(missing)} 文件"))
            continue

        out = unique_output_path(title)

        if DRY_RUN:
            log(f"  [dry-run] 将输出：{out.name}")
            count += 1
            continue

        cmd = [
            "ffmpeg",
            "-i", str(video),
            "-i", str(audio),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c", "copy",
            "-y", str(out),
        ]
        try:
            subprocess.run(
                cmd, check=True, timeout=900,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log(f"  成功: {out.name}")
            count += 1
        except subprocess.CalledProcessError as e:
            err = e.stderr[-300:].decode("utf-8", "ignore") if e.stderr else "未知错误"
            log(f"  失败: {err}")
            failed.append((title, err))
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass
        except subprocess.TimeoutExpired:
            log("  失败: ffmpeg 超时")
            failed.append((title, "ffmpeg 超时"))
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass

    log(f"\n共完成 {count} 个文件，输出目录：{OUTPUT_DIR}")

    if failed:
        log(f"失败 {len(failed)} 个：")
        for t, e in failed:
            log(f"  - {t}: {e}")

    if count > 0 and not DRY_RUN:
        refresh_gallery()


# ---------- 菜单动作 ----------
def action_clean():
    clean_temp()


def action_merge():
    log("== 运行前检测 ==")

    if not check_ffmpeg():
        return
    log("ffmpeg 已安装")

    readable, exists = can_read_cache()

    executor = None
    if not exists or not readable:
        executor = detect_privileged_executor()

    if not exists:
        if executor and path_exists_as_privileged(executor):
            exists = True
            log("普通用户不可见，但提权后确认缓存目录存在。")
        else:
            log(f"缓存目录不存在：{CACHE_ROOT}")
            log("请确认 B 站已下载过视频，或缓存路径是否被修改。")
            if executor is None:
                log("（也未能检测到 root / rish，无法进一步确认）")
            return

    if readable:
        if DRY_RUN:
            log("dry-run：跳过缓存复制，直接扫描原目录。")
            source_root = CACHE_ROOT
        else:
            log("缓存目录可直接读取，开始复制…")
            if not copy_cache_direct():
                return
            source_root = TEMP_DIR
    else:
        log("无法直接读取缓存目录。")
        log("Android 11 及以上版本限制了对 Android/data 的访问。")
        if executor is None:
            log("未检测到可用的提权方式：")
            log("  - 请授予 root 权限后重试，或")
            log("  - 使用 rish（Shizuku）运行本脚本")
            log("    rish 通过 Shizuku 以 shell 权限运行，可绕过该限制。")
            return
        who = "root" if executor[0] == "su" else "rish"
        log(f"使用 {who} 权限复制缓存…")
        if not copy_cache_with_executor(executor):
            return
        source_root = TEMP_DIR

    if not check_copied_cache(source_root):
        return
    log("目录中检测到有效缓存")

    if not check_output_writable():
        return
    log("输出目录可写")

    log("\n== 开始合并 ==")
    merge_all(source_root)


# ---------- 主菜单 ----------
def main():
    setup_logging()
    log("========== B 站缓存合并工具 ==========")

    if DRY_RUN:
        log("（dry-run 模式：只显示将输出的文件，不实际合成）")

    if not ensure_storage_permission():
        log("未获得存储权限，无法继续。请授权后重新运行。")
        return

    clean_temp()

    while True:
        log("\n1. 清理临时缓存")
        log("2. 开始寻找并合成视频")
        log("0. 退出")
        try:
            choice = input("请输入选项：").strip()
        except (EOFError, KeyboardInterrupt):
            log("\n已退出")
            clean_temp()
            break

        if choice == "1":
            action_clean()
        elif choice == "2":
            try:
                action_merge()
            except KeyboardInterrupt:
                log("\n用户中断。")
            except Exception as e:
                log(f"发生异常：{e}")
            finally:
                clean_temp()
        elif choice == "0":
            log("退出前清理临时目录…")
            clean_temp()
            log("已退出")
            break
        else:
            log("无效选项，请重新输入")


if __name__ == "__main__":
    main()