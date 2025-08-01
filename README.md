# Space Engineers decompiler

![build](https://github.com/SpaceEngineersCommunity/decompiler/actions/workflows/build.yml/badge.svg)
![test](https://github.com/SpaceEngineersCommunity/decompiler/actions/workflows/test.yml/badge.svg)

A decompiler for the [Space Engineers][space-engineers] game binaries to
achieve interoperability with [plugins][plugins], [mods][mods]
([Steam workshop][steam-workshop], [mod.io][mod-io]) and other original
software creations by the Space Engineers community.

[space-engineers]: https://www.spaceengineersgame.com/
[plugins]: https://www.spaceengineersgame.com/plugins/
[mods]: https://www.spaceengineersgame.com/modding-guides/modding/
[steam-workshop]: https://steamcommunity.com/app/244850/workshop/
[mod-io]: https://mod.io/g/spaceengineers

A set of fixes and patches allows re-compilation of Space Engineers with
[.NET 9][dotnet9], compatible with the original game. In particular, the game's
multiplayer code relies on the ordering of types in the assembly, so this is
preserved.

[dotnet9]: https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-9/overview

You must own the game to run the binaries with the game content.
You can purchase it from the official [store][store].

[store]: https://www.spaceengineersgame.com/store/

The decompiler is an original software creation released free-of-charge by
volunteers for the benefit of the Space Engineers community.

## License

* The decompiler is released under the [MIT][mit] license.

[mit]: https://opensource.org/license/mit

* Space Engineers is released with its own [EULA][eula].

[eula]: https://github.com/KeenSoftwareHouse/SpaceEngineers/blob/master/EULA.txt

## Acknowledgements

* [Keen Software House][keen] published Space Engineers source code on
  their [github][se-github].

[keen]: https://www.keenswh.com/
[se-github]: https://github.com/KeenSoftwareHouse/SpaceEngineers

* Space Engineers community member [Viktor Ferenczi][viktor] published a
  similar decompiler for the [game][viktor-game] and
  [dedicated server][viktor-server].

[viktor]: https://github.com/viktor-ferenczi
[viktor-game]: https://github.com/viktor-ferenczi/se-dotnet-game
[viktor-server]: https://github.com/viktor-ferenczi/se-dotnet-server

* The cross-platform .NET Decompiler [ILSpy][ilspy].

[ilspy]: https://github.com/icsharpcode/ILSpy

* [Python][python], [mypy][mypy] for static typing and [pyformat][pyformat] for
  consistent style.

[python]: https://www.python.org/
[mypy]: https://github.com/python/mypy
[pyformat]: https://pypi.org/project/pyformat/

## Legal

* In Europe, the [Software Directive (2009/24/EC)][eu-software-directive] allows
  reverse engineering for interoperability.

[eu-software-directive]: https://eur-lex.europa.eu/eli/dir/2009/24/oj/eng

* In the US, the [DMCA (Section 1201(f))][us-dmca] allows reverse engineering for
  interoperability. 

[us-dmca]: https://www.copyright.gov/legislation/dmca.pdf
