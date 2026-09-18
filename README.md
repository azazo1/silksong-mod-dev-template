# 丝之歌模组开发模板

在隔离子实例里开发, 测试 BepInEx 插件, 不碰 Steam 源安装和真存档.

游戏本体用目录联接共享只读数据; 存档, PlayerPrefs, 引擎日志全部在代码层指到实例目录. 源安装, 真存档, Steam 成就与云存档都不会被测试碰到.

## 快速开始

源安装不必预先装 BepInEx. 准备实例时若源安装没有, 会从 Thunderstore 下载 [BepInExPack Silksong](https://thunderstore.io/c/hollow-knight-silksong/p/silksong_modding/BepInExPack_Silksong/) 只装进实例, 不改源安装.

```shell
# 1. 从源安装拉起隔离子实例
just instance '<源安装>'

# 2. 编译示例插件和 InstanceTools, 装进实例
just install

# 3. 启动实例
just launch

# 4. 看日志
just log 80
```

首次启动会走语言选择. 进到标题界面后, BepInEx 日志里应能看到 `Example Mod` 与 `Instance Tools` 已加载, 以及 `persistentDataPath` 指向实例目录下的 `savedata`.

路径层级 (源安装 / 实例根目录 / 实例存档目录) 见 [game/README.md](game/README.md).

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `src/` | 你的模组源码. 模板自带一个会加载, 打一条 Harmony 补丁的示例插件 |
| `game/` | 隔离子实例: 准备 / 启动脚本, 以及实例专用的 `instance-tools` |
| `build.py` | 调用 Visual Studio 自带的 Roslyn csc 编译, `--install` 复制到 `BepInEx/plugins` |
| `SilksongPath.props` | 本机游戏目录, 不入版本库; 缺省指向实例目录 |
| `tools/` | 实例路径, BepInEx 下载安装, 日志查看 |

## 把模板变成你的模组

1. 把 `src/` 里的 `ExampleMod` 命名空间, `ExampleModPlugin` 类名, `PluginGuid` / `PluginName` 改成你的.
2. 同步改 `build.py` 里 `PROJECTS` 的 `name = "ExampleMod"`.
3. 删掉 `src/Patches/GameManagerStartPatch.cs`, 换成你要改的方法; 配置放到 `src/Config/`.
4. 缺哪个 Unity 程序集, 在 `build.py` 的 `references` 里补一行即可.

`game/instance-tools/` 是给实例用的, 不属于模组本体, 打包发布时不要带上.

## 常用命令

见 `justfile`. 没有 `just` 的话, 对应脚本是 `build.py`, `game/prepare_instance.py`, `game/launch_instance.py`.

没有装 `InstanceTools` 时, `just launch` 会拒绝启动, 避免游戏去读写真存档.
