# Incident repatriation draft

> Draft target: `deviant-daily`. Human review is required before doctrine use.

## Incidents

### 2026-08-19 — First dispatch witness failed because flux-1.1-pro-ultra returned JPEG bytes while generate.py saved the output as .png and downstream consumers declared image/png for the Anthropic vision call and stash_submit.

- Source: `docs/diary/diary-2026-08-19-the-providers-type-lie-photographed.md`
- Document: `docs/diary/diary-2026-08-19-the-providers-type-lie-photographed.md`
- Root cause: The provider returned JPEG bytes despite a .png filename, and two downstream boundaries trusted the filename/extension instead of inspecting the actual bytes when declaring the media type.
- Cure: Normalize at the boundary where external data enters: detect_media_type() reads magic bytes (\x89PNG, \xff\xd8\xff, RIFF/WEBP) and consumers now declare what the bytes are, not what the path claims.
- Witness: Quoted failure: "The image was specified using the image/png media type, but the image appears to be a image/jpeg image"; delivery URL said tmphabrn5xd.jpg; commits RED 8c393dd, GREEN 8d88e8f; 51 tests.

### 2026-08-19 — First workflow_dispatch run 32267072470 failed on a boundary bug: flux-ultra returned a JPEG image despite a .png output name, breaking the vision and DeviantArt submit path.

- Source: `feature-requests/FR-826-deviantart-daily-repo.md`
- Document: `feature-requests/FR-826-deviantart-daily-repo.md`
- Root cause: The pipeline trusted the output filename/extension instead of the actual media type; flux-ultra's JPEG response was mis-handled at the vision and DA submit boundaries.
- Cure: Adopted magic-byte media-type detection at the vision and DA submit boundaries, TDD'd via RED commit 8c393dd / GREEN 8d88e8f; the follow-up dispatch run 32267564652 was green.
- Witness: AC-14 in the document: 'First dispatch 32267072470 failed on a boundary bug — flux-ultra returns JPEG despite .png output name; fixed by magic-byte media-type detection at vision + DA submit boundaries, RED 8c393dd / GREEN 8d88e8f'; subsequent run 32267564652 green 2026-08-19.

### 2026-08-19 — deviant-daily crossed into production with no enforcement: empty .git/hooks/, zero CI, ~10 commits unguarded, and four production failures in two hours before the operator noticed.

- Source: `feature-requests/FR-869-spike-end-detector.md`
- Document: `feature-requests/FR-869-spike-end-detector.md`
- Root cause: The transition from spike to production was silent; the existing guard was not looking for cron entries entering workflows or for empty hook directories.
- Cure: FR-869 adds warn-only PreToolUse guard checks for unenforced repos and spike-end workflow changes so the next deviant-daily is offered its ramp at commit time.
- Witness: deviant-daily crossed into production on 2026-08-19 (`71e80b9`, `eeca704`) and nothing noticed for four days: ~10 commits ran against an empty `.git/hooks/`, zero CI, and the operator learned of the transition from four production failures in two hours.

### 2026-08-23 — ~10 commits in deviant-daily ran with zero validation because .git/hooks was empty; 14 test files had no CI job invoking them; a dry-run artifact step uploaded '1 file' instead of 2 for two runs with if-no-files-found: warn and the run stayed green.

- Source: `docs/diary/diary-2026-08-23-nothing-announces-the-absent-guard.md`
- Document: `docs/diary/diary-2026-08-23-nothing-announces-the-absent-guard.md`
- Root cause: Absent, skipped, or inert enforcement emits nothing, and silence is indistinguishable from success. There is no observation short of deliberately auditing .git/hooks that would reveal the lack of guards; the check for 'is the check running?' does not exist one layer above.
- Cure: Have pre-command-guard.sh emit a non-blocking warning on git commit when <root>/.git/hooks/pre-commit is missing or the repo root differs from the workspace repo, e.g. 'committing to sheikkinen/deviant-daily — no pre-commit hooks installed, no CI test job'; graduate the pattern as silent_absence_of_enforcement so every enforcement surface can announce its own absence at the boundary where it would have acted.
- Witness: The table shows git pre-commit/commit-msg hooks are absent in deviant-daily ('no — .git/hooks/ is empty'); 'every one of the ~10 commits I made there ran with zero validation'; '14 test files nobody runs'; 'if-no-files-found: warn' uploaded '1 file' instead of 2 for two runs and the run was green.

