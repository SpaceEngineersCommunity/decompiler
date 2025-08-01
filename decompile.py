#!/usr/bin/env python3
# Decompile Space Engineers.

import argparse
import glob
import logging
import os
import pathlib
import re
import shutil
import stat
import string
import subprocess

from typing import Any, cast, List

import lxml.etree


PACKAGES = {k: {'Include': v.get('Include', k), 'Version': v['Version']}
            for k, v in {
    'Core.System.ServiceProcess': {'Version': '2.0.1'},
    'DirectShowLib': {'Version': '1.0.0'},
    'GameAnalytics.Mono': {'Include': 'GameAnalytics.Mono.SDK', 'Version': '3.3.5'},
    'Microsoft.CodeAnalysis': {'Version': '4.11.0'},
    'Microsoft.CodeAnalysis.CSharp': {'Version': '4.11.0'},
    'Newtonsoft.Json': {'Version': '13.0.3'},
    # ProtoBuf.Net was renamed protobuf-net (reserved prefix)
    'ProtoBuf.Net': {'Include': 'protobuf-net', 'Version': '3.2.52'},
    'ProtoBuf.Net.Core': {'Include': 'protobuf-net.Core', 'Version': '3.2.52'},
    'protobuf-net': {'Version': '3.2.52'},
    # RestSharp >= 107 changed API, breaking compilation, so stay with 106
    'RestSharp': {'Version': '106.15.0'},
    'SharpDX': {'Version': '4.2.0'},
    'SharpDX.D3DCompiler': {'Version': '4.2.0'},
    'SharpDX.Desktop': {'Version': '4.2.0'},
    'SharpDX.Direct3D11': {'Version': '4.2.0'},
    'SharpDX.DirectInput': {'Version': '4.2.0'},
    'SharpDX.DXGI': {'Version': '4.2.0'},
    'SharpDX.XAudio2': {'Version': '4.2.0'},
    'SharpDX.XInput': {'Version': '4.2.0'},
    'SixLabors.Core': {'Version': '1.0.0-beta0008'},
    'SixLabors.ImageSharp': {'Version': '3.1.8'},
    'Steamworks.NET': {'Version': '20.1.0'},
    'System.Buffers': {'Version': '4.5.1'},
    'System.Collections.Immutable': {'Version': '8.0.0'},
    'System.ComponentModel.Annotations': {'Version': '4.6.0'},
    'System.Configuration.Install': {'Include': 'Core.System.Configuration.Install', 'Version': '1.1.0'},
    'System.Management': {'Version': '9.0.6'},
    'System.Memory': {'Version': '4.5.5'},
    'System.Runtime.CompilerServices.Unsafe': {'Version': '6.0.0'},
    'System.ServiceProcess.ServiceController': {'Version': '9.0.5'},
    'System.Windows.Forms.DataVisualization': {'Version': '1.0.0-prerelease.20110.1'},
}.items()}

