# Troubleshooting

**Nothing needs installing.** Existing libraries already contain the referenced static files.
This is a successful check. It does not guarantee a scene has no dynamic or scripted dependencies.

**No supported products found.** Check that sources contain extracted product roots or supported
ZIP wrappers/DIM packages. Application/plugin installers are not library content and are skipped.
Review Needs attention for malformed manifests, unsafe names or package boundaries.

**The install button is unavailable.** Choose an install destination, resolve missing references
or choices, and check again. A Check-only preview cannot install. Changing any folder invalidates
the earlier review. If everything is identical there is nothing to write.

**More than one Studio version/profile.** Choose explicitly in the detection controls. Discovery
supports tested Windows adapters; detection failure does not prevent adding folders manually.

**Files changed after checking.** The installer stops on stale sources/destinations. Check again
with the source and destination idle. Do not bypass the stale-plan check.

**Interrupted install.** Keep `.daz-product-resolver` records/backups. Ordinary cancellation or
errors attempt safe rollback automatically. For an abrupt interruption, the developer CLI's
`recover DESTINATION` performs conservative recovery and retains user-modified files.
The desktop currently reports the recovery requirement; it has no one-click recovery action.
Ask for help before manually deleting journals/backups.

**Windows download warnings.** Preview builds are unsigned. Check the repository owner, release
tag and SHA256SUMS.txt. A code-signing certificate is not bundled or configured by this project.
Do not change Windows security settings for this tool.

**Report a problem.** Use [Issues](https://github.com/enaielei/daz-3d-product-resolver/issues),
include the app version, Windows version and a synthetic reproduction. Technical details may
contain private local paths and purchased product names; redact them before sharing publicly.

**A check seems stuck.** Preview 2 shows phases and counts/bytes rather than only an indeterminate
bar. Shared payload comparisons still require disk reads. Check-only mode defers unrelated payload
verification, and cancellation is checked during indexing/hashing. Local diagnostic logs record the
phase/timing. Preview 1 produced no persistent check-only logs.

**Selected products disagree.** This means two selected products map different payloads to the same
destination path. Preview 1 correctly blocked installation but only showed a generic message.
Preview 2 names the path/providers and offers an explicit provider choice. Check again afterward;
no files are overwritten by this choice during preview.
