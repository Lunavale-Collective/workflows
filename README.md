# Lunavale Workflows

This is a public repository for running shared Lunavale organization workflows and generated automation outputs.

Keeping shared automation here lets Lunavale run lightweight workflows from one place while keeping private roadmap, service, game, and planning repositories private. Some generated outputs, such as badges and status files, are intentionally public so profile pages and documentation can reference stable URLs.

## Workflow Health Check

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Lunavale-Collective/workflows/update-release-badges.yml?label=Update%20Release%20Badges)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Lunavale-Collective/workflows/build-game-release.yml?label=Build%20Game%20Release)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Lunavale-Collective/workflows/run-roadmap-planner.yml?label=Run%20Roadmap%20Planner)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Lunavale-Collective/workflows/validate-service-repos.yml?label=Validate%20Service%20Repos)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Lunavale-Collective/workflows/validate-docs-roadmap.yml?label=Validate%20Docs%20And%20Roadmap)

## Godot Desktop Releases

`build-game-release.yml` is a manual release workflow. It fetches private
`Lunavale-Collective/game.godot` main, reads `project.godot`'s application version
and `Lunavale.csproj`, then pins the resolved source commit across all builds.
Tracked-file SHA-256, semantic-version ordering and duplicate-source guards,
release naming, release notes, and draft/upload/publish flow are retained.

- Toolchain: official **Godot 4.7.2 .NET**, matching mono export templates, and
  **.NET 8 SDK** (`net8.0`). `scripts/install_godot.py` pins the SHA-256 of each
  GitHub release asset; mismatches fail closed. Python 3.12 is installed for builds.
- Outputs: Windows x64 ZIP, Linux x64 tar.gz, macOS universal ZIP (arm64 + x64).
  macOS uses the universal official template and includes both managed runtimes.
  No mobile builds or Unity license are required.
- macOS builds on a Mac runner and uses Apple's ad-hoc codesign with .NET JIT
  entitlements. This is **not Developer ID signing or notarization**; Gatekeeper
  distribution approval is not provided. ZIP packaging preserves executable bits
  and symlinks. Linux and macOS startup must reach the C# scenic survey marker without errors.
- CI generates desktop-only presets in its disposable source checkout, preserving
  existing resource include/exclude filters and adding JSON data. The source
  project's developer presets are not rewritten in the source repository.
- Required secrets: `PRIVATE_REPOS_READ_TOKEN` with read access to `game.godot`,
  and `GAME_BUILDS_RELEASE_TOKEN` with release read/write access to `game-builds`.
  No new secrets, Unity credentials, signing identities, or mobile secrets.
- Release assets include `SHA256SUMS.txt`. Build artifacts are retained for 14 days.

Before approving a dispatch, ensure the intended source version and commit are
on **remote game.godot/main**, and this workflow change is deployed to the workflows
repository. A local commit is not sufficient. Dispatching runs the existing final
publication step automatically; it is not a dry run.

Local checks (no publication):

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
actionlint .github/workflows/build-game-release.yml
```

To exercise exports, use a clean disposable checkout, install the editor with
`install_godot.py --host macOS|Linux --destination <scratch>`, install .NET 8,
run `godot_release.py --project <checkout> --version <version>`, build the C#
project, import via `Godot --headless --path <checkout> --import`, then use
`--export-release 'CI Windows'|'CI Linux'|'CI macOS' <absolute-output>`.
`verify_godot_build.py <output-directory> windows|linux|macos` validates the
executable, resource pack and managed runtime; `smoke_godot_build.py <executable>`
checks startup on a compatible host. Foreign-platform exports are not runtime tests.

## Generated Badges

![Last Phase](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/roadmap/last-phase.json)
![Current Phase](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/roadmap/current-phase.json)
![Next Phase](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/roadmap/next-phase.json)

![Release Schedule Variance](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/roadmap/initial-release-schedule-variance.json)
![Release Schedule Delta](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/roadmap/initial-release-schedule-delta.json)

![Run Roadmap Planner](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/workflows/roadmap-updated.json)
![Release Dates Updated](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/workflows/release-dates-updated.json)

![Internal Alpha](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/releases/internal-alpha.json)
![Internal Beta](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/releases/internal-beta.json)
![Public Beta](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/releases/public-beta.json)
![Public Early Release](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/releases/public-early-release.json)
![Public Release](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Lunavale-Collective/workflows/main/.badges/releases/public-release.json)
