# B：Android TWA

本目录复制自课程提供的 Android 模板，已排除 build、.gradle、.idea 和 local.properties；当前没有构建或运行验证。

用 Android Studio 打开本目录，配置本机 SDK/JDK；核对 Gradle/AGP 兼容性。提供的模板缺少 gradle/wrapper/gradle-wrapper.jar，因此当前不能假定 ./gradlew 能运行；实施时通过可信 Gradle 工具生成匹配的 wrapper，不从未知来源下载 jar。

替换 app/src/main/res/values/strings.xml 的 example.invalid 为 A 提供的 HTTPS 网站。核对包名，生成本机签名，把公开指纹交给 A 更新 assetlinks；私钥与密码不要提交。构建签名 APK，在设备或模拟器验证登录、主题问答和无地址栏 TWA。编译产物放 artifacts 或保留本地，不提交 Git。
