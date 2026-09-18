using System;
using System.IO;
using System.Reflection;
using HarmonyLib;

namespace InstanceTools
{
    // 存档文件的写入: 游戏原本是 "写 .new -> File.Replace 换名", 受限权限下 Replace 被拒,
    // 结果临时文件留在磁盘上而正式存档没被换掉 (游戏随后弹 "无法保存进度").
    //
    // 这里整体接管: 直接用允许的文件操作写到位, 顺便留一份 .bak1.
    // 拿不到存档目录 (反射失败) 或者有在线子系统接管存档时, 返回 true 交回原方法.
    [HarmonyPatch(typeof(DesktopPlatform), "WriteSaveSlot")]
    internal static class SaveSlotWritePatch
    {
        private static readonly FieldInfo SaveDirField =
            AccessTools.Field(typeof(DesktopPlatform), "saveDirPath");

        private static readonly FieldInfo OnlineSubsystemField =
            AccessTools.Field(typeof(DesktopPlatform), "onlineSubsystem");

        [HarmonyPrefix]
        private static bool Prefix(DesktopPlatform __instance, int slotIndex, byte[] bytes, Action<bool> callback)
        {
            if (bytes == null || SaveDirField == null || OnlineSubsystemField == null)
            {
                return true;
            }

            try
            {
                if (OnlineSubsystemField.GetValue(__instance) != null)
                {
                    // 有在线子系统时存档由它负责, 不抢.
                    return true;
                }

                string directory = SaveDirField.GetValue(__instance) as string;
                if (string.IsNullOrEmpty(directory))
                {
                    return true;
                }

                // 与 Platform.GetSaveSlotFileName 一致: 0 号槽位是 user.dat, 其余是 user<N>.dat.
                string name = slotIndex == 0 ? "user.dat" : string.Format("user{0}.dat", slotIndex);
                string path = Path.Combine(directory, name);

                FileReplacement.WriteReplacing(path, bytes, path + ".bak1");

                InstanceToolsPlugin.Log.LogInfo(string.Format(
                    "已写入槽位 {0} 的存档 ({1} 字节): {2}",
                    slotIndex,
                    bytes.Length,
                    path));

                if (callback != null)
                {
                    CoreLoop.InvokeSafe(delegate { callback(true); });
                }

                return false;
            }
            catch (Exception exception)
            {
                InstanceToolsPlugin.Log.LogWarning("直接写存档失败, 交回游戏原方法: " + exception.Message);
                return true;
            }
        }
    }

    // shared.dat (跨存档的持久化设置) 走的是 JsonSharedData.WriteAllBytesSafe, 里面同样有 File.Replace.
    [HarmonyPatch(typeof(JsonSharedData), "WriteAllBytesSafe")]
    internal static class SharedDataWritePatch
    {
        [HarmonyPrefix]
        private static bool Prefix(string path, byte[] data)
        {
            if (string.IsNullOrEmpty(path) || data == null)
            {
                return true;
            }

            try
            {
                FileReplacement.WriteReplacing(path, data, path + ".bak");
                return false;
            }
            catch (Exception exception)
            {
                InstanceToolsPlugin.Log.LogWarning("直接写共享数据失败, 交回游戏原方法: " + exception.Message);
                return true;
            }
        }
    }
}
