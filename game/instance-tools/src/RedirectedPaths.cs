using System.IO;
using BepInEx;

namespace InstanceTools
{
    // 游戏取存档目录的链路是:
    //   Application.persistentDataPath -> DesktopPlatform.saveDirPath -> user<N>.dat
    //
    // persistentDataPath 由 Unity 按 globalgamemanagers 里烘焙的公司名算出来, 那是定长字符串,
    // 想换名字就得改二进制. 与其那样, 不如直接把这一层接管: 让它返回实例目录下的 savedata.
    // 效果就是 "把整个存档路径换掉", 而且游戏里所有用 persistentDataPath 的地方 (存档, AppConfig,
    // 本插件的设置文件) 一并跟着走, 全部落在仓库里.
    //
    // Player.log 是 Unity 在托管代码跑起来之前写的, 这里管不着, 由启动脚本用 -logFile 指定.
    internal static class RedirectedPaths
    {
        private const string SaveDataFolderName = "savedata";

        private static string _persistentDataPath;

        internal static string PersistentDataPath
        {
            get
            {
                if (_persistentDataPath == null)
                {
                    _persistentDataPath = Path.Combine(Paths.GameRootPath, SaveDataFolderName);
                    Directory.CreateDirectory(_persistentDataPath);
                    InstanceToolsPlugin.Log.LogInfo("persistentDataPath 已重定向到: " + _persistentDataPath);
                }

                return _persistentDataPath;
            }
        }
    }
}
