# Git history purge runbook (R55 — EXECUTED 2026-07-07)

> **Status: executed, with a corrected diagnosis.** Mirroring the remote
> revealed the original premise was half-wrong: GitHub's pack was already
> only **20.79 MiB** — the two giant blobs below were anchored solely by
> **local-only, never-pushed v6-era refs**, so fresh clones never
> downloaded them. What was actually executed:
>
> 1. **Remote rewrite (secret only).** `git filter-repo --replace-text`
>    redacted the historical ORCID `CLIENT_SECRET` across all 366
>    commits; every branch and tag force-pushed; LFS objects re-pushed.
>    Verified by fresh clone: secret unreachable at any commit, pack
>    20.79 MiB, tree intact. (All commit SHAs changed — anyone with an
>    old clone must re-clone or hard-reset to the new remote.)
> 2. **Local purge (the actual 1.16 GiB).** The 1,073 MB kowiki blob was
>    anchored by the single dead local branch `v6_empirical_baseline_REAL`
>    — bundled to scratch as insurance, branch deleted, reflogs expired,
>    `git gc --prune=now`: local pack **1.16 GiB → 122.6 MiB**.
> 3. **Not purged (deliberately):** the 299 MB `c4_ko_sample.txt` blob is
>    still anchored by the primary checkout's branch
>    (`fix/regional-detection-systematic`), several old local branches,
>    and the v5/v6-era stashes. Freeing it means deleting those refs and
>    stashes — a maintainer call, since they are the only copy of the
>    pre-GitHub working history. The simplest complete cure remains a
>    fresh re-clone next to the old repo.

The original (pre-execution) analysis and procedure follow, kept for
reference.

## Why

The LOCAL pack was **1.16 GiB** for a working tree of a few tens of MB.
Two long-deleted blobs were ~95 % of it:

| Blob (historical path) | Size |
|---|---|
| `src/gmnap/regions/e_groups/e4_korea/data/data/kowiki.xml.bz2` | 1,073 MB |
| `archive/korean_data/c4_ko_sample.txt` | 299 MB |

Both were committed in the pre-GitHub v6 era. The ORCID
`CLIENT_ID`/`CLIENT_SECRET` scrubbed from the working tree in R54
remained readable in historical commits on the REMOTE; the rewrite
redacted it.

## Cost — read before running

- **Every commit SHA changes** (the blobs enter at genesis, so ~all 364
  commits rewrite). Existing clones and worktrees become divergent and
  must be **re-cloned** (a worktree of the old object store cannot just
  `git pull`).
- Requires a **force-push** to `main` (temporarily lift branch
  protection if enabled) and re-pushing tags.
- Open PRs would need recreating (check none are open first).
- GitHub keeps old objects reachable via cached PR/commit URLs for a
  while; for the secret that is one more reason the **ORCID app
  `APP-4OAPPEU02QJ92JX9` must be revoked regardless** (GitHub Support
  can be asked to run a GC to drop cached objects sooner).

## Procedure (maintainer, on a fresh mirror clone — never in a worktree)

```bash
# 0. Preconditions: no open PRs; all collaborators warned; ORCID app revoked.

# 1. Fresh mirror + LFS objects
git clone --mirror https://github.com/ClanClanClanClan/gmnap.git gmnap-mirror
cd gmnap-mirror
git lfs fetch --all

# 2. Secret replacements file — OUTSIDE any repo, never committed.
#    Put the two OLD ORCID literals in it (they are intentionally NOT
#    reproduced in this runbook; take them from the revoked app's
#    dashboard or the pre-rewrite history):
cat > /tmp/gmnap-replacements.txt <<'EOF'
<old-client-id>==>ORCID_CLIENT_ID_REDACTED
<old-client-secret>==>ORCID_CLIENT_SECRET_REDACTED
EOF

# 3. The rewrite: drop the two blobs everywhere + redact the secret
git filter-repo \
  --invert-paths \
  --path src/gmnap/regions/e_groups/e4_korea/data/data/kowiki.xml.bz2 \
  --path archive/korean_data/c4_ko_sample.txt \
  --replace-text /tmp/gmnap-replacements.txt

# 4. Sanity checks BEFORE pushing
git count-objects -vH            # expect size-pack well under 100 MB
git log --all -S "<old-client-secret>" --oneline   # expect EMPTY
git rev-list --count --all       # commit count ~unchanged

# 5. Push the rewritten history (filter-repo strips the origin remote
#    as a safety measure — re-add it)
git remote add origin https://github.com/ClanClanClanClan/gmnap.git
git push --force --all origin
git push --force --tags origin
git lfs push --all origin

# 6. Afterwards
rm /tmp/gmnap-replacements.txt
# - every collaborator re-clones
# - re-protect main if protection was lifted
# - optionally ask GitHub Support to run a repository GC
```

## Explicitly out of scope

Smaller historical versions of `data/wikidata_genealogy.json` /
`genealogy_enrichment.json` (1–7 MB each) stay — legitimate data
evolution, and purging them buys little. The rewrite is deliberately
minimal: two dead blobs + one credential.
