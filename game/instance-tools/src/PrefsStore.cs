using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace InstanceTools
{
    // Unity 的 PlayerPrefs 在 Windows 上落在注册表 HKCU\Software\<公司名>\<产品名>.
    // 本插件把它换成实例存档目录下的一个文本文件, 好处是:
    //   - 设置跟着实例的存档走, 不污染真实账号的注册表;
    //   - 在受限权限下跑实例时 (写不了注册表) 游戏不会因为 PlayerPrefsException 卡住.
    //
    // 只存游戏真正会用到的三类值, 格式是每行 type \t key \t value 的纯文本.
    internal static class PrefsStore
    {
        private const string FileName = "instance-prefs.txt";

        private static readonly Dictionary<string, string> Strings = new Dictionary<string, string>();

        private static readonly Dictionary<string, int> Ints = new Dictionary<string, int>();

        private static readonly Dictionary<string, float> Floats = new Dictionary<string, float>();

        private static bool _loaded;

        private static bool _dirty;

        internal static string FilePath
        {
            get { return Path.Combine(Application.persistentDataPath, FileName); }
        }

        internal static bool HasKey(string key)
        {
            if (string.IsNullOrEmpty(key))
            {
                return false;
            }

            EnsureLoaded();
            return Strings.ContainsKey(key) || Ints.ContainsKey(key) || Floats.ContainsKey(key);
        }

        internal static void DeleteKey(string key)
        {
            EnsureLoaded();

            bool removed = Strings.Remove(key) | Ints.Remove(key) | Floats.Remove(key);
            if (removed)
            {
                _dirty = true;
            }
        }

        internal static void DeleteAll()
        {
            EnsureLoaded();

            Strings.Clear();
            Ints.Clear();
            Floats.Clear();
            _dirty = true;
        }

        internal static string GetString(string key, string def)
        {
            EnsureLoaded();

            string value;
            return Strings.TryGetValue(key, out value) ? value : def;
        }

        internal static void SetString(string key, string value)
        {
            EnsureLoaded();

            if (value == null)
            {
                DeleteKey(key);
                return;
            }

            string current;
            if (Strings.TryGetValue(key, out current) && current == value)
            {
                return;
            }

            Strings[key] = value;
            Ints.Remove(key);
            Floats.Remove(key);
            _dirty = true;
        }

        internal static int GetInt(string key, int def)
        {
            EnsureLoaded();

            int value;
            return Ints.TryGetValue(key, out value) ? value : def;
        }

        internal static void SetInt(string key, int value)
        {
            EnsureLoaded();

            int current;
            if (Ints.TryGetValue(key, out current) && current == value)
            {
                return;
            }

            Ints[key] = value;
            Strings.Remove(key);
            Floats.Remove(key);
            _dirty = true;
        }

        internal static float GetFloat(string key, float def)
        {
            EnsureLoaded();

            float value;
            return Floats.TryGetValue(key, out value) ? value : def;
        }

        internal static void SetFloat(string key, float value)
        {
            EnsureLoaded();

            float current;
            if (Floats.TryGetValue(key, out current) && Math.Abs(current - value) < float.Epsilon)
            {
                return;
            }

            Floats[key] = value;
            Strings.Remove(key);
            Ints.Remove(key);
            _dirty = true;
        }

        internal static void Save()
        {
            EnsureLoaded();

            if (!_dirty)
            {
                return;
            }

            try
            {
                StringBuilder builder = new StringBuilder();
                foreach (KeyValuePair<string, string> pair in Strings)
                {
                    builder.Append("s\t").Append(Escape(pair.Key)).Append('\t').Append(Escape(pair.Value)).Append('\n');
                }

                foreach (KeyValuePair<string, int> pair in Ints)
                {
                    builder.Append("i\t").Append(Escape(pair.Key)).Append('\t').Append(pair.Value).Append('\n');
                }

                foreach (KeyValuePair<string, float> pair in Floats)
                {
                    builder.Append("f\t").Append(Escape(pair.Key)).Append('\t')
                        .Append(pair.Value.ToString(CultureInfo.InvariantCulture)).Append('\n');
                }

                File.WriteAllText(FilePath, builder.ToString(), new UTF8Encoding(false));
                _dirty = false;
                InstanceToolsPlugin.Log.LogInfo(string.Format(
                    "已把 {0} 项设置写进 {1}",
                    Strings.Count + Ints.Count + Floats.Count,
                    FilePath));
            }
            catch (Exception exception)
            {
                InstanceToolsPlugin.Log.LogWarning("写设置文件失败: " + exception.Message);
            }
        }

        private static void EnsureLoaded()
        {
            if (_loaded)
            {
                return;
            }

            _loaded = true;

            try
            {
                if (!File.Exists(FilePath))
                {
                    InstanceToolsPlugin.Log.LogInfo("还没有设置文件, 从空开始: " + FilePath);
                    return;
                }

                int count = 0;
                foreach (string line in File.ReadAllLines(FilePath, Encoding.UTF8))
                {
                    if (string.IsNullOrEmpty(line))
                    {
                        continue;
                    }

                    string[] parts = line.Split('\t');
                    if (parts.Length < 3)
                    {
                        continue;
                    }

                    string key = Unescape(parts[1]);
                    string value = Unescape(parts[2]);
                    switch (parts[0])
                    {
                        case "s":
                            Strings[key] = value;
                            break;
                        case "i":
                            int intValue;
                            if (int.TryParse(value, out intValue))
                            {
                                Ints[key] = intValue;
                            }
                            break;
                        case "f":
                            float floatValue;
                            if (float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out floatValue))
                            {
                                Floats[key] = floatValue;
                            }
                            break;
                        default:
                            continue;
                    }

                    count++;
                }

                InstanceToolsPlugin.Log.LogInfo(string.Format("已从 {0} 读入 {1} 项设置", FilePath, count));
            }
            catch (Exception exception)
            {
                InstanceToolsPlugin.Log.LogWarning("读设置文件失败: " + exception.Message);
            }
        }

        private static string Escape(string value)
        {
            return value
                .Replace("\\", "\\\\")
                .Replace("\t", "\\t")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n");
        }

        private static string Unescape(string value)
        {
            StringBuilder builder = new StringBuilder(value.Length);
            for (int i = 0; i < value.Length; i++)
            {
                if (value[i] != '\\' || i + 1 >= value.Length)
                {
                    builder.Append(value[i]);
                    continue;
                }

                i++;
                switch (value[i])
                {
                    case 't':
                        builder.Append('\t');
                        break;
                    case 'r':
                        builder.Append('\r');
                        break;
                    case 'n':
                        builder.Append('\n');
                        break;
                    case '\\':
                        builder.Append('\\');
                        break;
                    default:
                        builder.Append(value[i]);
                        break;
                }
            }

            return builder.ToString();
        }
    }
}
