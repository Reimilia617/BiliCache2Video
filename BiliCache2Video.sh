#!/data/data/com.termux/files/usr/bin/bash
# B 站缓存合并工具 - root 版（Termux 执行）
# 用法: bash bili_merge.sh

CACHE_ROOT="${BILI_CACHE_ROOT:-/storage/emulated/0/Android/data/tv.danmaku.bili/download}"
TEMP_DIR="${BILI_TEMP_DIR:-/storage/emulated/0/Download/bili_cache_tmp}"
OUTPUT_DIR="${BILI_OUTPUT_DIR:-/storage/emulated/0/Movies/BiliMerge}"

DANGEROUS_PATHS="/ /storage /sdcard /storage/emulated /storage/emulated/0"

# ---------- 日志（固定在脚本自身目录） ----------
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
LOG_FILE="$SCRIPT_DIR/merge.log"

log() {
    local msg="$*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null
}

# ---------- root 检测 ----------
detect_root() {
    log "正在检测 root（如弹出授权请点允许）…"
    if command -v su >/dev/null 2>&1; then
        if su -c "id" 2>/dev/null | grep -q "uid=0"; then
            log "root 权限已获得。"
            return 0
        fi
    fi
    log "未检测到 root 权限，无法访问 Android/data 缓存目录。"
    return 1
}

