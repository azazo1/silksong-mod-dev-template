[private]
default:
    @just --list

# 编译示例插件和 InstanceTools
build:
    dotnet build SilksongMod.sln

# 编译. 有 SilksongPath.props 时会复制到 BepInEx/plugins
install:
    dotnet build SilksongMod.sln

# just install-to '<游戏目录>'
# 编译并安装到指定游戏目录
install-to gamedir:
    dotnet build SilksongMod.sln -p:SilksongFolder='{{gamedir}}' -p:SilksongPluginsFolder='{{gamedir}}/BepInEx/plugins'

# 打包可解压进 BepInEx/plugins 的 zip
dist:
    uv run python tools/pack_plugin.py --build --git-version

# just instance '<源安装>'
# 创建或补齐隔离子实例
instance source:
    uv run python game/prepare_instance.py --source '{{source}}'

# 启动隔离子实例
launch:
    uv run python game/launch_instance.py

# 启动隔离子实例并等它退出, 退出后打印 BepInEx 日志尾部
launch-wait:
    uv run python game/launch_instance.py --wait

# just log 80
# 查看隔离子实例的 BepInEx 日志尾部
log lines='40':
    uv run python tools/tail_log.py {{lines}}
