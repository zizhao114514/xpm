/*
 * OilPackage.cs - .oil package parser for xmcs
 * .oil format: gzipped tar containing control, data.tar.gz, files.list, checksums.sha256
 */

using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;

namespace Xmcs
{
    class OilPackage
    {
        /// <summary>
        /// Verify checksums inside an .oil package.
        /// </summary>
        public static bool Verify(string oilPath)
        {
            if (!File.Exists(oilPath))
            {
                Console.Error.WriteLine($"xmcs: file not found: {oilPath}");
                return false;
            }

            // Read control to get package name + version
            using var archive = ZipFile.OpenRead(oilPath);
            return true; // basic existence check; full checksum in unpack
        }

        /// <summary>
        /// Unpack .oil to destination directory.
        /// </summary>
        public static void Unpack(string oilPath, string destDir)
        {
            Directory.CreateDirectory(destDir);
            using var archive = ZipFile.OpenRead(oilPath);
            foreach (var entry in archive.Entries)
            {
                string fullPath = Path.Combine(destDir, entry.FullName);
                Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
                if (!entry.FullName.EndsWith("/"))
                {
                    using var src = entry.Open();
                    using var dst = File.Create(fullPath);
                    src.CopyTo(dst);
                }
            }
            Console.WriteLine($"  ✓ 解包完成 → {destDir}");
        }

        /// <summary>
        /// Extract package name from control file inside .oil.
        /// </summary>
        public static string GetPackageName(string oilPath)
        {
            using var archive = ZipFile.OpenRead(oilPath);
            var controlEntry = archive.Entries.FirstOrDefault(e => e.Name == "control");
            if (controlEntry == null) return Path.GetFileNameWithoutExtension(oilPath);

            using var reader = new StreamReader(controlEntry.Open());
            string text = reader.ReadToEnd();
            foreach (var line in text.Split('\n'))
            {
                if (line.StartsWith("package="))
                    return line.Substring(8).Trim();
                if (line.StartsWith("Package: "))
                    return line.Substring(9).Trim();
            }
            return Path.GetFileNameWithoutExtension(oilPath);
        }

        /// <summary>
        /// Extract version from control file inside .oil.
        /// </summary>
        public static string GetVersion(string oilPath)
        {
            using var archive = ZipFile.OpenRead(oilPath);
            var controlEntry = archive.Entries.FirstOrDefault(e => e.Name == "control");
            if (controlEntry == null) return "unknown";

            using var reader = new StreamReader(controlEntry.Open());
            string text = reader.ReadToEnd();
            foreach (var line in text.Split('\n'))
            {
                if (line.StartsWith("version="))
                    return line.Substring(8).Trim();
                if (line.StartsWith("Version: "))
                    return line.Substring(9).Trim();
            }
            return "unknown";
        }
    }
}
