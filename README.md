# 丝之歌模组开发模板

在隔离子实例里开发, 测试 BepInEx 插件, 不碰 Steam 源安装和真存档.

游戏本体用目录联接共享只读数据; 存档, PlayerPrefs, 引擎日志全部在代码层指到实例目录. 源安装, 真存档, Steam 成就与云存档都不会被测试碰到.

插件工程按官方 [Silksong.Modding.Templates](https://www.nuget.org/packages/Silksong.Modding.Templates) 的方式组织: SDK 风格 csproj, `Silksong.GameLibs` 提供游戏程序集引用, CI 里 `dotnet build` 就能编示例插件.

## 快速开始

需要 [.NET 10 SDK](https://dotnet.microsoft.com/download). Windows 上可以用 `scoop install dotnet-sdk`.

源安装不必预先装 BepInEx. 准备实例时若源安装没有, 会从 Thunderstore 下载 [BepInExPack Silksong](https://thunderstore.io/c/hollow-knight-silksong/p/silksong_modding/BepInExPack_Silksong/) 只装进实例, 不改源安装.

```shell
# 1. 从源安装拉起隔离子实例
just instance '<源安装>'

# 2. 指向实例目录 (一次性)
cp SilksongPath.props.example SilksongPath.props

# 3. 编译示例插件和 InstanceTools, 装进实例
just install

# 4. 启动实例
just launch

# 5. 看日志
just log 80
```

准备实例时会把 `game/instance-prefs.txt` 复制进子实例, 跳过语言选择. 进到标题界面后, BepInEx 日志里应能看到 `Example Mod` 与 `Instance Tools` 已加载, 以及 `persistentDataPath` 指向实例目录下的 `savedata`.

路径层级 (源安装 / 实例根目录 / 实例存档目录) 见 [game/README.md](game/README.md).

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `src/ExampleMod/` | 你的模组源码. 模板自带一个会加载, 打一条 Harmony 补丁的示例插件 |
| `game/` | 隔离子实例: 准备 / 启动脚本, 以及实例专用的 `instance-tools` |
| `Plugin.props` | BepInEx, HarmonyX, UnityEngine.Modules, Silksong.GameLibs |
| `SilksongPath.props` | 本机游戏目录, 不入版本库; 缺省指向实例目录 |
| `tools/` | 实例路径, BepInEx 下载安装, 日志查看 |

## 把模板变成你的模组

1. 把 `src/ExampleMod/` 里的命名空间, `ExampleModPlugin` 类名, `PluginGuid` / `PluginName` 改成你的.
2. 同步改 `src/ExampleMod/ExampleMod.csproj` 的 `AssemblyName` / `AssemblyTitle`.
3. 删掉 `src/ExampleMod/Patches/GameManagerStartPatch.cs`, 换成你要改的方法; 配置放到 `src/ExampleMod/Config/`.
4. 缺哪个 Unity 模块, 在 `Plugin.props` 里加 `PackageReference`, 或按官方模板那样引用 `UnityEngine.Modules`.

`game/instance-tools/` 是给实例用的, 不属于模组本体, 打包发布时不要带上.

## 常用命令

见 `justfile`. 没有 `just` 的话, 编译是 `dotnet build SilksongMod.sln`, 打包是 `uv run python tools/pack_plugin.py --build --git-version`, 实例脚本是 `game/prepare_instance.py`, `game/launch_instance.py`.

`just dist` 生成 `dist/ExampleMod-<version>.zip`, 解压到游戏的 `BepInEx/plugins`.

没有装 `InstanceTools` 时, `just launch` 会拒绝启动, 避免游戏去读写真存档.
