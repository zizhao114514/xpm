/*
 * xmcs - XPM C# Backend (Special Edition)
 * Version: 1.9-0-csharp
 * Policy: No apt, only dpkg + tar + wget
 * Oil: 100001% | Power: 1.x W
 */

using System;
using System.IO;

namespace Xmcs
{
    class Program
    {
        static int Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.Error.WriteLine("xmcs: no command");
                Console.Error.WriteLine("Usage: xmcs <install|remove|purge|verify|query|files|rebuild-db> [args]");
                return 1;
            }

            string cmd = args[0];
            string[] sub = args.Length > 1 ? args[1..] : Array.Empty<string>();

            try
            {
                switch (cmd)
                {
                    case "install":  return Xm.Install(sub);
                    case "remove":   return Xm.Remove(sub, purge: false);
                    case "purge":    return Xm.Remove(sub, purge: true);
                    case "verify":   return Xm.Verify(sub);
                    case "query":    return Xm.Query(sub);
                    case "files":    return Xm.Files(sub);
                    case "rebuild-db": return Xm.RebuildDb();
                    case "--version":
                    case "version":
                        Console.WriteLine("xmcs 1.9.0-csharp");
                        Console.WriteLine("Compiled with: mcs / .NET");
                        Console.WriteLine("Oil-driven: yes");
                        Console.WriteLine("Systemd: no");
                        Console.WriteLine("Apt: explicitly forbidden");
                        Console.WriteLine("Coffee machine: stable (for now)");
                        return 0;
                    default:
                        Console.Error.WriteLine($"xmcs: unknown command '{cmd}'");
                        return 1;
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"xmcs: fatal: {ex.Message}");
                Coffee.LogCrash();
                return 1;
            }
        }
    }
}
