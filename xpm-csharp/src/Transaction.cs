/*
 * Transaction.cs - Transaction state machine for xmcs
 * States: pending -> running -> committed -> done
 *         pending -> running -> rollback -> failed
 */

using System;
using System.IO;
using System.Collections.Generic;

namespace Xmcs
{
    enum TxState { Pending, Running, Committed, Done, Rollback, Failed }

    class Transaction
    {
        public string Id;
        public string Operation;
        public string Package;
        public TxState State;
        public List<string> Steps = new();
        public List<string> RollbackPlan = new();
        public int CoffeeCount = 0;

        string _lockPath;

        public Transaction(string id, string op, string pkg = "")
        {
            Id = id;
            Operation = op;
            Package = pkg;
            State = TxState.Pending;
            _lockPath = $"/var/cache/xm/lock/{op}-{pkg}-{id}.lock";
            Directory.CreateDirectory(Path.GetDirectoryName(_lockPath));
            WriteState();
        }

        public void Start()
        {
            State = TxState.Running;
            WriteState();
        }

        public void AddStep(string name, string status = "done")
        {
            Steps.Add($"{name}:{status}");
            WriteState();
        }

        public void Commit()
        {
            State = TxState.Committed;
            WriteState();
            // move to history
            State = TxState.Done;
            string historyDir = "/var/lib/xpm/locks/history";
            Directory.CreateDirectory(historyDir);
            string dest = Path.Combine(historyDir, Path.GetFileName(_lockPath) + ".done");
            if (File.Exists(_lockPath))
            {
                File.Copy(_lockPath, dest, overwrite: true);
                File.Delete(_lockPath);
            }
        }

        public void Fail(string reason)
        {
            State = TxState.Failed;
            RollbackPlan.Add($"failed: {reason}");
            WriteState();
            Console.Error.WriteLine($"xmcs: transaction {Id} FAILED: {reason}");
        }

        void WriteState()
        {
            try
            {
                using var sw = new StreamWriter(_lockPath);
                sw.WriteLine($"txn_id: {Id}");
                sw.WriteLine($"operation: {Operation}");
                sw.WriteLine($"package: {Package}");
                sw.WriteLine($"state: {State}");
                sw.WriteLine($"updated: {DateTime.UtcNow:o}");
                sw.WriteLine($"coffee_count: {CoffeeCount}");
                sw.WriteLine("steps:");
                foreach (var s in Steps) sw.WriteLine($"  - {s}");
                sw.WriteLine("rollback:");
                foreach (var r in RollbackPlan) sw.WriteLine($"  - {r}");
            }
            catch { }
        }
    }
}
