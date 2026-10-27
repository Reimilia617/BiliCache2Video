package com.example.bilimerge

import com.topjohnwu.superuser.Shell

object PrivilegedShell {
    fun init() {
        Shell.enableVerboseLogging = true
        Shell.setDefaultBuilder(
            Shell.Builder.create()
                .setFlags(Shell.FLAG_MOUNT_MASTER)
                .setTimeout(30)
        )
    }

    fun isRootAvailable(): Boolean {
        return try {
            val result = Shell.cmd("id").exec()
            result.isSuccess && result.out.any { it.contains("uid=0") }
        } catch (_: Exception) { false }
    }

    fun pathExists(path: String): Boolean {
        return try {
            Shell.cmd("test -e \"$path\" && echo YES || echo NO").exec()
                .out.any { it.contains("YES") }
        } catch (_: Exception) { false }
    }

    fun copyDirectory(src: String, dst: String): Boolean {
        return try {
            Shell.cmd("mkdir -p \"$dst\" && cp -a \"$src/.\" \"$dst/\" && chmod -R 777 \"$dst\"")
                .exec().isSuccess
        } catch (_: Exception) { false }
    }
}