# ---------- 清理 ----------
clean_temp() {
    [ -z "$TEMP_DIR" ] && return
    local d
    for d in $DANGEROUS_PATHS; do
        if [ "$TEMP_DIR" = "$d" ]; then
            log "危险路径，拒绝删除：$TEMP_DIR"
            return
        fi
    done
    if [ -e "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR" 2>/dev/null
        log "临时目录已清理：$TEMP_DIR"
    else
        log "临时目录是干净的。"
    fi
}

# ---------- 复制缓存（root） ----------
copy_cache_with_root() {
    rm -rf "$TEMP_DIR" 2>/dev/null
    local qt qs
    qt=$(printf '%q' "$TEMP_DIR")
    qs=$(printf '%q' "$CACHE_ROOT")
    local cmd="mkdir -p $qt && cp -a $qs/. $qt/ && chmod -R 777 $qt"
    if su -c "$cmd" 2>/dev/null; then
        return 0
    fi
    log "root 复制缓存失败，请检查 su 授权。"
    return 1
}

check_copied_cache() {
    local root="$1"
    [ -e "$root" ] || { log "缓存目录不存在：$root"; return 1; }
    find "$root" -name entry.json -type f 2>/dev/null | head -n1 | grep -q . \
        || { log "目录里没找到有效 B 站缓存。"; return 1; }
    return 0
}

check_output_writable() {
    mkdir -p "$OUTPUT_DIR" 2>/dev/null || { log "无法创建输出目录：$OUTPUT_DIR"; return 1; }
    local t="$OUTPUT_DIR/.write_test"
    if echo x > "$t" 2>/dev/null; then
        rm -f "$t" 2>/dev/null
        return 0
    fi
    log "输出目录不可写：$OUTPUT_DIR"
    return 1
}

# ---------- 元信息 ----------
TITLE=""
make_title() {
    local entry="$1" folder="$2" title part
    if command -v jq >/dev/null 2>&1; then
        title=$(jq -r '.title // empty' "$entry" 2>/dev/null)
        part=$(jq -r '.page_data.part // empty' "$entry" 2>/dev/null)
    else
        title=$(grep -o '"title"[[:space:]]*:[[:space:]]*"[^"]*"' "$entry" 2>/dev/null \
                | head -n1 | sed 's/.*:[[:space:]]*"\(.*\)"$/\1/')
        part=$(grep -o '"part"[[:space:]]*:[[:space:]]*"[^"]*"' "$entry" 2>/dev/null \
                | head -n1 | sed 's/.*:[[:space:]]*"\(.*\)"$/\1/')
    fi
    [ -z "$title" ] && title=$(basename "$folder")
    [ -z "$title" ] && title="untitled"
    title=${title//\//_}; title=${title:0:76}
    part=${part//\//_};   part=${part:0:40}
    if [ -n "$part" ]; then TITLE="${title}_${part}"; else TITLE="$title"; fi
    [ -z "$TITLE" ] && TITLE="untitled"
}

unique_output_path() {
    local title="$1" out="$OUTPUT_DIR/${title}.mp4" n=1
    while [ -e "$out" ]; do
        out="$OUTPUT_DIR/${title}_${n}.mp4"
        n=$((n + 1))
    done
    echo "$out"
}

VIDEO_PATH=""; AUDIO_PATH=""
find_media() {
    local folder="$1"
    VIDEO_PATH=$(find "$folder" -name 'video.m4s' -type f 2>/dev/null | head -n1)
    [ -z "$VIDEO_PATH" ] && VIDEO_PATH=$(find "$folder" -name '*.blv' -type f 2>/dev/null | head -n1)
    AUDIO_PATH=$(find "$folder" -name 'audio.m4s' -type f 2>/dev/null | head -n1)
}

# ---------- 合成 ----------
merge_all() {
    local source_root="$1"
    mkdir -p "$OUTPUT_DIR" || return 1

    local entries=()
    while IFS= read -r line; do entries+=("$line"); done \
        < <(find "$source_root" -name entry.json -type f 2>/dev/null)

    local total=${#entries[@]}
    if [ "$total" -eq 0 ]; then
        log "未找到任何 entry.json，无法合成。"
        return 1
    fi

    log "共发现 $total 个缓存条目，开始处理…"

    local count=0 i=0
    local ft=() fr=()

    for entry in "${entries[@]}"; do
        i=$((i + 1))
        local folder; folder=$(dirname "$entry")
        log "[$i/$total] $(basename "$folder")"

        make_title "$entry" "$folder"
        local title="$TITLE"

        find_media "$folder"
        local video="$VIDEO_PATH" audio="$AUDIO_PATH"

        if [ -z "$video" ] || [ -z "$audio" ]; then
            local missing=""
            [ -z "$video" ] && missing="视频"
            [ -z "$audio" ] && missing="${missing:+$missing、}音频"
            log "  跳过（缺 $missing 文件）"
            ft+=("$title"); fr+=("缺 $missing 文件")
            continue
        fi

        local out; out=$(unique_output_path "$title")

        if ffmpeg -i "$video" -i "$audio" \
                  -map 0:v:0 -map 1:a:0 \
                  -c copy -y "$out" >/dev/null 2>/tmp/bili_ff.err; then
            log "  成功：$(basename "$out")"
            count=$((count + 1))
        else
            log "  失败：$(tail -c 300 /tmp/bili_ff.err 2>/dev/null)"
            ft+=("$title"); fr+=("ffmpeg 合成失败")
            rm -f "$out" 2>/dev/null
        fi
    done

    log ""
    log "共完成 $count 个文件"
    if [ "$count" -gt 0 ]; then
        log "视频保存位置：$OUTPUT_DIR"
    fi
    if [ ${#ft[@]} -gt 0 ]; then
        log "失败 ${#ft[@]} 个："
        local k
        for k in "${!ft[@]}"; do
            log "  - ${ft[$k]}: ${fr[$k]}"
        done
    fi
    return 0
}

# ---------- 菜单动作 ----------
action_clean() {
    clean_temp
}

action_merge() {
    log "== 运行前检测 =="

    if ! command -v ffmpeg >/dev/null 2>&1; then
        log "未检测到 ffmpeg，请先执行：pkg install ffmpeg"
        return 1
    fi
    log "ffmpeg 已安装"

    if [ ! -e "$CACHE_ROOT" ]; then
        log "缓存目录不存在：$CACHE_ROOT"
        log "请确认 B 站已下载过视频。"
        return 1
    fi

    log "使用 root 复制缓存到临时目录…"
    copy_cache_with_root || return 1
    local source_root="$TEMP_DIR"

    check_copied_cache "$source_root" || return 1
    log "目录中检测到有效缓存"

    check_output_writable || return 1
    log "输出目录可写"

    log ""
    log "== 开始合并 =="
    merge_all "$source_root"
}

# ---------- 主菜单 ----------
main() {
    log "========== B 站缓存合并工具（root 版） =========="
    log "日志文件：$LOG_FILE"

    detect_root || exit 1

    while true; do
        log ""
        log "1. 清理临时缓存"
        log "2. 开始检测并合并视频"
        log "0. 退出"
        printf "请输入选项："
        local choice
        if ! read -r choice; then
            log ""
            log "已退出"
            clean_temp
            break
        fi
        choice=$(echo "$choice" | tr -d '[:space:]')

        case "$choice" in
            1) action_clean ;;
            2) action_merge ;;
            0)
                log "退出前清理临时目录…"
                clean_temp
                log "已退出"
                break
                ;;
            *) log "无效选项，请重新输入" ;;
        esac
    done
}

trap 'log ""; log "用户中断。"; clean_temp; exit 130' INT

main