# B · Part 2 evidence and handoff to A

## Handoff to A (needed before the TWA runs without an address bar)

Put `assetlinks.json` from this folder on the website at exactly
`https://desktop-jdferfe.taile24d30.ts.net/.well-known/assetlinks.json`
(content type `application/json`, no redirect). It declares:

- package name: `edu.usc.ee542.f1assistant`
- signing certificate SHA-256: `40:C7:CF:68:1A:2E:C4:25:14:6E:20:A3:27:40:E4:3C:E7:BD:41:AB:AF:E5:6F:EA:FF:6D:5D:8B:01:4E:FE:96`

The site currently serves the template file (package `com.helloworld.groupchat.twa`, placeholder fingerprint), so Chrome shows the URL bar until it is replaced.

## Build record (2026-10-31, macOS, JDK 17, Gradle 8.13, AGP 8.13.0, SDK platform 34)

```
./gradlew assembleRelease assembleDebug
app/build/outputs/apk/release/app-release.apk   1,024,780 bytes, signed
app/build/outputs/apk/debug/app-debug.apk       1,304,085 bytes, debug key
apksigner verify --print-certs app-release.apk
  Signer #1 certificate SHA-256 digest: 40c7cf681a2ec425146e20a32740e43ce7bd41abafe56feaff6d5d8b014efe96
aapt dump badging app-release.apk
  package: name='edu.usc.ee542.f1assistant' versionCode='1' versionName='1.0' compileSdkVersion='34'
  application-label:'F-1 Student Desk'
```

APKs are kept in `artifacts/android/` (git-ignored); the keystore and its passwords are not in the repository.
