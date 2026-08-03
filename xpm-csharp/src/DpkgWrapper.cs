/*
 * DpkgWrapper.cs - Only allowed external package manager call: dpkg
 * NEVER call apt, apt-get, apt-cache.
 */

using System;
using System.Diagnostics;

namespace Xmcs
{
    class DpkgWrapper
    {
        public static int Install(string debPath)
        {
            return Run($"-i {debPath}");
        }

        public static int Remove(string pkg)
        {
            return Run($"--remove {pkg}");
        }

        public static int Purge(string pkg)
        {
            return Run($"--purge {pkg}");
        }

        public static int ConfigureA()
        {
            return Run("--configure -a");
        }

        public static int ListInstalled()
        {
            return Run("-l");
        }

        public static int ListFiles(string pkg)
        {
            return Run($"-L {pkg}");
        }

        static int Run(string args)
        {
            var psi = new ProcessStartInfo("dpkg", args)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var p = Process.Start(psi);
            string line;
            while ((line = p.StandardOutput.ReadLine()) != null)
                Console.WriteLine($"       {line}");
            while ((line = p.StandardError.ReadLine()) != null)
                Console.Error.WriteLine($"       {line}");
            p.WaitForExit();
            return p.ExitCode;
        }
    }
}