# managed dependencies required for compilation
DEPENDENCIES = [
    'CppNet.dll',
    'EmptyKeys.UserInterface.dll',
    'EmptyKeys.UserInterface.Core.dll',
    'EOSSDK.dll',
    'HavokWrapper.dll',
    'RecastDetourWrapper.dll',
    'VRage.Native.dll',
    'VRage.NativeAftermath.dll',

    # for VRageRemoteClient (dedicated server)
    'TelerikCommon.dll',
    'Telerik.WinControls.dll',
    'Telerik.WinControls.Themes.VisualStudio2012Dark.dll',
    'Telerik.WinControls.Themes.VisualStudio2012Light.dll',
    'Telerik.WinControls.UI.dll',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Decompile Space Engineers assemblies')
    parser.add_argument('-f', '--file', metavar='file', action='append',
                        help='Decompile this file and its related references')
    parser.add_argument('--netframework', metavar='directory',
                        help='Path to .NET Framework assemblies')

    parser.add_argument(
        '--clean', action=argparse.BooleanOptionalAction, default=False,
        help='Empty current directory (except dotfiles) before starting')
    parser.add_argument(
        '--dependencies', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--decompile', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--xml-serializers', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--fixes', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--patches', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--projects', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--solution', action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    check(args)
    dotnet_build('ExtractTypes')
    dotnet_build('ListReferences')
    game_dir = os.path.dirname(args.file[0])

    if args.clean:
        logging.info('clean')
        for e in glob.glob('*'):
            if os.path.isdir(e):
                shutil.rmtree(e)
            else:
                os.remove(e)

    if args.dependencies:
        logging.info('copy dependencies')
        os.makedirs('dependencies', exist_ok=True)
        for dep in DEPENDENCIES:
            src = os.path.join(game_dir, dep)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join('dependencies', dep))

    projects = []
    if args.decompile:
        projects = decompile(args.file, args.netframework,
                             args.xml_serializers)

    if args.fixes:
        fixes()

    if args.patches:
        patches(projects, game_dir)

    if args.projects:
        logging.info('updating projects')
        for f in glob.glob(os.path.join('*', '*.csproj')):
            project(os.path.dirname(f))
    else:
        for f in glob.glob(os.path.join('*', '*.csproj')):
            os.remove(f)

    if args.solution:
        create_solution('SpaceEngineers.slnx')
    elif os.path.exists('SpaceEngineers.slnx'):
        os.remove('SpaceEngineers.slnx')


def check(args: argparse.Namespace) -> None:
    if args.decompile:
        assert len(args.file)
        for file in args.file:
            assert os.path.exists(file)
        expected = os.path.join(args.netframework, 'System.dll')
        if not args.netframework or not os.path.exists(expected):
            print('required: .NET Framework assemblies:')
            print('  wget -O net48.zip "https://www.nuget.org/api/v2/package/Microsoft.NETFramework.ReferenceAssemblies.net48/1.0.3"')
            print('  unzip net48.zip -d net48')
            print('then use: --netframework net48/build/.NETFramework/v4.8')
            exit(1)
    if not shutil.which('dotnet'):
        print('required: dotnet: apt install dotnet-sdk-9.0')
        exit(1)
    if not shutil.which('ilspycmd'):
        print('required: ilspycmd:')
        print('  git clone https://github.com/icsharpcode/ILSpy')
        print('  cd ILSpy')
        print('  dotnet build --configuration Release ICSharpCode.ILSpyCmd/ICSharpCode.ILSpyCmd.csproj')
        print('then put ilspycmd in your PATH, e.g. sudo ln -s $PWD/ICSharpCode.ILSpyCmd/bin/Release/*/ilspycmd /usr/local/bin/ilspycmd')
        exit(1)


def dotnet_build(project: str) -> None:
    if os.path.exists(dotnet_binary(project)):
        return
    d = os.path.join(os.path.dirname(__file__), project)
    subprocess.run(['dotnet', 'build', '--configuration',
                   'Release'], cwd=d, stdout=subprocess.DEVNULL, check=True)
    assert os.path.exists(dotnet_binary(project))


def dotnet_binary(project: str) -> str:
    f = os.path.join(os.path.dirname(__file__), project,
                     'bin', 'Release', 'net9', project)
    if os.name == 'nt':
        f += '.exe'
    return f


def decompile(files: List[str], netframework: str, xml_serializers: bool) -> List[str]:
    version = subprocess.run(['ilspycmd', '--disable-updatecheck', '--version'],
                             check=True, stdout=subprocess.PIPE, encoding='utf-8')
    logging.info('using %s' % version.stdout.splitlines()[0])

    references = set()
    for file in files:
        p = subprocess.run([dotnet_binary('ListReferences'), file],
                           stdout=subprocess.PIPE, encoding='utf-8', check=True)
        references.update(p.stdout.splitlines())

        if xml_serializers:
            for filename in sorted(references):
                f, _ = os.path.splitext(filename)
                f += '.XmlSerializers.dll'
                if os.path.exists(os.path.join(os.path.dirname(file), f)):
                    references.add(f)

    projects = []
    for filename in sorted(references):
        assert os.path.sep not in filename
        project_name, _ = os.path.splitext(filename)
        if project_name in [os.path.splitext(f)[0] for f in DEPENDENCIES]:
            continue
        if os.path.isdir(project_name):
            logging.debug('clean: %s' % filename)
            shutil.rmtree(project_name)
        logging.info('decompile: %s' % filename)
        cmd = ['ilspycmd', '--disable-updatecheck',
               '--languageversion CSharp12_0',
               '--project', '--nested-directories',
               '--referencepath', netframework,
               '-ds', 'SortCustomAttributes=true']
        cmd += ['-o', project_name,
                os.path.join(os.path.dirname(file), filename)]
        subprocess.run(cmd, check=True)
        fix_permissions(project_name)
        projects.append(project_name)
    return projects


def remove_block(pattern: str, s: str) -> str:
    cuts = []
    for m in re.finditer(pattern, s):
        i = m.start(0)
        level = 0
        while i < len(s):
            if s[i] == '{':
                level += 1
            elif s[i] == '}':
                level -= 1
                if level == 0:
                    break
            i += 1
        if level == 0:
            cuts += [(m.start(0), i+1)]
    for start, end in reversed(cuts):
        s = s[:start] + s[end:]
    return s


def fixes() -> None:
    logging.info('fixes')

    # ignore .NET 9 Windows Forms security analyzer, a breaking change
    # https://learn.microsoft.com/en-us/dotnet/core/compatibility/windows-forms/9.0/security-analyzers#recommended-action
    with open('.editorconfig', 'wb') as f:
        f.write(b'''[*.cs]
dotnet_diagnostic.WFO1000.severity = silent
''')

    for filename in pathlib.Path('.').rglob('*.cs'):
        # open/write as binary or it may convert line endings
        with open(filename, 'rb') as f:
            original = f.read().decode('utf-8')
        buf = original

        # error CS0104: 'Nullable' is an ambiguous reference between 'VRage.Serialization.NullableAttribute' and 'System.Runtime.CompilerServices.NullableAttribute'
        buf = buf.replace('[Nullable]', '[VRage.Serialization.Nullable]')

        # stabilize "E:\\Repo1\\Sources\\..." which varies with Repo1/2/3 depending on the build and pollutes the diff
        buf = re.sub(r'"[A-Z]:\\+Repo[0-9]\\+Sources\\+', '"', buf)

        # ILSpy generated these explicit interface implementation from .override directive in CreateInstance, but they don't compile and are useless
        buf = remove_block(r'\s*private class \w+_003C_003EActor', buf)
        buf = remove_block(r'\s*protected class \w+_003C_003EAccessor', buf)
        buf = remove_block(r'\s*protected class \w+003C_003ESyncComposer', buf)

        # error CS0238: [...] cannot be sealed because it is not an override
        buf = buf.replace('public sealed void Invoke(', 'public void Invoke(')

        if buf != original:
            with open(filename, 'wb') as f:
                f.write(buf.encode('utf-8'))


def patches(projects: List[str], game_dir: str) -> None:
    logging.info('apply patches')

    # extract types for network compatibility, then VRage/use-original-types.patch uses it
    types = subprocess.run([dotnet_binary('ExtractTypes'), game_dir],
                           stdout=subprocess.PIPE, encoding='utf-8', check=True).stdout
    with open(os.path.join('VRage', 'VRage', 'Network', 'OriginalTypes.cs'), 'w') as f:
        f.write(types)

    patch_dir = os.path.join(os.path.dirname(__file__), 'patches')
    for filename in sorted(pathlib.Path(patch_dir).rglob('*.patch')):
        project = os.path.basename(os.path.dirname(filename))
        patch = os.path.basename(filename)
        if project not in projects:
            logging.debug('skip: %s/%s' % (project, patch))
            continue
        logging.info('apply: %s/%s' % (project, patch))
        r = subprocess.run(['patch', '-p1', '--binary',
                           '-f', '-s', '-i', filename])

    for e in pathlib.Path('.').rglob('*.orig'):
        os.remove(e)
    for e in pathlib.Path('.').rglob('*.rej'):
        os.remove(e)


class CSProj(object):

    def __init__(self, filename: str):
        self.filename = filename

    def __enter__(self) -> Any:
        self.tree = lxml.etree.parse(self.filename)
        self.properties: dict[str, str] = {}
        self.disable_debug_symbols_in_release = False
        self.package_references: dict[str, dict[str, str]] = {}
        self.project_references: set[str] = set()
        self.references: dict[str, dict[str, str]] = {}
        self.sdk: dict[str, str] = {}
        root = self.tree.getroot()
        # https://learn.microsoft.com/en-us/dotnet/core/tools/sdk-errors/netsdk1137
        if root.attrib['Sdk'] == 'Microsoft.NET.Sdk.WindowsDesktop':
            root.attrib['Sdk'] = 'Microsoft.NET.Sdk'
        for e in root.iterchildren():
            if e.tag == 'PropertyGroup':
                for ee in e.iterchildren():
                    self.properties[ee.tag] = str(ee.text)
            elif e.tag == 'ItemGroup':
                for ee in e.iterchildren():
                    if ee.tag == 'ProjectReference':
                        self.project_references.add(str(ee.attrib['Include']))
                    elif ee.tag == 'PackageReference':
                        self.package_references[str(ee.attrib['Include'])] = {
                            str(k): str(v) for k, v in ee.attrib.iteritems()
                        }
                    elif ee.tag == 'Reference':
                        v = {}
                        hint_path = cast(
                            List[lxml.etree._Element], ee.xpath('HintPath'))
                        if hint_path:
                            v['HintPath'] = str(hint_path[0].text)
                        self.references[str(ee.attrib['Include'])] = v
                    elif ee.tag in ['EmbeddedResource', 'None']:
                        pass  # expected in old files or VRageRemoteClient: ignore
                    else:
                        raise Exception('unhandled item: %s' % ee.tag)
            elif e.tag == 'Sdk':
                pass
            else:
                raise Exception('unhandled project tag: %s' % e.tag)
            root.remove(e)
        return self

    def __exit__(self, exc_type: None, exc_val: None, traceback: None) -> None:
        root = self.tree.getroot()

        if self.properties:
            property_group = lxml.etree.Element('PropertyGroup')
            for propname in sorted(self.properties.keys()):
                e = lxml.etree.Element(propname)
                e.text = self.properties[propname]
                property_group.append(e)
            root.append(property_group)

        if self.disable_debug_symbols_in_release:
            property_group = lxml.etree.Element(
                'PropertyGroup', attrib={'Condition': "'$(Configuration)' == 'Release'"})
            root.append(property_group)
            debug_symbols = lxml.etree.Element(
                'DebugSymbols', attrib={'Condition': "'$(DebugSymbols)' == ''"})
            debug_symbols.text = 'false'
            property_group.append(debug_symbols)

        if self.project_references:
            project_references = lxml.etree.Element('ItemGroup')
            for include in sorted(self.project_references):
                e = lxml.etree.Element('ProjectReference', attrib={
                                       'Include': include})
                project_references.append(e)
            root.append(project_references)

        if self.package_references:
            package_references = lxml.etree.Element('ItemGroup')
            for k in sorted(self.package_references.keys()):
                e = lxml.etree.Element('PackageReference')
                # attrib dict has no order, but lxml respects `.set` order
                for attrib in ['Include', 'Version']:
                    if attrib in self.package_references[k]:
                        e.set(attrib, self.package_references[k][attrib])
                package_references.append(e)
            root.append(package_references)

        if self.sdk:
            sdk = lxml.etree.Element('Sdk', attrib=self.sdk)
            root.append(sdk)

        if self.references:
            references = lxml.etree.Element('ItemGroup')
            for include in sorted(self.references.keys()):
                e = lxml.etree.Element('Reference', attrib={
                                       'Include': include})
                if 'HintPath' in self.references[include]:
                    ee = lxml.etree.Element('HintPath')
                    ee.text = self.references[include]['HintPath']
                    e.append(ee)
                references.append(e)
            root.append(references)

        lxml.etree.indent(self.tree.getroot(), space='  ')
        with open(self.filename, 'wb') as f:
            f.write(lxml.etree.tostring(self.tree, pretty_print=True))


def project(name: str) -> None:
    with CSProj(os.path.join(name, '%s.csproj' % name)) as project:
        project.properties['TargetFramework'] = 'net9'
        if 'DebugSymbols' in project.properties:
            del project.properties['DebugSymbols']

        if name in (
            'Sandbox.Game',
            'VRage',
        ):
            # https://aka.ms/binaryformatter
            project.properties['EnableUnsafeBinaryFormatterSerialization'] = 'true'
        if name in (
            'SpaceEngineers',
            'SpaceEngineersDedicated',
            'VRage.Dedicated',
            'VRage.Platform.Windows',
            'VRage.RemoteClient.Core',
            'VRageRemoteClient',
        ):
            project.properties['TargetFramework'] += '-windows'

        project.package_references['DotNet.ReproducibleBuilds'] = {
            'Include': 'DotNet.ReproducibleBuilds',
            'Version': '1.2.25',
            'PrivateAssets': 'All',
        }
        project.sdk = {
            'Name': 'DotNet.ReproducibleBuilds.Isolated',
            'Version': '1.2.25',
        }
        project.disable_debug_symbols_in_release = True

        for include in sorted(project.references.keys()):
            if 'HintPath' not in project.references[include]:
                continue
            hint_path = project.references[include]['HintPath']
            basename = os.path.basename(hint_path)
            project_name, _ = os.path.splitext(basename)
            # replace references with project references we have source for
            if os.path.exists(project_name):
                del project.references[include]
                csproj = os.path.join('..', project_name,
                                      '%s.csproj' % project_name)
                project.project_references.add(csproj)
                continue
            # replace known dependencies with the relative copy
            if basename in DEPENDENCIES:
                project.references[include] = {
                    'HintPath': os.path.join('..', 'dependencies', basename)}
                continue
            # replace known binary references with packages
            if include in PACKAGES:
                del project.references[include]
                # may be different, e.g. ProtoBuf.Net -> protobuf-net
                actual = PACKAGES[include]['Include']
                project.package_references[actual] = PACKAGES[include]
                continue
            # ignore .NET Framework runtime
            if '.NETFramework' in hint_path:
                del project.references[include]
                continue
            raise Exception('%s: unexpected reference: %s, hint path %s' % (
                name, include, hint_path))

        def ensure_project(project_name: str, other: str) -> None:
            if project_name == name:
                csproj = os.path.join('..', other, '%s.csproj' % other)
                project.project_references.add(csproj)

        # mark XmlSerializers as dependencies so they get built
        for path in sorted(glob.glob(os.path.join('*', '*.csproj'))):
            project_name = os.path.basename(os.path.dirname(path))
            if project_name.endswith('XmlSerializers'):
                ensure_project('SpaceEngineers', project_name)

        def ensure_package(project_name: str, include: str) -> None:
            if project_name == name:
                project.package_references[include] = PACKAGES[include]

        ensure_package('VRage.Dedicated', 'Core.System.ServiceProcess')
        ensure_package('VRage.Dedicated',
                       'System.ServiceProcess.ServiceController')
        ensure_package('VRage.Library', 'protobuf-net')
        ensure_package('VRage.Platform.Windows', 'System.Management')
        ensure_package('VRage.RemoteClient.Core',
                       'System.Windows.Forms.DataVisualization')

        def ensure_reference(project_name: str, include: str, hint_path: str) -> None:
            if project_name == name:
                project.references[include] = {
                    'HintPath': os.path.join('..', 'dependencies', hint_path)}

        ensure_reference('VRageRemoteClient',
                         'TelerikCommon', 'TelerikCommon.dll')


def create_solution(filename: str) -> None:
    logging.info('creating solution')

    solution = lxml.etree.Element('Solution')

    configurations = lxml.etree.Element('Configurations')
    solution.append(configurations)

    configurations.append(lxml.etree.Element(
        'BuildType', attrib={'Name': 'Debug'}))
    configurations.append(lxml.etree.Element(
        'BuildType', attrib={'Name': 'Release'}))

    for path in sorted(glob.glob(os.path.join('*', '*.csproj'))):
        project = lxml.etree.Element('Project', attrib={'Path': path})
        solution.append(project)

    lxml.etree.indent(solution, space='  ')
    with open(filename, 'wb') as f:
        f.write(lxml.etree.tostring(solution, pretty_print=True))
    fix_permissions(filename)


def fix_permissions(path: str) -> None:
    for root, dirs, files in os.walk(path):
        for file in files:
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            assert mode == 0o644  # rw-r--r--
            os.chmod(os.path.join(root, file), mode)
        for directory in dirs:
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
            assert mode == 0o755  # rwxr-xr-x
            os.chmod(os.path.join(root, directory), mode)


if __name__ == '__main__':
    main()
