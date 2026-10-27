package com.example.bilimerge

import org.json.JSONObject
import java.io.File

data class MergeTask(
    val title: String,
    val videoPath: String,
    val audioPath: String
)

object CacheScanner {
    fun scan(root: File): List<MergeTask> {
        val tasks = mutableListOf<MergeTask>()
        root.walkTopDown()
            .filter { it.name == "entry.json" }
            .forEach { entryFile ->
                try {
                    val meta = JSONObject(entryFile.readText(Charsets.UTF_8))
                    val folder = entryFile.parentFile ?: return@forEach
                    val base = meta.optString("title", folder.name).replace("/", "_").take(76)
                    val part = meta.optJSONObject("page_data")
                        ?.optString("part", "")?.replace("/", "_")?.take(40) ?: ""
                    val title = if (part.isNotEmpty()) "${base}_$part" else base

                    // 递归查找，优先 video.m4s，找不到再用 *.blv 兜底
                    val video = folder.walkTopDown()
                        .firstOrNull { it.name == "video.m4s" }
                        ?: folder.walkTopDown()
                            .firstOrNull { it.extension == "blv" }
                    val audio = folder.walkTopDown()
                        .firstOrNull { it.name == "audio.m4s" }

                    if (video != null && audio != null) {
                        tasks.add(MergeTask(title, video.absolutePath, audio.absolutePath))
                    }
                } catch (_: Exception) { }
            }
        return tasks
    }
}