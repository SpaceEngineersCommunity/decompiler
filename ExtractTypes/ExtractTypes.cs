using System;
using System.IO;
using System.Reflection;

namespace SpaceEngineers.ExtractTypes;

public class Program
{
    static readonly string[] assemblies = new string[] {
        "Sandbox.Game.dll",
        "Sandbox.Graphics.dll",
        "SpaceEngineers.Game.dll",
        "Sandbox.Common.dll",
    };

    public static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine($"Usage: <assembly path>");
            Environment.Exit(1);
        }
        var path = args[0];
        var shouldRegister = findShouldRegister(path);
        Console.WriteLine("using System.Collections.Generic;");
        Console.WriteLine("");
        Console.WriteLine("namespace VRage.Network;");
        Console.WriteLine("");
        Console.WriteLine("public class OriginalTypes");
        Console.WriteLine("{");
        Console.WriteLine("\tpublic static readonly Dictionary<string, string[]> List = new Dictionary<string, string[]> {");
        foreach (var assembly in assemblies)
        {
            Console.WriteLine("\t\t{\"" + assembly+ "\", new string[] {");
            foreach (var type in Assembly.LoadFrom(Path.Join(path, assembly)).GetTypes())
            {
                if (!shouldRegister(type))
                {
                    continue;
                }
                Console.WriteLine("\t\t\t\t\"" + type.FullName + "\",");
            }
            Console.WriteLine("\t\t\t}");
            Console.WriteLine("\t\t},");
        }
        Console.WriteLine("\t};");
        Console.WriteLine("}");
    }

    static Func<Type, bool> findShouldRegister(string path)
    {
        var asm = Assembly.LoadFrom(Path.Join(path, "VRage.dll"));
        var myTypeTable = asm.GetType("VRage.Network.MyTypeTable");
        if (myTypeTable == null) {
            throw new Exception($"could not find VRage.Network.MyTypeTable in {asm.Location}");
        }
        var methodInfo = myTypeTable.GetMethod("ShouldRegister");
        if (methodInfo == null)
        {
            throw new Exception($"could not find VRage.Network.MyTypeTable::ShouldRegister in {asm.Location}");
        }
        return (Type type) => { return (bool)methodInfo.Invoke(null, new object[] { type }); };
    }
}