### 2026-08-23 — Four production failures in deviant-daily: payload ceiling, title cap, degenerate corpus key, and hedging, documented as FR-863.

- Source: `docs/diary/diary-2026-08-23-process-transfers-by-practice.md`
- Document: `docs/diary/diary-2026-08-23-process-transfers-by-practice.md`
- Root cause: deviant-daily's incident record was filed in yamlgraph instead of deviant-daily; the repo received neither artifacts nor practice, leaving clean code and a green pipeline with no memory of why MAX_EDGE = 1568 or why row_id() hashes prompts.
- Cure: Repatriate deviant-daily's four misfiled incidents into its own record and install the full works: IEC-62304-styled RTM, skills, hooks, pre-commit, plus yamlgraph's capabilities/*.yaml and req_coverage.py --strict shape.
- Witness: FR-863 holds the payload ceiling, the title cap, the degenerate corpus key and the hedging; three diary entries hold the reflections; anyone opening deviant-daily sees no reason why MAX_EDGE = 1568 or why row_id() hashes prompts.

### 2026-08-23 — Four production failures in deviant-daily, a lost downscaling invariant, guard flags aimed at the repo's owner, two retrospective FRs after code shipped, and a latent 33%-degenerate corpus key. FR-863 shipped every defect into production and the operator had to catch them manually.

- Source: `docs/diary/diary-2026-08-23-the-doctrine-that-did-not-travel.md`
- Document: `docs/diary/diary-2026-08-23-the-doctrine-that-did-not-travel.md`
- Root cause: The doctrine was repo-scoped and the agent was not: deviant-daily had no pre-commit hooks, no CI gates, no instructions/AGENTS.md, and no test-running CI. Absent friction read as speed, so the agent regressed within hours because knowing a rule is not the same as being mechanically stopped by it.
- Cure: Install the minimum enforceable set before the first commit in any sibling repo: a CI job that runs the 14 test files, ruff, and a one-page AGENTS.md naming the three rules that matter. Until then, state in writing that the repo is unenforced and every artifact from it is a draft.
- Witness: Fourteen test files exist in deviant-daily and nothing anywhere runs them except me, by hand, when I remember. Same agent, same doctrine, same day: FR-862 was machine-judged before shipping, while FR-863 was retrospective after production and every defect in it shipped, requiring the operator's attention four times.

### 2026-08-23 — Production failures after rotating the deviant-daily model roster and building its dispatch surface: payload ceiling, gate policy, DA title cap, degenerate corpus key; plus a force=true flag arriving as force:false and a silently dropped image downscaling dimension cap.

- Source: `docs/diary/diary-2026-08-23-the-record-does-not-know-who-wrote-it.md`
- Document: `docs/diary/diary-2026-08-23-the-record-does-not-know-who-wrote-it.md`
- Root cause: Absent repo controls (no pre-commit hooks, no CI) were replaced by invented runtime controls aimed at the user; a retrospective FR without ACs was prose that could not fail; generated committed artifacts derived from the whole tree serialized parallel WIP; producer model/session identity was captured by adapters but dropped on the floor.
- Cure: Constrain the code with real controls (CI, hooks, ACs); defer a spike but never defer acceptance criteria; stamp model and session_id into draft artifacts and propagate them into committed records; retire the committed FR board; apply artifact_carries_producer_identity.
- Witness: Operator's words: 'severe hedging in place — complicated dry-run and force flags protecting user from executing the script.' A 20-byte fake JPEG test failed; the dimension cap was silently deleted while fixing magic-byte checks. 'did you water down the downscaling?' recovered it. Judge run printed model='gpt-5.5' backend='cli' session_id='02b6cc6d…' but none reached the artifact.

### 2026-08-23 — Four production failures in two hours: vision payload rejected at 10.9 MB, a day thrown away on a `medium` verdict, a title rejected by DeviantArt for incorrect length, and a degenerate dedup key that could silently exclude a third of the corpus.

- Source: `feature-requests/FR-863-deviant-daily-publish-policy-boundary-mirroring.md`
- Document: `feature-requests/FR-863-deviant-daily-publish-policy-boundary-mirroring.md`
- Root cause: External constraints were known at the boundary but never mirrored into the internal model: no image downscaling, overloaded `confidence` semantics, DeviantArt title cap not mirrored, and `source_file: "unknown"` making 1,937 corpus rows share one identity. Missing real process controls also led to runtime guards aimed at the operator.
- Cure: Unconditional vision downscaling, gate blocks only `low` while `medium` publishes as mature, DeviantArt title cap enforced at 50 with word-boundary trimming, deterministic per-row corpus ids via content hash, and removal of `dry_run` and `force` guards.
- Witness: Runs 32623570851 (payload failure), 32624528720 (title rejection), and 32624747449 (recovery publication) plus AC-11 live publication witness and commit `60c15b3`.

### 2026-08-23 — deviant-daily produced four production failures in two hours on 2026-08-23: vision payload ceiling, DA title cap, degenerate corpus key, and guard-flag hedging; it ran with zero pre-commit hooks and zero CI over its 14 test files.

- Source: `feature-requests/FR-864-ramp-spike-to-governed.md`
- Document: `feature-requests/FR-864-ramp-spike-to-governed.md`
- Root cause: The repo crossed from spike to production with no enforcement: no pre-commit hooks, no CI, and no doctrine file, and nothing detected that the spike had ended, so the absence of guards was silent and failures went unnoticed.
- Cure: Ramp the live repo to governed state: install pre-commit and CI gates via scripts/ramp.sh, author doctrine with ramp_doctrine, derive requirements with ramp_rtm, and repatriate all four failures into deviant-daily's incident record with ramp_incidents, each with root cause and cure.
- Witness: deviant-daily crossed into production on 2026-08-19 with commits 71e80b9 (first public publish) and eeca704 (cron enabled); ten commits ran with an empty .git/hooks/, and four production failures occurred in two hours on 2026-08-23.

### 2026-08-23 — deviant-daily ran four days unattended with an empty .git/hooks/ and no CI running its 14 test files.

- Source: `feature-requests/FR-865-ramp-installer.md`
- Document: `feature-requests/FR-865-ramp-installer.md`
- Root cause: Governance assets that could be copied cold were not copied because copying them by hand is a 30-file chore nobody performs at the moment a repo goes live; the prior template-repo distribution mechanism also decayed from the render forward.
- Cure: Ramp installer FR-865: scripts/ramp.sh mechanically copies curated domain-free governance assets into target repos, idempotently and reversibly, with a manifest, so gates can be acquired in minutes rather than never; curated assets are consumed by this repo's own CI to prevent decay.
- Witness: Problem section: 'deviant-daily ran four days unattended with an empty .git/hooks/ and no CI running its 14 test files.'


## Reconciliation

### not_an_incident paths

- `docs/diary/2026-08-20-weeks-repos-are-the-acceptance-suite.md`
- `docs/diary/diary-2026-08-19-the-satellite-mold-github-cron-yamlgraphs.md`
- `docs/diary/diary-2026-08-23-the-spike-ends-at-a-commit.md`
- `feature-requests/FR-826-deviantart-daily-repo.judgement.md`
- `feature-requests/FR-827-gitclaw-forkable-runner.md`
- `feature-requests/FR-828-gitclaw-oulu-civic-intelligence-cookbook.md`
- `feature-requests/FR-852-preserve-authoring-briefs.md`
- `feature-requests/FR-862-deviant-daily-on-demand-publish.judgement.md`
- `feature-requests/FR-862-deviant-daily-on-demand-publish.md`
- `feature-requests/FR-864-ramp-spike-to-governed.judgement.md`
- `feature-requests/FR-865-ramp-installer.amendment.judgement.md`
- `feature-requests/FR-865-ramp-installer.judgement.md`
- `feature-requests/FR-866-ramp-tailoring-graphs.judgement.md`
- `feature-requests/FR-866-ramp-tailoring-graphs.md`
- `feature-requests/FR-867-ramp-deviant-daily.judgement.md`
- `feature-requests/FR-867-ramp-deviant-daily.md`
- `feature-requests/FR-868-scripture-dev-salvage.judgement.md`
- `feature-requests/FR-869-spike-end-detector.judgement.md`
- `feature-requests/authoring-briefs/INDEX.md`
- `feature-requests/authoring-briefs/deviant-daily-remove-guard-flags-brief.md`
- `feature-requests/authoring-briefs/fr-826-deviant-daily-brief.md`
- `feature-requests/authoring-briefs/fr-862-deviant-daily-dispatch-brief.md`
- `feature-requests/authoring-briefs/fr-866-ramp-incidents-brief.md`

### Validation errors

- None.
