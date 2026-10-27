# BOOX Leaf2 Physical Edge Avoidance

A removable, root-required Android resource overlay that excludes one damaged physical screen edge while following 180° rotation. Tested on one BOOX Leaf2_P firmware only; source-only release under the MIT License.

通过可移除的 Magisk 模块和 Android 资源覆盖（RRO），让系统只使用屏幕的健康部分。避让区域绑定物理边缘；旋转180°后，画面中的避让侧随之改变，不再额外裁剪健康对边。

**已验证环境：BOOX Leaf2_P、Android 11、固件 `2025-11-26_19-25_4.0.2-rel_0621_da686c4b1`。** 自然方向右侧140px配置使1264×1680屏幕的逻辑区域变为1124×1680。系统设置、输入法和微信读书墨水屏版的窗口几何已检查。实物损坏覆盖和真实手指触摸验收仍待确认，详见[实测记录](docs/VALIDATION.md)。

这是已有root设备的显示定制工程，不包含获取root、解锁、刷写启动分区或跨型号固件的流程。Leaf2与Leaf2_P不能仅凭名称相似认定兼容。升级固件前应停用模块，新固件需要重新验证。

## 原理和范围

资源包无Activity、服务、网络权限和可执行应用代码，只覆盖四个framework资源：

- `config_mainBuiltInDisplayCutout`
- `config_mainBuiltInDisplayCutoutRectApproximation`
- `config_maskMainBuiltInDisplayCutout=true`
- `config_fillMainBuiltInDisplayCutout=false`

右侧宽度w的路径为：

```text
M -w,0 L 0,0 L 0,1680 L -w,1680 Z @right @bind_right_cutout
```

这里的w是物理像素，不使用`@dp`。框架通过masking insets减小逻辑尺寸，并同步显示投影和输入viewport。模块挂载到独立的`/product/overlay/Leaf2EdgeAvoidance.apk`，不替换原厂APK，不修改wm size/density、SELinux或AVB。没有启动脚本。

这不修复面板损伤。坏区可能呈黑色或有墨水屏残影；不保证纯白。启动过渡存在短暂旧尺寸的已知现象。

## 从源码构建

