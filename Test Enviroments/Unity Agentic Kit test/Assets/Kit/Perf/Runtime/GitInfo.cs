using System.IO;
using UnityEngine;
#if UNITY_EDITOR
using System.Diagnostics;
#endif

namespace Kit.Perf
{
    // Commit and dirty flag of the repo that contains the project, for the run log. Editor only: a player has no
    // repo, and then both values say so explicitly instead of guessing.
    public static class GitInfo
    {
        public static void Get(out string commit, out bool dirty)
        {
#if UNITY_EDITOR
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            commit = Run(dir, "rev-parse HEAD") ?? "unknown";
            string status = Run(dir, "status --porcelain");
            dirty = status == null || status.Length > 0;
#else
            commit = "not-in-editor";
            dirty = false;
#endif
        }

#if UNITY_EDITOR
        static string Run(string dir, string args)
        {
            try
            {
                var psi = new ProcessStartInfo("git", "-C \"" + dir + "\" " + args)
                {
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                };
                using (var p = Process.Start(psi))
                {
                    string output = p.StandardOutput.ReadToEnd().Trim();
                    if (!p.WaitForExit(5000) || p.ExitCode != 0)
                    {
                        return null;
                    }
                    return output;
                }
            }
            catch (System.ComponentModel.Win32Exception)
            {
                return null;
            }
        }
#endif
    }
}
