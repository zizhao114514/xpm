/*
 * Xm.cs - Core backend logic for xmcs
 * Implements: install, remove, purge, verify, query, files, rebuild-db
 * Only calls: dpkg, tar, gzip, wget (NEVER apt)
 */

using System;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace Xmcs
{
    class Xm
    {
        const string StatusDb = "/var/lib/xpm/status.db";
        const string CoffeeLog = "/var/lib/xpm/coffee.log";
        const string LockDir = "/var/cache/xm/lock";
        const string CacheDir = "/var/cache/xpm/archives";

        // ---------- public commands ----------

        public static int Install(string[] args)
        {
            if (args.Length == 0) { Console.Error.WriteLine("xmcs: install: missing file"); return 1; }
            string oilPath = args[0];

            if (!File.Exists(oilPath))
            {
                // try wget if not local
                Console.WriteLine($"  [1/5] 本地未找到，尝试下载: {oilPath}");
                string url = oilPath;
                Directory.CreateDirectory(CacheDir);
                string fname = Path.GetFileName(url);
                string dest = Path.Combine(CacheDir, fname);
                if (Run("wget", $"-q --timeout=60 -O {dest} {url}") != 0)
                {
                    Console.Error.WriteLine("xmcs: download failed");
                    Coffee.LogCrash();
                    return 1;
                }
                oilPath = dest;
            }

            // acquire lock
            using var _lock = new LockFile(Path.Combine(LockDir, "install.lock"));
            if (!_lock.Acquire())
            {
                Console.Error.WriteLine($"xmcs: lock busy (held by PID {_lock.OwnerPid})");
                Console.Error.WriteLine($"  waiting... (max 120s)");
                if (!_lock.Wait(120))
                {
                    Console.Error.WriteLine("xmcs: timeout waiting for lock");
                    Coffee.LogCrash();
                    return 2;
                }
            }

            string txnId = "txn-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
            var txn = new Transaction(txnId, "install", oilPath);

            try
            {
                // 2. verify
                Console.WriteLine($"  [2/5] 校验包...");
                if (!OilPackage.Verify(oilPath))
                {
                    Console.Error.WriteLine("xmcs: checksum failed");
                    txn.Fail("verify");
                    Coffee.LogCrash();
                    return 1;
                }

                // 3. unpack
                Console.WriteLine($"  [3/5] 解包...");
                string tmpDir = Path.Combine("/tmp", "xmcs-unpack-" + txnId);
                Directory.CreateDirectory(tmpDir);
                OilPackage.Unpack(oilPath, tmpDir);

                // 4. dpkg -i
                Console.WriteLine($"  [4/5] 安装 (dpkg -i)...");
                int rc = Run("dpkg", $"-i {oilPath}");
                if (rc != 0)
                {
                    Console.Error.WriteLine($"xmcs: dpkg failed (rc={rc})");
                    txn.Fail("dpkg");
                    Coffee.LogCrash();
                    return rc;
                }

                // 5. register in status.db
                Console.WriteLine($"  [5/5] 注册到 status.db...");
                string pkgName = OilPackage.GetPackageName(oilPath);
                string version = OilPackage.GetVersion(oilPath);
                RegisterPackage(pkgName, version, oilPath);

                txn.Commit();
                Console.WriteLine($"  ✅ 安装完成: {pkgName} {version}");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"xmcs: {ex.Message}");
                txn.Fail(ex.Message);
                Coffee.LogCrash();
                return 1;
            }
        }

        public static int Remove(string[] args, bool purge)
        {
            if (args.Length == 0) { Console.Error.WriteLine("xmcs: remove: missing package name"); return 1; }
            string pkg = args[0];

            using var _lock = new LockFile(Path.Combine(LockDir, $"remove-{pkg}.lock"));
            if (!_lock.Acquire())
            {
                Console.Error.WriteLine($"xmcs: lock busy (held by PID {_lock.OwnerPid})");
                if (!_lock.Wait(120))
                {
                    Coffee.LogCrash();
                    return 2;
                }
            }

            string action = purge ? "--purge" : "--remove";
            string label = purge ? "彻底清除" : "卸载";
            Console.WriteLine($"  [1/3] {label}: {pkg}");

            // prerm
            Console.WriteLine($"  [2/3] 执行 prerm...");
            // dpkg handles prerm/postrm via maintainer scripts automatically

            int rc = Run("dpkg", $"{action} {pkg}");
            if (rc != 0)
            {
                Console.Error.WriteLine($"xmcs: dpkg {action} failed (rc={rc})");
                Coffee.LogCrash();
                return rc;
            }

            Console.WriteLine($"  [3/3] 从 status.db 注销...");
            UnregisterPackage(pkg);

            Console.WriteLine($"  ✅ {label}完成: {pkg}");
            return 0;
        }

        public static int Verify(string[] args)
        {
            if (args.Length == 0) { Console.Error.WriteLine("xmcs: verify: missing package name"); return 1; }
            string pkg = args[0];
            var files = GetInstalledFiles(pkg);
            int bad = 0;
            foreach (var f in files)
            {
                if (!File.Exists(f))
                {
                    Console.WriteLine($"  ✗ 缺失: {f}");
                    bad++;
                }
                else
                {
                    Console.WriteLine($"  ✓ {f}");
                }
            }
            return bad == 0 ? 0 : 1;
        }

        public static int Query(string[] args)
        {
            if (args.Length == 0) { Console.Error.WriteLine("xmcs: query: missing package name"); return 1; }
            string pkg = args[0];
            var db = ReadStatusDb();
            if (db.TryGetValue(pkg, out var info))
            {
                Console.WriteLine($"  Package: {pkg}");
                Console.WriteLine($"  Version: {info.GetValueOrDefault("version","?")}");
                Console.WriteLine($"  State:   {info.GetValueOrDefault("state","?")}");
                Console.WriteLine($"  Origin:  {info.GetValueOrDefault("origin","?")}");
                return 0;
            }
            Console.WriteLine($"  {pkg}: 未安装");
            return 1;
        }

        public static int Files(string[] args)
        {
            if (args.Length == 0) { Console.Error.WriteLine("xmcs: files: missing package name"); return 1; }
            string pkg = args[0];
            var files = GetInstalledFiles(pkg);
            foreach (var f in files) Console.WriteLine(f);
            return files.Count > 0 ? 0 : 1;
        }

        public static int RebuildDb()
        {
            Console.WriteLine("  [1/2] 扫描已安装包 (dpkg -l)...");
            var psi = new ProcessStartInfo("dpkg", "-l")
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var p = Process.Start(psi);
            string output = p.StandardOutput.ReadToEnd();
            p.WaitForExit();

            var db = new Dictionary<string, Dictionary<string, string>>();
            foreach (var line in output.Split('\n'))
            {
                if (line.Length < 4 || line[0] != 'i') continue;
                if (line[1] != 'i' && line[1] != 'U') continue;
                var parts = Regex.Split(line.Trim(), @"\s+");
                if (parts.Length < 3) continue;
                string name = parts[1];
                string version = parts[2];
                db[name] = new Dictionary<string, string>
                {
                    ["version"] = version,
                    ["state"] = "installed",
                    ["origin"] = "dpkg-rebuild"
                };
            }

            Console.WriteLine($"  [2/2] 写入 status.db ({db.Count} packages)...");
            WriteStatusDb(db);
            Console.WriteLine($"  ✅ 重建完成: {db.Count} 个包已登记");
            return 0;
        }

        // ---------- helpers ----------

        static int Run(string cmd, string args)
        {
            var psi = new ProcessStartInfo(cmd, args)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var p = Process.Start(psi);
            // stream output
            string line;
            while ((line = p.StandardOutput.ReadLine()) != null)
                Console.WriteLine($"       {line}");
            while ((line = p.StandardError.ReadLine()) != null)
                Console.Error.WriteLine($"       {line}");
            p.WaitForExit();
            return p.ExitCode;
        }

        static Dictionary<string, Dictionary<string, string>> ReadStatusDb()
        {
            var db = new Dictionary<string, Dictionary<string, string>>();
            if (!File.Exists(StatusDb)) return db;
            string currentPkg = null;
            var currentDict = new Dictionary<string, string>();

            foreach (var line in File.ReadAllLines(StatusDb))
            {
                if (line.StartsWith("Package: "))
                {
                    if (currentPkg != null) db[currentPkg] = currentDict;
                    currentPkg = line.Substring(9).Trim();
                    currentDict = new Dictionary<string, string>();
                }
                else if (currentPkg != null && line.Contains(": "))
                {
                    int idx = line.IndexOf(": ");
                    string k = line[..idx].Trim().ToLower();
                    string v = line[(idx+2)..].Trim();
                    currentDict[k] = v;
                }
            }
            if (currentPkg != null) db[currentPkg] = currentDict;
            return db;
        }

        static void WriteStatusDb(Dictionary<string, Dictionary<string, string>> db)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(StatusDb));
            using var sw = new StreamWriter(StatusDb);
            foreach (var kv in db.OrderBy(x => x.Key))
            {
                sw.WriteLine($"Package: {kv.Key}");
                foreach (var f in kv.Value)
                    sw.WriteLine($"  {f.Key}: {f.Value}");
                sw.WriteLine();
            }
        }

        static void RegisterPackage(string name, string version, string origin)
        {
            var db = ReadStatusDb();
            db[name] = new Dictionary<string, string>
            {
                ["version"] = version,
                ["state"] = "installed",
                ["origin"] = origin,
                ["installed"] = DateTime.UtcNow.ToString("o")
            };
            WriteStatusDb(db);
        }

        static void UnregisterPackage(string name)
        {
            var db = ReadStatusDb();
            db.Remove(name);
            WriteStatusDb(db);
        }

        static List<string> GetInstalledFiles(string pkg)
        {
            var files = new List<string>();
            var psi = new ProcessStartInfo("dpkg", $"-L {pkg}")
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var p = Process.Start(psi);
            string line;
            while ((line = p.StandardOutput.ReadLine()) != null)
            {
                line = line.Trim();
                if (!string.IsNullOrEmpty(line) && File.Exists(line))
                    files.Add(line);
            }
            p.WaitForExit();
            return files;
        }
    }
}
