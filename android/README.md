# B: Android TWA (Part 2, Part 4 app)

This folder comes from the course's Trusted Web Activity template. The app has no screens of its own: `LauncherActivity` (android-browser-helper) opens A's website in Chrome, full screen and without an address bar, and login, group chat, and topic Q&A all happen on the website.

## Configuration

| Item | Value | File |
|---|---|---|
| Package name / applicationId | `edu.usc.ee542.f1assistant` | `app/build.gradle` |
| App name | F-1 Student Desk | `app/src/main/res/values/strings.xml` |
| URL it opens | `https://desktop-jdferfe.taile24d30.ts.net/` (A's website) | `defaultUrl` in `strings.xml` |
| Signing | Release builds use `keystore/f1assistant-release.jks`, with settings in `keystore.properties` (neither is committed) | `signingConfigs` in `app/build.gradle` |
| Gradle | Wrapper 8.13 (the template lacked `gradle-wrapper.jar`, so it was generated with a local Gradle and added), AGP 8.13.0, JDK 17 | `gradle/wrapper/` |

SHA-256 fingerprint of the signing certificate:

```
40:C7:CF:68:1A:2E:C4:25:14:6E:20:A3:27:40:E4:3C:E7:BD:41:AB:AF:E5:6F:EA:FF:6D:5D:8B:01:4E:FE:96
```

The `assetlinks.json` for A is `evidence/b-part2/assetlinks.json`; it goes on the website at `/.well-known/assetlinks.json`. The package name and fingerprint must match the values above; otherwise Chrome does not trust the app and falls back to a Custom Tab with an address bar.

## Build

Requires JDK 17 and the Android SDK (platform 34, build-tools 34.0.0). Put `sdk.dir=<SDK path>` in `local.properties` (not committed).

```sh
cd android
./gradlew assembleDebug          # debug build (debug signing), can be installed on an emulator directly
./gradlew assembleRelease        # with keystore.properties, builds a release APK signed with the release key
# output: app/build/outputs/apk/{debug,release}/
```

Without `keystore.properties` the release build is unsigned; debug builds are not affected. To verify the signature:

```sh
$ANDROID_HOME/build-tools/34.0.0/apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
```

## Install and verify

```sh
adb install -r app/build/outputs/apk/release/app-release.apk
```

Verification order:
1. After A deploys `assetlinks.json`, `curl https://desktop-jdferfe.taile24d30.ts.net/.well-known/assetlinks.json` should return the content above.
2. Install the **signed release build** (the fingerprint must match; the debug build uses a different key and shows an address bar).
3. Open the app: there is no address bar and the website appears directly. Register or log in, send a topic question containing `?`, and receive an answer with sources.

The template download, `.gradle`, `.idea`, `build`, `local.properties`, and keys are not committed; keep APKs locally or in `artifacts/`.

## Why a TWA

A TWA renders the website with the system's Chrome, so the app is only a shell: website changes need no new app release, and Chrome's login state and cookies are reused. The cost is that HTTPS is required, and the website must publish `assetlinks.json` to prove that "this website authorizes this package name with this signing key" to open it; otherwise Chrome falls back to a Custom Tab with an address bar.
