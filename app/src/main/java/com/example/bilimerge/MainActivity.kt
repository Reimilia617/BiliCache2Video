class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PrivilegedShell.init()
        setContent { MiuixTheme { MergeScreen(this) } }
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
        Text("BiliMerge", style = MaterialTheme.typography.headlineMedium)

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
                    val result = doMerge(cachePath) { msg ->
                        activity.runOnUiThread { logText += "\n$msg" }
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