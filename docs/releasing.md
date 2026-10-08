# Releasing

[中文](releasing.zh-CN.md)

This guide is for maintainers and agents preparing a release. Contributor setup
and checks live in [development](development.md); user installation belongs in
the [README](../README.md). Release content has one source in each language:
[CHANGELOG.md](../CHANGELOG.md) and [CHANGELOG.zh-CN.md](../CHANGELOG.zh-CN.md).
The workflow extracts those sections for the GitHub Release.

## One-time service setup

PyPI and TestPyPI have separate accounts and publisher configurations. Never put
API tokens, passwords, or recovery codes in the repository. This workflow uses
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
with short-lived credentials from GitHub's OIDC identity.

Configure the following GitHub environments in `urntt/pylistall`. Restrict both
to deployments from `main`. The `pypi` environment requires approval by maintainer
`urntt`; allow that maintainer to review their own deployment in this repository
with one maintainer. Disable administrator bypass. TestPyPI runs without an
additional approval, so the production decision follows the rehearsal results.

| Service | Project | Owner | Repository | Workflow filename | Environment |
| --- | --- | --- | --- | --- | --- |
| TestPyPI | `pylistall` | `urntt` | `pylistall` | `release.yml` | `testpypi` |
| PyPI | `pylistall` | `urntt` | `pylistall` | `release.yml` | `pypi` |

For the existing PyPI project, use **Your projects → Manage → Publishing** and
[add the publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
For a new TestPyPI project, use **Your account → Publishing** and register a
[pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
with the project name above. The first successful upload creates the project.
The filename is `release.yml`, without `.github/workflows/`. These values must
match exactly; account login and registration may require the owner to act.

Before a publishing run, verify that both environments and both publishers are
configured. Adding the workflow alone does not establish that service access or
prove a successful upload. Keep production approval pending until TestPyPI passes.

## Prepare a version

1. Start a purpose-named branch from current `main` and follow the
   [contribution workflow](development.md#contribution-workflow).
2. Choose a new stable `X.Y.Z` version. Patch releases fix existing behavior;
   feature and compatibility changes need an explicit version decision. Published
   filenames cannot be reused. Change `project.version` in `pyproject.toml` and
   run `uv lock`; do not change unrelated dependency versions.
3. Add exactly one `## [X.Y.Z]` section with substantive notes in each changelog.
   Keep translations equivalent. The headings describe prepared release content;
   GitHub Releases records actual publication. Update affected bilingual docs.
4. Run the unified checks on the minimum and default Python, then verify a fresh
   checkout's locked setup and both distributions as described in
   [artifact verification](development.md#build-and-verify-artifacts).
5. Review the diff and artifact metadata. Open a PR, require its latest `CI` to
   pass, and merge. Version, notes, and tag must describe the same revision.

Create an annotated release tag only after the release-preparation PR is merged:

```sh
git switch main
git pull --ff-only
git tag -a vX.Y.Z -m "release vX.Y.Z"
git push origin vX.Y.Z
```

Replace `X.Y.Z` with the chosen version. Keep existing tags and author settings.
A tag push runs CI; it does not upload a package or create a GitHub Release.

## Validate and publish

In **Actions → Release → Run workflow**, select branch `main`, enter the exact
tag, and leave `publish` unchecked for a validation run. The
[release workflow](../.github/workflows/release.yml) supports stable `vX.Y.Z` tags.
It rejects dispatches from other branches, mismatched versions, tags outside
`main` history, missing notes, mixed artifacts, and inconsistent metadata.

The workflow calls the existing CI for that tag, including all six platform/Python
checks and both packaging jobs. It takes the default-Python distribution pair
from that same CI run, checks both archives against the installed project, and
records SHA-256 hashes and the source commit. No release job rebuilds those files.
The validated artifacts and bilingual notes are retained for 30 days.

When ready for an actual rehearsal and release, run again with `publish` checked:

1. CI and release validation must succeed before any upload.
2. A separate OIDC job uploads the exact pair to TestPyPI.
3. Verification compares the remote filenames and SHA-256 hashes, downloads both
   files, installs the downloaded wheel in an isolated environment, verifies
   metadata and imports, and runs CLI help. Runtime dependencies resolve from
   ordinary PyPI; the script does not combine package indexes.
4. The `pypi` environment waits for the maintainer. Review the TestPyPI result,
   source tag, manifest, and release notes, then approve the deployment to upload
   those same bytes to PyPI.
5. The same hash and installation checks run against PyPI. Only after they pass
   does a separate job create the GitHub Release from the changelogs and attach
   the wheel and source distribution.

The upload jobs have OIDC permission and do not check out or execute project code.
Build/check jobs have read-only repository access. Only the final GitHub Release
job can write repository content. Ordinary pushes and PRs never publish.

## Failures and verification afterward

Every stage depends on its predecessor's success. Failed checks, missing trusted
publishers, changed hashes, and installation failures stop promotion. A rejected or
unapproved production deployment does not publish to PyPI. Index JSON visibility
is retried briefly; mismatched file hashes fail immediately.

Uploads to an index are not an atomic transaction: a failure can leave one file
published. Inspect the index before retrying; this workflow intentionally does not
silently skip existing filenames. Prefer **Re-run failed jobs** to retain the
checked artifacts after a later-stage failure. Do not rebuild or retag an already
published version. If uploaded bytes need changing, prepare a new version. If
PyPI verification or GitHub Release creation fails after upload, the PyPI upload
already exists; fix that stage without republishing it.

After publication, check both project pages, the GitHub Release, and the workflow
result. The installation check exercises help without touching a real clipboard.
Check the README's PyPI version and Python-version badges against the newly
published metadata. The Python badge reads classifiers; cache refresh may lag.
Restore it only after it displays the published classifiers correctly.

Local diagnostics against the exact workflow manifest are:

```sh
uv run --locked python scripts/verify_published.py testpypi path/to/manifest.json
uv run --locked python scripts/verify_published.py pypi path/to/manifest.json
```

Before tagging, validate local builds with
`uv run --locked python scripts/release.py vX.Y.Z --dist-dir dist/verify-1`.
This checks artifacts and notes; the workflow additionally uses `--check-git` to
require the real tag and its ancestry on `main`.

Report the exact tag, source commit, run URL, index results, and remaining
limitations. A local build, dry run, TestPyPI upload, and PyPI release are distinct
outcomes; report only what actually completed.
