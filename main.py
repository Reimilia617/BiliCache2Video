import os
import json
import shutil
import subprocess
from pathlib import Path

CACHE_ROOT = "/storage/emulated/0/Android/data/tv.danmaku.bili/download"
TEMP_DIR = "/storage/emulated/0/Download/bili_cache_tmp"
OUTPUT_DIR = "/storage/emulated/0/Movies/BiliMerge"  # Movies 目录，相册会自动扫描


# ---------- 基础检测 ----------
def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("未检测到ffmpeg，可能是未安装或未在termux内执行？")
        return False
    return True


def check_user():
    """返回 'root' / 'shell' / None"""
    try:
        r = subprocess.run(["su", "-c", "id"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "uid=0" in r.stdout:
            return "root"
    except Exception:
        pass
    try:
        r = subprocess.run(["id"], capture_output=True, text=True, timeout=5)
        if "uid=2000" in r.stdout:
            return "shell"
    except Exception:
        pass
    return None


# ---------- 临时目录清理 ----------
def clean_temp():
    p = Path(TEMP_DIR)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
        print(f"临时目录已清理！：{TEMP_DIR}")
    else:
        print("临时目录不存在啊，咋清理？")


# ---------- 复制缓存 ----------
def copy_cache(user):
    if Path(TEMP_DIR).exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

    if user == "root":
        cmd = f'mkdir -p "{TEMP_DIR}" && cp -r "{CACHE_ROOT}/." "{TEMP_DIR}/"'
        try:
            r = subprocess.run(["su", "-c", cmd], capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                print(f"复制缓存失败：{r.stderr.strip()[-300:]}")
                return False
        except Exception as e:
            print(f"以Root权限复制缓存失败：{e}")
            return False

    elif user == "shell":
        try:
            shutil.copytree(CACHE_ROOT, TEMP_DIR, dirs_exist_ok=True)
        except Exception as e:
            print(f"复制缓存失败：{e}")
            return False

    else:
        return False

    return True


def check_copied_cache():
    p = Path(TEMP_DIR)
    if not p.exists():
        print(f"临时目录不存在！：{TEMP_DIR}")
        return False
    if next(p.rglob("entry.json"), None) is None:
        print("复制后的目录里没找到有效 B站缓存，可能是B站版本未受到支持？")
        return False
    return True


def check_output_writable():
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        test = Path(OUTPUT_DIR) / ".write_test"
        test.write_text("test")
        test.unlink()
        return True
    except Exception as e:
        print(f"输出目录无权限读写！：{OUTPUT_DIR}（{e}）")
        return False


# ---------- 刷新相册 ----------
def refresh_gallery():
    """优先用 termux-media-scan，失败则静默跳过"""
    try:
        r = subprocess.run(
            ["termux-media-scan", "-r", OUTPUT_DIR],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            print("已广播相册刷新。")
        else:
            print("termux-media-scan 返回非零，相册可能稍后自动刷新。")
    except FileNotFoundError:
        print("未安装 termux-media-scan，相册可能稍后自动扫描 Movies 目录。")
    except Exception as e:
        print(f"刷新相册失败：{e}")


# ---------- 合成 ----------
def merge_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count = 0
    for entry in Path(TEMP_DIR).rglob("entry.json"):
        folder = entry.parent

        try:
            with open(entry, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"跳过（entry.json 读取失败）：{entry}（{e}）")
            continue

        title = meta.get("title", folder.name).replace("/", "_")[:80]

        video = next(folder.rglob("video.m4s"), None)
        audio = next(folder.rglob("audio.m4s"), None)
        if not video or not audio:
            print(f"跳过（缺音视频文件）：{folder}")
            continue

        out = Path(OUTPUT_DIR) / f"{title}.mp4"
        n = 1
        while out.exists():
            out = Path(OUTPUT_DIR) / f"{title}_{n}.mp4"
            n += 1

        cmd = [
            "ffmpeg", "-i", str(video), "-i", str(audio),
            "-c:v", "copy", "-c:a", "copy",
            "-y", str(out)
        ]
        try:
            subprocess.run(cmd, check=True, timeout=300,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE)
            print(f"成功: {out.name}")
            count += 1
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode(errors="ignore")[-300:] if e.stderr else ""
            print(f"失败 {title}: {err}")

    print(f"\n共完成 {count} 个文件，输出目录：{OUTPUT_DIR}")
    if count > 0:
        refresh_gallery()


# ---------- 菜单动作 ----------
def action_clean():
    clean_temp()


def action_merge():
    print("== 运行前检测 ==")

    if not check_ffmpeg():
        return
    print("ffmpeg 已安装")

    user = check_user()
    if user is None:
        print("当前为普通用户，无法访问缓存目录！")
        print("   请检查权限后再试！")
        return
    print(f"当前用户权限：{user}")

    print("正在复制缓存到临时目录")
    if not copy_cache(user):
        return
    print("缓存已复制到临时目录")

    if not check_copied_cache():
        return
    print("临时目录中检测到有效缓存")

    if not check_output_writable():
        return
    print("输出目录可写")

    print("\n== 开始合并 ==")
    merge_all()


# ---------- 主菜单 ----------
def main():
    while True:
        print("\n========== B 站缓存合并工具 ==========")
        print("1. 清理临时缓存")
        print("2. 开始寻找并合成视频")
        print("0. 退出")
        choice = input("请输入选项：").strip()

        if choice == "1":
            action_clean()
        elif choice == "2":
            try:
                action_merge()
            except KeyboardInterrupt:
                print("\n用户中断。")
            except Exception as e:
                print(f"发生异常：{e}")
            finally:
                clean_temp()
        elif choice == "0":
            print("退出前清理临时目录…")
            clean_temp()
            print("已退出")
            break
        else:
            print("无效选项，请重新输入")


if __name__ == "__main__":
    main()