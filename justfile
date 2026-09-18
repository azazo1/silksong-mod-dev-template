[private]
default:
    @just --list

# 编译插件到 bin/
build:
    uv run python build.py

# 编译并安装到游戏目录 (默认取 SilksongPath.props, 没有则用隔离子实例)
install:
    uv run python build.py --install

# 编译并安装到指定游戏目录
# just install-to '<游戏目录>'
install-to gamedir:
    uv run python build.py --install --game-dir '{{gamedir}}'

# 创建或补齐隔离子实例
# just instance '<源安装>'
instance source:
    uv run python game/prepare_instance.py --source '{{source}}'

# 启动隔离子实例
launch:
    uv run python game/launch_instance.py

# 启动隔离子实例并等它退出, 退出后打印 BepInEx 日志尾部
launch-wait:
    uv run python game/launch_instance.py --wait

# 查看隔离子实例的 BepInEx 日志尾部
# just log 80
log lines='40':
    uv run python tools/tail_log.py {{lines}}
