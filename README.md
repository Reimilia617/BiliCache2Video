# BiliCache2Video
基于Termux为安卓用户制作的将哔哩哔哩的离线缓存转换为本地视频的工具

# 快速开始

## 前置软件
1. 缓存了视频的哔哩哔哩客户端(目前仅在9.13.0版本测试通过)
2. 安装了ffmpeg和python3的termux
3. shell权限或root权限并赋予给termux(目前仅测试过root权限)
- 最好安装Termux:API这个软件和Termux内安装"termux-api"这个包，并赋予Termux:API文件与媒体权限

## 使用方法
1. 下载仓库内的"main.py"并拷贝到任意可读写目录(建议放在内部存储根目录方便寻找)
2. 进入Termux执行以下命令
```bash
termux-setup-storage
cd /sdcard          ("/sdcard"换成存放py脚本的目录)
python main.py
```

# 特性
因从Android11开始普通应用没有访问"Android/data"的权限，需要shell用户或root用户才可读写，所以我们搞出了：

## 权限管理
- 自动检测权限等级(root或shell)，然后根据权限等级自动选择正确的命令
- 在使用高权限确认哔哩哔哩缓存目录存在后会将其复制到临时目录以防止多次调用高权限
- 在结束脚本运行时会自动清理缓存目录

## 自动刷新
- 使用ffmpeg合并视频后会使用"termux-media-scan"刷新媒体库(如果正确配置了Termux:API)

## 容错措施
- 若合成视频时出现了错误则会跳过这个视频并报错，不影响剩下的任务

# 提醒
- 若你是Root用户需要记得给Termux权限，或使用shizuku
- 对于无Root用户，可以使用shizuku临时授权，若无法使用shizuku可尝试用Android原生"文件"应用将整个缓存目录手动放到普通应用可读写的位置后编辑py脚本使其扫描的目录指向复制出的缓存文件夹
- 对于Android11以下的用户，可尝试编辑脚本将逻辑和操作修改一下
- AI是个好东西，你看不懂脚本，但是它看得懂

# 贡献者
- Deepseek: 提供部分判断逻辑代码
- Reimilia617: 项目发起者，创作灵感来源，大部分代码提供者