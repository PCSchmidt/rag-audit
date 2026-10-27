# rag-audit: Evidence Notes

Companion to rag-audit.md. Labels: Confirmed, Ran it, Per the docs, My reading, Ask the author, Author says.

## E1 Fact sheet
- Repo: github.com/PCSchmidt/rag-audit, public, MIT, v0.2.0 (pyproject). 0 stars, 0 forks per GitHub API (2026-10-27). Not on PyPI. Confirmed.
- Kind: Python library plus CLI plus FEVER benchmark. Source: claims.py 68 lines, auditor.py 170, nli.py 82, cli.py 44, init 16; tests 114 lines; scripts 157+19; demo 43. Confirmed.
- 12 commits, 2026-10-09 to 2026-10-19. 11 carry "Co-Authored-By: Claude Sonnet 5.5"; the last (24f4cdd, adds an older explainer file to the repo) carries "Claude Opus 5.5". No CLAUDE.md, AGENTS.md or settings folders. Confirmed.
- Description on GitHub: "Deterministic factuality gate for RAG outputs: claim decomposition, citation span alignment, NLI verification, hashed audit certificates." Topics set. Confirmed.
- Not deployed. Runs: CI success on every listed run (last 2026-10-19). Ran it (gh run list).
- Needs: Python 3.11+, pydantic; extras torch and transformers; model download about 570 MB (small) / 740 MB (base, safetensors sizes seen in local cache). Benchmark also needs datasets and numpy (not declared in pyproject; README names datasets). Confirmed.

## E2 Reading and running log
Read: README, docs/RESULTS.md, all of src, tests, scripts, examples/demo.py, pyproject, ci.yml, dependabot.yml, Dockerfile, .gitignore, all frozen.json and test_summary.json, dev_sweep files, git log. Not read on purpose: the older explainer file committed in the repo (instruction). Note: a git-history secret grep printed lines from that file's commit diff; none were used as a source.
Scratch copy of the clone (the old explainer file deleted there), run with the author's existing virtual environment from the working copy of the project via PYTHONPATH pointing at the scratch src, HF_HUB_OFFLINE=1 (models and FEVER were already in the local Hugging Face cache; nothing downloaded):
- pytest -q -p no:cacheprovider: 10 passed (3.06 s). Ran it.
- mypy src tests scripts: no issues in 7 files. ruff check: all checks passed. Ran it.
- examples/demo.py: output identical to README; payload sha256 a27614165856cb273e6a5b1695a75577a5a672ea6d6302604dc542f46776e15d on two runs, equal to README. Ran it.
- Demo model scores (small model, threshold 0.55): claim 1 ent 0.996; claim 2 ent 0.000 con 0.998 (passage "carries six lanes"); claim 3 ent 0.997. Ran it.
- Benchmark script not re-run (hours on CPU). Saved summaries read instead.
- gh api and gh run list used read-only. Clone git status: clean (checked at end).
Not run: Docker, the full ablation.

