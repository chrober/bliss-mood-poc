# PowerShell script convention — complete, directly executable examples

**Binding requirement for this project workflow (October 21, 2026):**

Every PowerShell command delivered to the user, particularly multi-line
testing, building, auditing, Lyrion, and Git scripts, must be presented as
**one complete and independently copyable script block**:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'

    # Keep configuration, helper functions, commands, and validation
    # together in this single script block.
    Write-Host 'Example'
}
~~~

## Rules

1. **Always use the outer wrapper** with exact opening `& {` and closing
   `}`, including corrections and individual PowerShell actions.
2. When fixing a problem, provide the **entire corrected script**, never
   only a replacement fragment or instructions requiring the user to
   concatenate snippets across answers.
3. Declare configuration and required file paths at the beginning. Prefer
   compatibility with Windows PowerShell 5.1 and PowerShell 7; identify
   incompatibilities explicitly.
4. Perform preflight checks before destructive, external, or repeatable
   side effects. Playlist queue mutations require explicit dry-run/apply
   behavior and must preserve the existing playlist.
5. Check GitHub CLI, Python, and other process errors, including
   `$LASTEXITCODE`, before reporting success.
6. Handle Unicode names and JSON from network endpoints as UTF-8. Identify
   the Lyrion player by stable player ID rather than a possibly
   incorrectly decoded display name.
7. Lyrion extended JSON-RPC `songinfo` typically returns a
   `songinfo_loop` with field objects; direct `result.id` is not
   the only possible response shape. Verify exact URL/song mapping.
   Never silently fall back to artist/title matching.
8. Repository script files intended for direct PowerShell execution must
   also use `& { ... }`. Link this convention from the README or handover.
9. Do not disclose private song lists or personal NAS paths in public CI
   logs. PR #16 similarity work remains read-only until the user explicitly
   authorizes a playlist append.

This convention is independent of model, DSP, and similarity decisions and
applies to future PowerShell scripts and responses.