依赖：Python 3、JDK（提供keytool并运行apksigner）、官方Android SDK Build-Tools 36.0.0、SDK Platform Android 30。依赖请自行从[Android官方SDK渠道](https://developer.android.com/studio)安装并接受其许可；仓库不下载或捆绑工具。

```sh
sdkmanager 'build-tools;36.0.0' 'platforms;android-30'
```

在**仓库外**创建自己的签名密钥。keytool会交互询问密码及证书信息，不要把密码写入脚本或提交密钥：

```sh
keytool -genkeypair -keystore /path/outside/repository/edge.jks \
  -alias edge -keyalg RSA -keysize 2048 -validity 3650
python3 scripts/build.py --sdk /path/to/android-sdk \
  --side right --width 140 \
  --keystore /path/outside/repository/edge.jks
```

构建目录必须不存在；重复构建请用新的`--output`。工具先用AAPT2编译链接、zipalign对齐，再用官方apksigner签名及验证。密码通过apksigner交互输入。参见[AAPT2](https://developer.android.com/tools/aapt2)、[apksigner](https://developer.android.com/tools/apksigner)。

输出包括签名APK、源码副本、校验摘要和`build/module/`。`module-payload.zip`是文件载荷备份，**不是Magisk一键安装ZIP**。构建过程不连接设备、不自动安装、不请求root。

目前不分发预编译APK。不同签名密钥产生不同包；不要直接覆盖已安装的其他签名版本。发布构建链尚未完整复测，构建成功也不等于新机型兼容。原实测包与发布构建的区别见实测记录。

## 测量与安装

先确定自然方向ROTATION_0下的坏边和所需最小宽度。不能从系统截图测出物理坏屏；缩放显示的刻度图也不能直接当作物理像素。140仅是本次指定配置。

需要已正常运行的Magisk、已授权ADB，以及仅在操作期间临时授予Shell的root。先读[恢复方法](#停用与恢复)，保证ADB可用。以下为已测试设备的手动路径；`/debug_ramdisk/su`是该设备实际路径，其他环境不要盲目照搬。

核对机型、固件和现有模块：

```sh
adb -d shell getprop ro.product.model
adb -d shell getprop ro.build.display.id
adb -d shell '/debug_ramdisk/su -c "test ! -e /data/adb/modules/leaf2_edge_avoidance"'
```

只有型号/固件匹配、最后一条成功且不存在同名模块时继续。若已有本模块，先停用并移除旧版本、重启确认恢复，不覆盖目录。

```sh
adb -d push build/module /data/local/tmp/leaf2-edge-module
adb -d shell '/debug_ramdisk/su -c "test ! -e /data/adb/modules/leaf2_edge_avoidance && mkdir /data/adb/modules/leaf2_edge_avoidance && cp -R /data/local/tmp/leaf2-edge-module/. /data/adb/modules/leaf2_edge_avoidance/ && chmod -R u=rwX,go=rX /data/adb/modules/leaf2_edge_avoidance"'
adb -d reboot
```

初始包含`disable`标记。先确认正常开机、屏幕仍完整，APK没有挂载。之后允许模块挂载并重启：

```sh
adb -d shell '/debug_ramdisk/su -c "rm /data/adb/modules/leaf2_edge_avoidance/disable"'
adb -d reboot
```

开机后确认包来自`/product/overlay/`，然后显式启用：

```sh
adb -d shell pm path local.leaf2.edgeavoidance
adb -d shell '/debug_ramdisk/su -c "cmd overlay enable --user 0 local.leaf2.edgeavoidance"'
adb -d shell cmd overlay dump local.leaf2.edgeavoidance
adb -d shell wm size
```

直接`adb install`到用户应用目录在实测固件上被framework签名策略拒绝，因此需要受信任的系统挂载路径；不要尝试关闭验证策略。

## 验证

检查系统与微信读书、键盘、健康区域两侧触摸和180°翻转。对140配置，稳定后的逻辑区域必须为1124×1680；不能只检查RRO显示enabled。

`dumpsys display`和`dumpsys input`可核对投影/触摸，但完整输出可能含设备标识，不要原样公开。预期几何见[实测记录](docs/VALIDATION.md)。测试前记录自动旋转设置，临时改动后恢复原值。确认重启后稳定生效。

完成后在Magisk超级用户页撤销Shell权限，用最小`su -c id`确认被拒绝。无需给微信读书或其他应用root，也无需全局自动授权。

## 停用与恢复

若显示异常但ADB可用，在临时Shell root授权下执行：

```sh
adb -d shell '/debug_ramdisk/su -c "cmd overlay disable --user 0 local.leaf2.edgeavoidance"'
adb -d shell '/debug_ramdisk/su -c "touch /data/adb/modules/leaf2_edge_avoidance/disable"'
adb -d reboot
```

也可在Magisk模块页停用本模块并重启。热关闭RRO和disable标记重启恢复均已实测。完全移除时先关闭RRO，再在Magisk模块页删除本模块并重启。模块机制见[Magisk官方开发文档](https://topjohnwu.github.io/Magisk/guides.html)。

若设备无法启动或ADB不可用，上述命令无法执行；本仓库不承诺自动救砖。安装前应具备适合自己设备的恢复条件。模块停用不需要刷写启动分区，不能用其他机型的boot镜像代替。

## 仓库内容与隐私

仅含原创生成器、构建脚本和文档。不包含原厂分区备份、厂商framework/反汇编、Loader、Magisk二进制、签名密钥、账号凭据、设备标识或个人截图。构建输出和密钥扩展名已加入`.gitignore`，上传前仍需检查实际文件。

## 许可

本仓库原创代码与文档采用[MIT许可](LICENSE)。许可不适用于外部Android SDK、Magisk或厂商代码；这些内容未包含在仓库内，其使用受各自许可约束。
