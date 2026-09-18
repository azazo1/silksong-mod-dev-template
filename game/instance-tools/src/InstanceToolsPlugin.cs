using BepInEx;
using BepInEx.Logging;
using HarmonyLib;

namespace InstanceTools
{
    // 隔离子实例的工具插件, 让游戏在受限权限 (写不了注册表, 也做不了 File.Replace) 的环境下也能正常跑.
    // 三件事:
    //   1. 接管 Application.persistentDataPath, 把存档目录指到实例目录下的 savedata;
    //   2. 把 PlayerPrefs 读写重定向到实例存档目录下的文本文件
    //      (Unity 在 Windows 上把 PlayerPrefs 写进 HKCU\Software\<公司名>\<产品名>, 被拒之后
    //      PlayerPrefs.SetString 会抛 PlayerPrefsException, 表现为语言选择界面点不动);
    //   3. 把游戏里两处 File.Replace 换成 Copy/Delete/Move 的等价实现
    //      (File.Replace 底层是 ReplaceFile, 会被拒, 存档会写不进去).
    //
    // 这不是模组本体的一部分, 是实例工具, 普通直接双击游戏启动的玩家用不到.
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class InstanceToolsPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "silksong.instance-tools";

        public const string PluginName = "Instance Tools";

        public const string PluginVersion = "0.1.0";

        private Harmony _harmony;

        internal static InstanceToolsPlugin Instance { get; private set; }

        internal static ManualLogSource Log
        {
            get { return Instance != null ? Instance.Logger : null; }
        }

        private void Awake()
        {
            Instance = this;
            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll();
            Logger.LogInfo(string.Format(
                "{0} {1} 已加载. 设置文件: {2}; 存档写入已改为不依赖 File.Replace.",
                PluginName,
                PluginVersion,
                PrefsStore.FilePath));
        }

        private void OnDestroy()
        {
            if (_harmony != null)
            {
                _harmony.UnpatchSelf();
                _harmony = null;
            }

            if (Instance == this)
            {
                Instance = null;
            }
        }
    }
}
