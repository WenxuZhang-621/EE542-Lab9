# B：Android TWA（Part 2，Part 4 App 端）

本目录来自课程的 Trusted Web Activity 模板。App 本身没有页面：`LauncherActivity`（android-browser-helper）用 Chrome 以全屏、无地址栏的方式打开 A 的网站，登录、群聊和主题问答都在网页里完成。

## 已配置

| 项 | 值 | 文件 |
|---|---|---|
| 包名 / applicationId | `edu.usc.ee542.f1assistant` | `app/build.gradle` |
| App 名称 | F-1 Student Desk | `app/src/main/res/values/strings.xml` |
| 打开的网址 | `https://desktop-jdferfe.taile24d30.ts.net/`（A 的网站） | `strings.xml` 的 `defaultUrl` |
| 签名 | release 用 `keystore/f1assistant-release.jks`，参数在 `keystore.properties`（两者都不提交） | `app/build.gradle` 的 `signingConfigs` |
| Gradle | wrapper 8.13（模板缺的 `gradle-wrapper.jar` 用本机 Gradle 生成后加入），AGP 8.13.0，JDK 17 | `gradle/wrapper/` |

签名证书的 SHA-256 指纹：

```
40:C7:CF:68:1A:2E:C4:25:14:6E:20:A3:27:40:E4:3C:E7:BD:41:AB:AF:E5:6F:EA:FF:6D:5D:8B:01:4E:FE:96
```

给 A 的 `assetlinks.json` 在 `evidence/b-part2/assetlinks.json`，要放到网站的 `/.well-known/assetlinks.json`。包名和指纹必须和上面一致，否则 Chrome 不信任这个 App，会退回带地址栏的 Custom Tab。

## 构建

需要 JDK 17 和 Android SDK（platform 34、build-tools 34.0.0）。在 `local.properties` 写 `sdk.dir=<SDK 路径>`（不提交）。

```sh
cd android
./gradlew assembleDebug          # 调试包（调试签名），可直接装模拟器
./gradlew assembleRelease        # 有 keystore.properties 时输出正式签名的 release 包
# 输出：app/build/outputs/apk/{debug,release}/
```

没有 `keystore.properties` 时 release 构建不签名，调试构建不受影响。验证签名：

```sh
$ANDROID_HOME/build-tools/34.0.0/apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
```

## 安装和验证

```sh
adb install -r app/build/outputs/apk/release/app-release.apk
```

验证顺序：
1. A 部署 `assetlinks.json` 后，`curl https://desktop-jdferfe.taile24d30.ts.net/.well-known/assetlinks.json` 应返回上面的内容。
2. 安装 **签名的 release 包**（指纹必须匹配；debug 包用的是另一把密钥，会显示地址栏）。
3. 打开 App：无地址栏、直接显示网站；注册/登录；发一条带 `?` 的主题问题，收到带来源的回答。

模板、`.gradle`、`.idea`、`build`、`local.properties`、密钥不提交；APK 放本地或 `artifacts/`。

## 为什么是 TWA

TWA 用系统的 Chrome 渲染网页，App 只是一层壳：网站改了 App 不用重新发版，Chrome 的登录态和 Cookie 直接复用。代价是必须 HTTPS，并且网站要发布 `assetlinks.json` 证明"这个网站授权这个包名 + 这把签名"来打开它，否则 Chrome 退回带地址栏的 Custom Tab。
