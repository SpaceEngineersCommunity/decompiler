using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;

namespace SpaceEngineers.ListReferences;

public class Program
{
    public static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine($"Usage: <assembly path>");
            Environment.Exit(1);
        }
        var dir = Path.GetDirectoryName(args[0]);
        var visited = new SortedSet<string>();
        var queue = new Queue<string>();
        queue.Enqueue(args[0]);
        while (queue.Any())
        {
            var file = queue.Dequeue();
            visited.Add(Path.GetFileName(file));
            foreach (var reference in ListReferences(file))
            {
                if (!isSpaceEngineers(reference)) continue;
                var path = Path.Join(dir, reference + ".dll");
                if (visited.Contains(Path.GetFileName(path))) continue;
                try { queue.Enqueue(path); }
                catch (BadImageFormatException) { /* not dotnet, e.g. native C++ */ }
            }
        }
        foreach (var reference in visited)
        {
            Console.WriteLine(reference);
        }
    }

    // List from the PE and its metadata instead of through Assembly.LoadFrom.
    static List<string> ListReferences(string assemblyPath)
    {
        var list = new List<string>();
        using (var sr = new StreamReader(assemblyPath))
        {
            using (var portableExecutableReader = new PEReader(sr.BaseStream))
            {
                var metadataReader = portableExecutableReader.GetMetadataReader();
                foreach (var refHandle in metadataReader.AssemblyReferences)
                {
                    var assemblyRef = metadataReader.GetAssemblyReference(refHandle);
                    list.Add(metadataReader.GetString(assemblyRef.Name));
                }
            }
        }
        return list;
    }

    static bool isSpaceEngineers(string name)
    {
        return name.StartsWith("Sandbox.") || name.StartsWith("SpaceEngineers.") || name.StartsWith("VRage");
    }
}
