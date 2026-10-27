plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.example.bilimerge"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.example.bilimerge"
        minSdk = 26
        targetSdk = 37
        versionCode = 14
        versionName = "Beta.261028.Patch14"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures { compose = true }
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation(platform("androidx.compose:compose-bom:2025.05.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")

    // 解决 AndroidManifest 中 Theme.Material3.DayNight.NoActionBar 的资源链接
    implementation("com.google.android.material:material:1.14.0")

    // Miuix 核心 UI，Android 变体
    implementation("top.yukonga.miuix.kmp:miuix-ui-android:0.9.1")

    // FFmpegKit 维护版
    implementation("dev.ffmpegkit-maintained:ffmpeg-kit-full:8.1.7")

    // libsu root shell
    implementation("com.github.topjohnwu.libsu:core:6.0.0")
}