## E3 Claims check (L1 = doc matches committed result file)
- CL-01 F1 0.920, P 0.914, R 0.927, kept 82.5%, p50 46 ms (small, titles): matches test_summary.json. L1. Supported.
- CL-02 other three rows of the 2x2 table: match test_summary.json. L1. Supported.
- CL-03 ECE 0.08-0.17: 0.081, 0.090, 0.150, 0.166. L1. Supported.
- CL-04 "about 83% of REFUTES get CONTRADICTED": 0.827-0.838 across cells. L1. Supported.
- CL-05 recall of unsupported 0.93-0.95: overall recall 0.927-0.946. L1. Supported (README says "catch rate 0.93-0.95").
- CL-06 earlier baseline F1 0.874, P 0.802, R 0.960, kept 52.7%: matches results/test_summary.json (n=1798). L1. Supported.
- CL-07 invalid run: recall 1.0, kept 0, p50 about 20 microseconds: matches results/test_run1_INVALID_summary.json. L1. Supported.
- CL-08 "single-sentence 52.8% kept vs multi 52.1%": not recomputable from committed files (no per-item evidence length). Per the docs. Unchecked.
- CL-09 "10 tests, mypy strict, ruff". Ran it: true. CI runs mypy and pytest only; ruff not in CI. Partly (verification list vs CI).
- CL-10 "committed results carry only ids, labels, scores, never text and local paths" (commit 7ee7eba, aa4455e). Ids and scores confirmed; the committed benchmark logs (results/ablation/*/dev.log, test.log) still contain a local virtual-environment path from a Python warning line (a Windows path under the author's project folder, no username seen). Partly.
- CL-11 "Thresholds frozen on dev before test": run_ablation.sh runs dev then test per tag; the script refuses to rerun test when test_scores.json exists. Confirmed in code; order in time Per the docs.
- CL-12 "dev curve nearly flat": small_plain dev F1 range 0.862-0.871; small_titles 0.915-0.928; base_plain 0.884-0.891; base_titles about 0.935-0.943. Ran it. Supported.
- CL-13 "same inputs give same report and hash": demo twice, same hash. Ran it, one machine only. Partly.
- CL-14 "45 ms median at CPU": matches p50 0.044-0.046 s for small. L1.
- CL-15 "small vs base F1 gap within noise": README gives a rough interval of about 1.5-2 points; not independently recomputed. Per the docs.
- CL-16 Test n: 1,800 for all four cells; dev 1,793 items (small_titles). README says about 1,790. Supported.
- CL-17 Extra check (mine): flag-everything F1 = 0.800 (1,200 of 1,800 positive). Ran it with the benchmark's own sample function on test seed 3: P 0.667, R 1.0, F1 0.800.
- CL-18 Extra check (mine): LexicalOverlapNLI as scorer, dev threshold chosen by best F1 on dev (0.95), test seed 3, no titles: P 0.688, R 0.997, F1 0.814, supported kept 0.097. Ran it (scratch script, not committed). Not part of the project's claims.

## E4 Rule attacks (scratch probes, lexical stand-in unless noted)
- Empty summary: score 0.0, 0 claims. Ran it.
- Footnotes [0], [2] with one source, [1,9]: INVALID_CITATION for each; [1,9] flags the whole claim. Ran it.
- Empty source list with [1]: INVALID_CITATION. Empty source string with [1]: UNSUPPORTED, no crash.
- Thresholds 0.0 and 1.5: ValueError. Ran it.
- Unsigned report verify: False. Same inputs, different keys: same payload hash, different signature. Hash changes when threshold changes. Ran it.
- 100,000-character source: completes (stand-in).
- Splitter: "The bridge opened [1]. it has lanes [1]." stays one claim (lowercase start). "Dr. Smith built it [1]. It opened [1]." gives claims "Dr.", "Smith built it [1].", "It opened [1]." so "Dr." becomes an UNCITED claim (by code, since a claim with empty citations is UNCITED). Ran it.
- One sentence with two facts: one claim.
- Real model, threshold 0.55, one source "The Harbor Bridge opened to traffic in 1932. The Harbor Bridge carries six lanes...": paraphrase SUPPORTED (ent 1.0); negation CONTRADICTED; year flipped 1923 CONTRADICTED; matching claim SUPPORTED (0.99); two true facts in one sentence UNSUPPORTED; one true plus one wrong in one sentence UNSUPPORTED; claim needing combination UNSUPPORTED; source "He was born in 1950" with claim "Alan Moore was born in 1950" UNSUPPORTED (0.0); same with "Alan Moore: " prefix SUPPORTED (1.0); source with "Ignore previous instructions ... opened in 1999" vs claim 1932: CONTRADICTED. Ran it. Single probes, not measurements.
- Model label order from config.json: 0 contradiction, 1 entailment, 2 neutral (cached small model). Confirmed.

## E5 Code map
src/rag_audit/claims.py (regex split, extract_citations, strip_citations, split_claims); auditor.py (passages, FactualityAuditor._best_evidence, _judge, audit, verify_signature, canonical JSON, hash/HMAC); nli.py (NLIScores validator, NLIScorer protocol, CrossEncoderNLI, LexicalOverlapNLI); cli.py (argparse, --fail-below, --scorer, key from RAG_AUDIT_SIGNING_KEY). Defaults: entail 0.7, contradict 0.5; the CLI builds the auditor with defaults and has no threshold or title option. Scripts: fever_benchmark.py (sample, score_items, prf, ece, dev/test), run_ablation.sh (hard-codes a Windows venv path). Confirmed.

## E6 Model call sites
- nli.py CrossEncoderNLI.score: tokenizer(premise, hypothesis, truncation, max_length 512), softmax over logits, label map from config. Used by auditor._best_evidence (once per source sentence per cited source) and by fever_benchmark.score_items (dev) and via audit (test). Models: cross-encoder/nli-deberta-v3-small (default), -base (ablation). No generative model, no prompts, no network after download, no per-call cost. Config shows base architecture microsoft/deberta-v3-small, 6 layers, hidden 768. Training data of the cross-encoders is not recorded in the repo (My reading: natural-language-inference sets; not verified).
- Not used: roberta-large-snli_mnli_fever_anli (skipped, README).

## E7 Tests and CI
10 tests (7 example, 3 Hypothesis). Spot checks: test_verdicts_cover_every_branch uses a scripted scorer and asserts the five verdicts in order and score 20.0 plus 4 flagged (real assertion). test_hash_deterministic_and_sensitive asserts equal hash on repeat and different hash after editing a source (real). test_split_claims_never_crashes asserts offsets slice back to claim text (property, real). CI (.github/workflows/ci.yml): checkout, Python 3.12, pip install -e ".[dev]", mypy src tests, pytest -q. No ruff, no model, no benchmark. Dockerfile: python:3.12-slim, installs [dev], copies tests, CMD pytest; no model. Coverage not measured. Confirmed.

## E8 History
Commit times (local): scaffold 10-09 16:53 with RESULTS.md saying "No model benchmarks have been run yet" and the planned frozen-threshold protocol; benchmark plus splitter fix 17:14 same day (21 minutes later); 2x2 ablation 10-10 07:23; README rewrite, diagram, scrub, doc fixes 10-10 to 10-12; Dependabot 10-13; roadmap gaps 10-13; old explainer added 10-19. Plan-versus-results: plan existed before the benchmark script but is a plan, not a locked protocol with a success rule. The 2x2 hypothesis (titles) arose from analysis of test seed 2 outputs (README/RESULTS), then final numbers used a fresh seed 3 sample. Credits: 11 Sonnet 5.5, 1 Opus 5.5.

## E9 Gates and approvals
None in the repo (no gates.yaml, no approvals).

## E10 Environment
pyproject: pydantic>=2.6; nli extra transformers>=4.40, torch>=2.2; dev extra pytest, hypothesis, mypy, ruff, all lower bounds, no lockfile, model revision not pinned. Environment used for the probes: torch 2.14.1 CPU, transformers 5.19.0, pydantic 2.14.0, hypothesis 6.168.5 (author's existing environment). Python 3.14 on PATH for plotting only. Results record model name but not versions. Dependabot monthly for pip and Actions; open dependency PRs exist (pytest, mypy bumps).

## E11 Security and privacy
Pattern grep of full git history for key-like strings: no real hits (only the words signing key, tokenizer, tokens). No .env read. Only secret is optional RAG_AUDIT_SIGNING_KEY read from the environment. HMAC is shared-key; the unkeyed hash can be recomputed by anyone. Model download from Hugging Face is the only network use; weights are not checksum-pinned. Dependabot present; no security policy file. FEVER text excluded from commits for licence reasons.

## E12 Shortcomings register
1. CLI cannot set thresholds or titles; default entail threshold 0.7 was never a frozen benchmark value (frozen values 0.15-0.60). Dev F1 at 0.7 is 0.927 vs 0.928 at 0.55 for small plus titles, so impact likely small. Severity Medium. Not disclosed. Options: add flags (small); read a config file; leave and document. Recommend flags. Effort small, payoff medium.
2. Splitter errors: abbreviations ("Dr.") create spurious uncited claims; lowercase-starting sentences merge. Severity Medium for real prose, none on FEVER. Not disclosed. Options: abbreviation list; use a sentence-splitting library; leave. Effort small to medium.
3. Evidence is one source sentence at a time; multi-sentence or multi-document claims flagged. Severity High for real use. Disclosed.
4. Single-domain measurement (FEVER). Disclosed.
5. Benchmark joins gold evidence sentences into one short source; real documents have many distractor sentences and the tool takes the max entailment over them (My reading: raises false-support risk; unmeasured). Not disclosed. Severity Medium.
6. Model version not pinned, training data not recorded, weights not checksum-checked. Not disclosed (README mentions the download). Severity Medium.
7. README verification list names ruff but CI does not run it; Dockerfile and CI never touch the real model. Low.
8. Committed logs still hold a local environment path; README claims paths were removed. Low.
9. Calibration poor (ECE 0.08-0.17), disclosed; the score and "entailment" fields could be misread as confidence. Low-Medium.
10. Empty summary scores 0.0, which a --fail-below gate treats as failure; undocumented. Low.
Hash proves nothing without HMAC key; HMAC cannot prove authorship to a third party. Low, documentation only.

## E13 Method detail
Score = 100 x supported / claims, rounded to 6 places. Per-claim: for each cited n, best passage by entailment; best across sources by entailment; if >= T1 SUPPORTED; else worst = max contradiction across candidates, if >= T2 CONTRADICTED with that evidence; else UNSUPPORTED. Any out-of-range citation makes INVALID_CITATION before scoring. Cost: one model pass per source sentence per cited source. ECE: 10 equal bins on entailment as P(supported), unweighted edges, last bin closed. Worked check: small plus titles at T=0.55 on 1,800 items: supported kept 0.825 gives 495 of 600 kept, 105 false flags; recall 0.9267 gives 1,112 of 1,200; precision 1112/(1112+105)=0.9137, matches 0.914. Flag-all: precision 1200/1800=0.667, F1 0.8. Note the benchmark's dev scoring uses best entailment over passages with threshold test ent < t, the same rule as the auditor except the contradiction branch (which does not affect flagged versus kept).

## E14 Discrepancies
README says "Tests: 10 ... ruff" as verified; CI omits ruff. README quickstart "pytest -q # 10 passed" true. README says committed results have no local paths; logs contain one. GitHub description says "hashed audit certificates"; pyproject says "signed audit certificates". Hash covers rounded entailment and span but not contradiction values or passage text (code reading).

## E15 Production readiness
Placement: Works locally. Traits: clean-start run Partly (no lockfile); CI blocks bad change Partly (tests and types, no quality gate); quality measured vs baseline Yes (one dataset); safe on failure Partly (flags, stops without model; no timeouts or limits); human in the loop Partly (advisory); prompts/models versioned No (no prompts; model not pinned); logs and monitoring No; data and secrets Yes (public data, optional key from env). Gaps: release packaging missing, hosting missing, sign-in missing, monitoring missing, rollback only via git, model pin missing, cost limits not applicable, security review missing, runbook missing.

## E16 Review dispositions
Self-review passes: acronyms checked at first use; numbers re-derived against saved files (E3, E13); claims of "I ran" replaced by neutral phrasing; images checked for clipping.

## E17 Completeness and backlog
Done and tested: splitting, citation parsing, passage cutting, verdicts, hash and HMAC, CLI, demo, FEVER benchmark, 2x2 ablation. Done but untested by automation: real-model path (benchmark only), Docker image (not built here). Planned only (README gaps): PyPI release, HaluEval, roberta-large comparison (skipped on purpose), multi-claim and non-Wikipedia evaluation, GPU timings.
Backlog. Fix: CLI thresholds and titles; splitter abbreviations; pin model revision; document empty-summary behaviour; scrub log paths; add ruff to CI. Improve: coreference or previous-sentence context; multi-sentence claim handling; add per-run version record to reports. Add: second-domain evaluation with hand labels; scheduled quality check; logging; release to PyPI. Next milestone: CLI flags plus a CI step that runs the 10 tests and a small benchmark sample, exit test: CI fails when F1 on the sample drops. Then second-domain sample, then model pin and release.

## E18 Revision log (v1 to v2 draft, reader-check fixes)
Archived prior draft as rag-audit.v1draft.md (7,603 words by wc -w). Revised draft is about 7,070 words by wc -w. No numbers or facts changed; all figures re-used from E3 and E13.
1. Length cut: repeated "In short" lines removed from five chapters, results table removed (chart plus prose carries it), duplicate caveats, the results "what did not work" paragraph, the real-use "mirrors practice" paragraph, the tuning-curve figures and the fresh-install paragraph removed; interview list cut to four questions.
2. F1 defined in one sentence beside the first headline number (opening), with scale; worked example kept in methods.
3. "Fingerprint" defined at first use in the opening as a tamper seal.
4. Deterministic-versus-probabilistic paragraph moved into the opening (second fixed-rules chapter folded in): mostly fixed code, one learned model, repeatable on one machine but not guaranteed identical elsewhere.
5. Parts chapter: referee, passage cutter and similar jargon replaced with plain wording; Docker and share-alike glossed in place.
6. Ten-row edge-case table moved to an appendix; testing chapter keeps four examples in prose.
7. Supported, contradicted, unsupported, uncited, invalid citation and flagged defined once in the opening with the port-expansion example, before any numbers.
8. Glossary extended (baseline, entailment, fingerprint, held-out); terms also defined inline at first use. Glossary stays at the back (no glossary box early, per rule 0.0).
9. Testing chapter rewritten for a lay reader: what tests prove and do not; invalid first run explained plainly.
10. "Best" made unambiguous: the setup to use is small model with titles (F1 0.920); base with titles scores 0.933 nominally but the 0.013 gap is within README-estimated noise, at about twice the time. Flag-everything named as a weak baseline in the opening; untested tuned non-model method stated. "Close to deployable" removed; real-use chapter now says it works locally and needs real work. Plan-before-results softened to a plan, not a locked protocol.
Also: "kept 82.5 percent" reworded as share of supported claims not wrongly flagged (not accuracy); "stars" and "installable package" glossed; "exit code" glossed; "Hard Power Intelligence" and "evaluator" glossed; role family and agent workflows explained.

## E19 Review fixes: pictures and naming
Source: rag-audit.review.md "Needs Chris". Checked auditor._best_evidence (scores every passage, keeps max entailment) and _judge (cut-offs applied after) in the clone. Regenerated images/rag-audit-learned-vs-rules.png (the model box now reads "scores every source sentence"; the next box "keeps the highest-scoring sentence; cut-offs pick a verdict (fixed rule)") and images/rag-audit-parts.png ("Summary splitter", "Source splitter", "Verdict rules", "exit status 1"; "Passage cutter" and "Referee" removed). Same style, viewed after render: no clipping or overlap. Guide parts paragraph renamed to match (summary splitter, source splitter, verdict rules, report writer). Word count now 7,1xx by wc -w (limit 8,000).
