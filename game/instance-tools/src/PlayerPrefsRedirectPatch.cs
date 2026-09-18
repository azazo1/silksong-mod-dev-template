using HarmonyLib;

namespace InstanceTools
{
    // 游戏里只有 PlayerPrefsSharedData 这一个类碰 UnityEngine.PlayerPrefs,
    // 所以把这几个方法整体接管掉就够了, 不用去 hook Unity 的 native 调用.
    //
    // 每个 Prefix 都返回 false, 表示原方法 (也就是真正的 PlayerPrefs 读写) 不再执行.
    [HarmonyPatch(typeof(PlayerPrefsSharedData))]
    internal static class PlayerPrefsRedirectPatch
    {
        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.HasKey))]
        private static bool HasKey(string key, ref bool __result)
        {
            __result = PrefsStore.HasKey(key);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.DeleteKey))]
        private static bool DeleteKey(string key)
        {
            PrefsStore.DeleteKey(key);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.DeleteAll))]
        private static bool DeleteAll()
        {
            PrefsStore.DeleteAll();
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.GetString))]
        private static bool GetString(string key, string def, ref string __result)
        {
            __result = PrefsStore.GetString(key, def);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.SetString))]
        private static bool SetString(string key, string val)
        {
            PrefsStore.SetString(key, val);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.GetInt))]
        private static bool GetInt(string key, int def, ref int __result)
        {
            __result = PrefsStore.GetInt(key, def);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.SetInt))]
        private static bool SetInt(string key, int val)
        {
            PrefsStore.SetInt(key, val);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.GetFloat))]
        private static bool GetFloat(string key, float def, ref float __result)
        {
            __result = PrefsStore.GetFloat(key, def);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.SetFloat))]
        private static bool SetFloat(string key, float val)
        {
            PrefsStore.SetFloat(key, val);
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(PlayerPrefsSharedData.Save))]
        private static bool Save()
        {
            PrefsStore.Save();
            return false;
        }
    }
}
