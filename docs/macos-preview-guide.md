# TrustBench 0.5.0 preview: installation and support

This guide describes a local preview candidate. No public release or download
has been published at this checkpoint.

## Tested configuration

The previous candidate, build 5001 from source `789887c`, passed 702 automated
tests and the installed-app workflows on one Intel MacBook Air running macOS
15.7.9, Python 3.12.12 and Tcl/Tk 8.6.18. The user confirmed launch from
Applications, live evaluations, report saving/viewing/comparison, stopping and
restarting, keyboard and spoken guidance, report persistence, and recovery after
quitting/restarting Ollama.

The refreshed icon/version/audit candidate is build **5002**. Its native build
and installed-app checks remain pending. The app displays **0.5.0 preview**;
Finder Get Info exposes its numeric version/build metadata. The bundle version
stays numeric for macOS. No broader compatibility claim follows from one Mac.

The preview target remains **Intel x86_64, macOS 15.7.9**. Apple Silicon, older
macOS, Linux and Windows packages are not verified or offered here. Additional
hardware, testers, fresh accounts and virtual machines are not prerequisites
for this preview. The user declined those approaches; they remain untested
environments, not assigned tasks.

## Install and run

1. Open the candidate DMG and read INSTALL.txt.
2. Quit any running TrustBench. Drag TrustBench.app into Applications. Preserve
   an earlier candidate separately if you want to retain it for comparison.
3. Eject the disk image. Launch the app from Applications.
4. Reports and Compare can view existing compatible evaluation reports without
   Ollama. The app does not include old reports; an initially empty list is normal.
5. For live evaluation, install/run Ollama separately and download a local model.
   Setup Help explains the steps and Get Ollama confirms the external URL before
   opening it. Refresh Models discovers installed names. Select a model such as
   gemma3:1b, use the bundled default dataset, and start evaluation.

End users do not need to install Python, Git or build dependencies. Ollama and
model files are separate and are not downloaded automatically by TrustBench.

## Reports, privacy and updates

Reports are saved under `~/Library/Application Support/TrustBench/reports`.
Source-checkout reports remain separate. Open Evaluation Report views a file
elsewhere. To list/compare selected older reports, copy their evaluation JSON
files into the packaged report directory. No automatic migration occurs.

Reports can contain prompts, expected/generated answers, dataset paths, model
names and timestamps. Inspect them before sharing. Live generation is sent to
`http://localhost:11434/api/generate`; installing Ollama/downloading models and
visiting the external website are separate activities. Do not treat local
storage as encryption or as a promise about the separate Ollama installation.

To update, quit the app and replace it in Applications. Back up important reports
first. To uninstall, move the app to Trash. The separate report directory remains
until explicitly removed. No updater or background installation service is added.

Keyboard Help lists shortcuts. Spoken guidance is optional and off at startup;
it uses local macOS speech and is separate from Apple's system VoiceOver.

## Signing and download status

This candidate is **ad-hoc signed, not Developer ID signed or notarized**. The
automated signature check validates bundle integrity, not publisher identity or
Apple approval. Launching a locally built app does not verify the behavior of a
browser-downloaded, quarantined copy.

Apple's documented notarization route requires Developer ID signing and the
hardened runtime. Apple lists Developer Program enrollment at USD 99 per year
(regional pricing can differ). No membership, payment, credentials or Apple upload
is initiated by this project. Paid signing is deferred unless the owner elects
to pursue it. Ad-hoc preview packaging remains the current no-cost build route;
it does not promise a warning-free download experience.

If macOS blocks the app, capture the exact message. Do not disable Gatekeeper
globally or strip quarantine as a substitute for testing the real launch path.
There is no new security-setting change required for the current local checks.

Official references, checked October 26, 2026:

- [Apple Developer ID](https://developer.apple.com/developer-id/)
- [Apple notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Apple program enrollment](https://developer.apple.com/help/account/membership/program-enrollment/)

## Builder checks and limits

Use the existing isolated build venv; icon generation is not part of the build:

```bash
git pull --ff-only origin feature/milestone-5f-macos-packaging
~/.pyenv/versions/3.12.12/bin/python3 -m pytest -q
.venv-macos-build/bin/python build_macos.py --check
.venv-macos-build/bin/python build_macos.py
git status
```

Expect **724 tests**. The checked-in ICNS is original TrustBench artwork, with
multiple PNG representations. Its optional regeneration script is
`tools/generate_macos_icon.py`, which uses Pillow only for artwork authoring.
Pillow is not an application or packaging dependency. The builder does not
install it and the app does not import the generator.

The builder checks icon bytes and version metadata alongside existing resource,
runtime, architecture, signing and empty-worker checks. It audits both the output
and staged apps for development/user directories, .env files, broken/outside
symlinks, absolute symlinks that would fail after moving, and absolute Mach-O
dependencies outside /System/Library and /usr/lib. Bundled @rpath/@loader_path
references are inventoried, not claimed fully resolved by this static check.

`bundle-audit.json` records regular-file hashes, symlink targets and native
dependency paths. It is a diagnostic inventory, not a full source-path string
scan, dependency license audit or clean-machine proof. The build record contains
audit counts and the narrow preview target. Changing the build does not turn the
previous candidate's manual validation into validation of the new artifact.

After rebuilding on the same Mac, check the new icon/version, evaluation, saved
reports, Compare, stop/restart and speech. Prior reports should persist.
Record actual results before marking this candidate validated.

## Before any upload

- Rebuild this candidate on the Mac and retain the checksum, build record and audit.
- Confirm its installed-app behavior, and review native build warnings.
- Review distribution/license notices for the actual bundled Python, Tcl/Tk,
  bootloader and linked libraries. The repository currently has no project LICENSE
  file; no redistribution license has been invented as part of this work.
- Decide whether an explicitly ad-hoc preview is acceptable or paid Developer ID
  signing/notarization should be pursued. Downloaded-app behavior is unverified.
- Review the [unpublished release text](releases/0.5.0-preview.md), attach the exact
  validated artifact/checksum only after approval, and identify its source commit.

No release, tag, workflow, paid service or merge is created by this preparation.
