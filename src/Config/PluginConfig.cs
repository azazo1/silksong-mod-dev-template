using BepInEx.Configuration;

namespace ExampleMod.Config
{
    internal sealed class PluginConfig
    {
        internal PluginConfig(ConfigFile config)
        {
            Enabled = config.Bind(
                "General",
                "Enabled",
                true,
                "总开关, 关掉后示例补丁不再执行");
        }

        internal ConfigEntry<bool> Enabled { get; private set; }
    }
}
