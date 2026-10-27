package com.example.bilimerge

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.arthenica.ffmpegkit.FFmpegKit
import com.arthenica.ffmpegkit.ReturnCode
import top.yukonga.miuix.kmp.theme.MiuixTheme
import java.io.File

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PrivilegedShell.init()
        requestAllFilesAccess()
        setContent { MiuixTheme { MergeScreen(this) } }
    }

    private fun requestAllFilesAccess() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    startActivity(intent)
                } catch (_: Exception) { }
            }
        }
    }
}

@Composable
fun MergeScreen(activity: ComponentActivity) {
    var cachePath by remember {
        mutableStateOf("/storage/emulated/0/Android/data/tv.danmaku.bili/download")
    }
    var logText by remember { mutableStateOf("就绪") }
    var isRunning by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("BiliCache2Video", style = MaterialTheme.typography.headlineMedium)

        OutlinedTextField(
            value = cachePath,
            onValueChange = { cachePath = it },
            label = { Text("缓存路径") },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isRunning
        )

        Button(
            onClick = {
                isRunning = true
                logText = "开始处理…"
                Thread {
                    val result = try {
                        val tempRoot = activity.getExternalFilesDir(null) ?: activity.filesDir
                        doMerge(cachePath, tempRoot) { msg ->
                            activity.runOnUiThread { logText += "\n$msg" }
                        }
                    } catch (e: Throwable) {
                        "异常：${e.javaClass.simpleName}: ${e.message}"
                    }
                    activity.runOnUiThread {
                        logText += "\n$result"
                        isRunning = false
                    }
                }.start()
            },
            enabled = !isRunning,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isRunning) "处理中…" else "扫描并合并")
        }

        Text("日志", style = MaterialTheme.typography.titleMedium)
        Text(
            text = logText,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

private fun doMerge(cachePath: String, tempRoot: File, log: (String) -> Unit): String {
    if (!PrivilegedShell.isRootAvailable()) return "Root 未授权"
    if (!PrivilegedShell.pathExists(cachePath)) return "路径不存在：$cachePath"

    val tempDir = File(tempRoot, "bili_merge_tmp")
    try {
        if (tempDir.exists()) tempDir.deleteRecursively()
        tempDir.mkdirs()
    } catch (e: Exception) {
        return "创建临时目录失败：${e.message}"
    }

    log("Root 复制缓存…")
    if (!PrivilegedShell.copyDirectory(cachePath, tempDir.absolutePath)) {
        return "复制失败，请确认 Root 授权"
    }

    log("扫描缓存…")
    val tasks = try {
        CacheScanner.scan(tempDir)
    } catch (e: Exception) {
        return "扫描异常：${e.message}"
    }
    if (tasks.isEmpty()) return "未找到有效缓存（临时目录：${tempDir.absolutePath}）"

    val outputDir = File(
        Environment.getExternalStorageDirectory(),
        "Movies/BiliMerge"
    )
    try {
        outputDir.mkdirs()
    } catch (_: Exception) { }
    log("发现 ${tasks.size} 个任务，开始 FFmpeg 合并…")

    var success = 0
    tasks.forEachIndexed { i, task ->
        val out = File(outputDir, "${task.title}.mp4")
        val cmd = "-i \"${task.videoPath}\" -i \"${task.audioPath}\" " +
                "-map 0:v:0 -map 1:a:0 -c copy -y \"${out.absolutePath}\""
        try {
            val session = FFmpegKit.execute(cmd)
            if (ReturnCode.isSuccess(session.returnCode)) {
                success++
                log("[${i + 1}/${tasks.size}] 成功: ${task.title}")
            } else {
                log("[${i + 1}/${tasks.size}] 失败: ${task.title}")
                out.delete()
            }
        } catch (e: Throwable) {
            log("[${i + 1}/${tasks.size}] 异常: ${task.title} (${e.message})")
        }
    }
    return "完成：$success / ${tasks.size}，输出：${outputDir.absolutePath}"
}