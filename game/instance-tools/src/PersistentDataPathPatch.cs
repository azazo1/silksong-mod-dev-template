using HarmonyLib;
using UnityEngine;

namespace InstanceTools
{
    // 把 Application.persistentDataPath 换成 RedirectedPaths 算出来的路径.
    // 属性 getter 本身是有 IL 的托管方法, 直接 Postfix 改返回值即可.
    [HarmonyPatch(typeof(Application), "get_persistentDataPath")]
    internal static class PersistentDataPathPatch
    {
        [HarmonyPostfix]
        private static void Postfix(ref string __result)
        {
            string redirected = RedirectedPaths.PersistentDataPath;
            if (!string.IsNullOrEmpty(redirected))
            {
                __result = redirected;
            }
        }
    }
}
