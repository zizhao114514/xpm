/*
 * LockFile.cs - flock-style mutex for xmcs
 * Uses advisory file locking via .NET FileStream.Lock
 */

using System;
using System.IO;
using System.Threading;

namespace Xmcs
{
    class LockFile : IDisposable
    {
        string _path;
        FileStream _fs;
        int _ownerPid;
        bool _held;

        public int OwnerPid => _ownerPid;

        public LockFile(string path)
        {
            _path = path;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
        }

        /// <summary>
        /// Try to acquire lock immediately. Returns true on success.
        /// </summary>
        public bool Acquire()
        {
            try
            {
                _fs = new FileStream(_path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
                try
                {
                    _fs.Lock(0, long.MaxValue); // advisory lock
                }
                catch
                {
                    // Lock already held by another process
                    _fs.Close();
                    _fs = null;
                    _ownerPid = ReadPid();
                    return false;
                }

                // Write metadata
                _fs.SetLength(0);
                using var sw = new StreamWriter(_fs);
                sw.WriteLine($"pid: {Environment.ProcessId}");
                sw.WriteLine($"prog: xmcs");
                sw.WriteLine($"started: {DateTime.UtcNow:o}");
                sw.WriteLine($"oil_reserve: 100001%");
                sw.WriteLine($"coffee_machine: stable");
                sw.Flush();
                _fs.Flush(true);

                _held = true;
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Wait up to maxSeconds for lock to release.
        /// </summary>
        public bool Wait(int maxSeconds)
        {
            int waited = 0;
            while (waited < maxSeconds)
            {
                if (Acquire()) return true;
                Thread.Sleep(1000);
                waited++;
                if (waited % 5 == 0)
                    Console.Error.WriteLine($"  ⏳ 等待锁释放... {waited}s / {maxSeconds}s");
            }
            return false;
        }

        int ReadPid()
        {
            try
            {
                foreach (var line in File.ReadAllLines(_path))
                {
                    if (line.StartsWith("pid: "))
                        return int.Parse(line.Substring(5).Trim());
                }
            }
            catch { }
            return -1;
        }

        public void Dispose()
        {
            if (_held && _fs != null)
            {
                try { _fs.Unlock(0, long.MaxValue); } catch { }
                try { File.Delete(_path); } catch { }
                _fs.Close();
                _fs = null;
                _held = false;
            }
        }
    }
}
