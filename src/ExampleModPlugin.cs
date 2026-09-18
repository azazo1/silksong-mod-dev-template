using BepInEx;
using BepInEx.Logging;
using ExampleMod.Config;
using HarmonyLib;
using UnityEngine;

namespace ExampleMod
{
    // 示例插件入口. 把本文件, 命名空间, GUID 改成你的模组之后, 在 Patches/ 里写补丁即可.
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInDependency("silksong.instance-tools", BepInDependency.DependencyFlags.SoftDependency)]
    public sealed class ExampleModPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "silksong.example-mod";

        public const string PluginName = "Example Mod";

        public const string PluginVersion = "0.1.0";

        private Harmony _harmony;

        private PluginConfig _config;

        internal static ExampleModPlugin Instance { get; private set; }

        internal ManualLogSource Log
        {
            get { return Logger; }
        }

        internal PluginConfig Settings
        {
            get { return _config; }
        }

        private void Awake()
        {
            Instance = this;
            _config = new PluginConfig(Config);

            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll();

            Logger.LogInfo(string.Format(
                "{0} {1} 已加载. 总开关: {2}; persistentDataPath: {3}",
                PluginName,
                PluginVersion,
                _config.Enabled.Value ? "开启" : "关闭",
                Application.persistentDataPath));
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
