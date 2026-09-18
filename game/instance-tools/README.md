# InstanceTools (实例工具插件)

给 `game/Hollow Knight Silksong/` 这个隔离子实例用的补丁插件, **不属于 mod 本体**, 打包发布时不要带上.

它做三件事, 都是把游戏原本会碰到 "本机全局状态" 的行为改成只影响实例目录:

| 补丁 | 原本行为 | 改成 |
| --- | --- | --- |
| `PersistentDataPathPatch` | `Application.persistentDataPath` 由 Unity 按构建时烘焙的公司名算, 指向 `%USERPROFILE%\AppData\LocalLow\<公司名>\<产品名>` | 返回 `<实例目录>/savedata` |
| `PlayerPrefsRedirectPatch` | PlayerPrefs 在 Windows 上写注册表 `HKCU\Software\<公司名>\<产品名>` | 读写实例目录下的 `savedata/instance-prefs.txt` |
| `SaveSlotWritePatch` / `SharedDataWritePatch` | 写存档与 `shared.dat` 用 "写临时文件 + `File.Replace`" | 换成 `Copy` / `Delete` / `Move` 的等价实现 |

路径层级见 [game/README.md](../README.md).

## 为什么要这样

- **存档路径**: 直接改游戏的 `globalgamemanagers` 也能换路径, 但那里面是定长字符串, 换名字还得迁就长度. 路径本来就是游戏自己算出来的, 那就在代码层把算出来的结果换掉, 一改全通 (`DesktopPlatform.saveDirPath` 等自然跟着走).
- **PlayerPrefs**: 写注册表在受限权限下会抛 `PlayerPrefsException: Could not store preference value`, 表现是卡在语言选择界面, 点任何语言都没反应; 就算跳过去, 后面每次点存档槽位写 `lastProfileIndex` 还会再抛.
- **`File.Replace`**: 底层是 Win32 的 `ReplaceFile`, 受限权限下会被直接拒绝并抛 `UnauthorizedAccessException`, 而 `WriteAllBytes` / `Copy` / `Delete` / `Move` 都是允许的. 游戏用它的地方只有两处 (存档本体与 `shared.dat`), 这两处写不进去的表现就是弹 "无法保存进度".

## 还有一处没法用补丁解决

`Player.log` 是 Unity 引擎在托管代码跑起来之前就写好的, 位置由构建时的公司名决定, 托管补丁管不着. 所以 `game/launch_instance.py` 启动时给游戏加了引擎自带的 `-logFile <实例目录>/Player.log`.

## 构建

跟主插件一起编:

```shell
just install
```
