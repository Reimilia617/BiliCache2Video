plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

android {
    namespace = "com.example.bilimerge"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.bilimerge"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
}

chaquopy {
    defaultConfig {
        version = "3.10"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")

    // Miuix 核心 UI，Android 变体
    implementation("top.yukonga.miuix.kmp:miuix-ui-android:0.9.1")

    // FFmpegKit 维护版，包名 API 不变，只换 groupId [citation:1][citation:7]
    implementation("dev.ffmpegkit-maintained:ffmpeg-kit-full:8.1.7")

    // libsu root shell
    implementation("com.github.topjohnwu.libsu:core:6.0.0")
}