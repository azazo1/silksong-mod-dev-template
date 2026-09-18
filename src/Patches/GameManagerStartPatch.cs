using HarmonyLib;

namespace ExampleMod.Patches
{
    // 示例 Harmony 补丁: 游戏进到主流程时打一条日志, 用来确认插件真的挂上了.
    // 写自己的模组时删掉这个文件, 换成你要改的方法.
    [HarmonyPatch(typeof(GameManager), "Start")]
    internal static class GameManagerStartPatch
    {
        [HarmonyPostfix]
        private static void Postfix()
        {
            ExampleModPlugin plugin = ExampleModPlugin.Instance;
            if (plugin == null || plugin.Settings == null || !plugin.Settings.Enabled.Value)
            {
                return;
            }

            plugin.Log.LogInfo("Example Mod: GameManager.Start 已触发.");
        }
    }
}
