using System;
using System.IO;

namespace InstanceTools
{
    // File.Replace 底层是 Win32 的 ReplaceFile, 在受限权限下会被直接拒绝
    // (UnauthorizedAccessException: Access to the path is denied),
    // 而 WriteAllBytes / Copy / Delete / Move 都是允许的. 这里用它们拼出等价的 "替换" 语义:
    //
    //   写临时文件 -> 备份旧文件 -> 把旧文件挪开 -> 把临时文件挪到位 -> 删掉挪开的旧文件
    //
    // 中间任何一步失败都会抛出去, 由调用方决定退回原方法还是报错.
    internal static class FileReplacement
    {
        private const string TempSuffix = ".instance-tmp";
        private const string DisplacedSuffix = ".instance-old";

        internal static void WriteReplacing(string path, byte[] data, string backupPath)
        {
            if (string.IsNullOrEmpty(path))
            {
                throw new ArgumentException("path 不能为空", "path");
            }

            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            string temp = path + TempSuffix;
            File.WriteAllBytes(temp, data);

            if (File.Exists(path))
            {
                if (!string.IsNullOrEmpty(backupPath))
                {
                    try
                    {
                        File.Copy(path, backupPath, true);
                    }
                    catch (Exception exception)
                    {
                        InstanceToolsPlugin.Log.LogWarning("备份旧文件失败 (继续写入): " + exception.Message);
                    }
                }

                string displaced = path + DisplacedSuffix;
                if (File.Exists(displaced))
                {
                    File.Delete(displaced);
                }

                File.Move(path, displaced);
            }

            File.Move(temp, path);

            string leftover = path + DisplacedSuffix;
            if (File.Exists(leftover))
            {
                try
                {
                    File.Delete(leftover);
                }
                catch (Exception exception)
                {
                    InstanceToolsPlugin.Log.LogWarning("清理旧文件失败: " + exception.Message);
                }
            }
        }
    }
}
