# BiliCache2Video
基于 Termux 为安卓用户制作的将哔哩哔哩的离线缓存转换为本地视频的工具

# 快速开始

## 前置软件
1. 缓存了视频的哔哩哔哩客户端（目前仅在 9.13.0 版本测试通过）
2. 安装了 ffmpeg 和 python3 的 Termux
3. ~~shell 权限或 root 权限并赋予给 termux（目前仅测试过 root 权限）~~
   root 权限或 rish（基于 Shizuku 的 shell 权限），并赋予给 Termux（目前 root 与 rish 均已在脚本层面支持，但实际设备测试仍以 root 为主）
- 最好安装 Termux:API 这个软件和 Termux 内安装 `termux-api` 这个包，并赋予 Termux:API 文件与媒体权限

## 使用方法
1. 下载仓库内的 `main.py` 并拷贝到任意可读写目录（建议放在内部存储根目录方便寻找）
2. 进入 Termux 执行以下命令
```bash
termux-setup-storage
cd /sdcard          ("/sdcard"换成存放 py 脚本的目录)
python main.py
```
3. 想先看看会输出哪些文件而不实际合并？可以加 `--dry-run`：
```bash
python main.py --dry-run
```

# 特性
因从 Android 11 开始普通应用没有访问 `Android/data` 的权限，需要 shell 用户或 root 用户才可读写，所以我们搞出了：

## 权限管理
- ~~自动检测权限等级（root 或 shell），然后根据权限等级自动选择正确的命令~~
  改为**实测缓存目录能否读取**，不再靠版本号或用户身份猜测；能读就直接复制，读不了再尝试提权
- 提权方式支持 `su`（root）与 `rish`（Shizuku 的 shell 权限），脚本会自动探测哪一种可用
- 在使用高权限确认哔哩哔哩缓存目录存在后会将其复制到临时目录以防止多次调用高权限
- 复制后会 `chmod -R 777` 临时目录，避免 root 复制导致 Termux 普通用户读不了后续文件
- 在结束脚本运行时会自动清理缓存目录
- 启动时会先检测存储权限，没有就自动拉起 `termux-setup-storage`，等待用户点允许后再继续

## 自动刷新
- 使用 ffmpeg 合并视频后会使用 `termux-media-scan` 刷新媒体库（如果正确配置了 Termux:API）

## 容错措施
- 若合成视频时出现了错误则会跳过这个视频并报错，不影响剩下的任务
- 失败时会清理可能残留的半成品 `.mp4`，并在结束时统一汇总失败条目
- 支持多分 P 命名（自动附加 `page_data.part`），同名文件自动追加 `_1`、`_2` 后缀，不覆盖已有文件
- 临时目录清理带危险路径白名单，拒绝删除 `/`、`/storage`、`/sdcard` 等路径
- 日志同时输出到终端和 `merge.log` 文件，后台运行也不丢记录

# 提醒
- 若你是 Root 用户需要记得给 Termux 权限，或使用 Shizuku
- 对于无 Root 用户，可以使用 Shizuku + rish 临时授权，脚本已内置 rish 检测；若无法使用 Shizuku，可尝试用 Android 原生“文件”应用将整个缓存目录手动放到普通应用可读写的位置后，编辑 py 脚本或设置环境变量 `BILI_CACHE_ROOT` 使其扫描复制出的缓存文件夹
- ~~对于 Android 11 以下的用户，可尝试编辑脚本将逻辑和操作修改一下~~
  脚本现在不再依赖版本号判断，Android 11 以下只要能读到缓存目录就会直接走普通复制分支，无需改动逻辑
- 首次使用 rish 请先在 Termux 里手动运行一次 `rish` 完成初始化，否则脚本会提示调用失败
- AI 是个好东西，你看不懂脚本，但是它看得懂

# 贡献者
- Deepseek：提供部分判断逻辑代码
- Reimilia617：项目发起者，创作灵感来源，大部分代码提供者