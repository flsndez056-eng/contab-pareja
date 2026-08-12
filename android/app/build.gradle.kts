plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.ksp)
}

if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

val productionApiBaseUrl = providers.gradleProperty("CONTAB_API_BASE_URL")
    .orElse("https://contab.siptrapollo.online/")
    .get()
    .let { if (it.endsWith('/')) it else "$it/" }

val debugApiBaseUrl = providers.gradleProperty("CONTAB_DEBUG_API_BASE_URL")
    .orElse(productionApiBaseUrl)
    .get()
    .let { if (it.endsWith('/')) it else "$it/" }

android {
    namespace = "com.flsndez.contabpareja"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.flsndez.contabpareja"
        minSdk = 23
        targetSdk = 37
        versionCode = 10
        versionName = "1.0.0-rc1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true
        buildConfigField("String", "API_BASE_URL", "\"$productionApiBaseUrl\"")
    }

    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"$debugApiBaseUrl\"")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging.resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.fragment.ktx)
    implementation(libs.androidx.biometric)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)
    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.androidx.datastore.preferences)

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)

    implementation(libs.retrofit.core)
    implementation(libs.retrofit.gson)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.zxing.core)
    coreLibraryDesugaring(libs.desugar.jdk.libs)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
    arg("room.generateKotlin", "true")
}
