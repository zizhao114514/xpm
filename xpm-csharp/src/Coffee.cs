/*
 * Coffee.cs - Coffee machine crash counter for xmcs
 * Shared log with xpm frontend.
 */

using System;
using System.IO;
using System.Globalization;

namespace Xmcs
{
    class Coffee
    {
        const string CoffeeLog = "/var/lib/xpm/coffee.log";
        const int MaxCrashes = 31;

        public static void LogCrash()
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(CoffeeLog));
                int count = GetCount() + 1;
                using var sw = new StreamWriter(CoffeeLog, append: true);
                sw.WriteLine($"[{DateTime.UtcNow:o}] xmcs: CRASH #{count}");
                Console.Error.WriteLine($"☕ 咖啡机爆炸 +1 (累计 {count}/{MaxCrashes})");
                Console.Error.WriteLine("🛢️ 石油消耗：0.01%");
            }
            catch { }
        }

        public static int GetCount()
        {
            if (!File.Exists(CoffeeLog)) return 0;
            int n = 0;
            foreach (var line in File.ReadAllLines(CoffeeLog))
                if (line.Contains("CRASH")) n++;
            return n;
        }
    }
}
