# Emotional shape transfer

## Editing policy

**Flexible transformation** is the default. It permits changes to imagery, perspective, emotional reactions, details and local events while asking the model to maintain a recognizable connection to the target. A separate review checks coherence and relevance, and reports meaning changes. The closest scored reasonable revision among the generated attempts is selected, even if the original scored closer. This deliberately favors transformation; before/after geometry remains visible and improvement is not guaranteed. Choose two attempts to compare two candidates per unit. Unscorable or unreasonable candidates are not selected.

**Preserve meaning** retains the original strict review and numeric checks as vetoes, and requires improvement over the original. The strict workflow below applies to that option. Flexible-mode semantic and numeric changes are recorded but do not veto an otherwise reasonable candidate. Reports include editing policy and selection notes; final assembled-context scores can differ from selection-time scores.

## Workflow

Analyze or open the **source** text in the main Atlas window. Click **Emotional shape transfer…** beneath the CSV export button, paste or open a **target** text, choose paragraph/sentence units, strength, and one or two attempts, then click **Transfer / Resume**. At least two source units need known valence, intensity and direction. There is no need to export source geometry first.

The transfer window takes a source snapshot and keeps the main analysis unchanged. It uses the source analysis's provider/model, with that provider's memory-only key from the main window. The target text and neighboring context are sent to that provider. Source prose is not sent to the rewriting model: only the desired numerical emotional coordinates are supplied. Original and revised target texts are shown side by side. The comparison tab shows requested, original and revised geometries and a per-unit review log; click a plotted point to inspect its attempts.

## What is transferred

The in-memory plot coordinates are `p = (valence, direction, 2*intensity - 1)`. These define an emotional trajectory through the source text. Unit position is normalized as `t_i = (i-1)/(N-1)`. Known source points form a piecewise-linear path `p(t)`. Missing source coordinates are skipped and gaps interpolated; values outside the known range clamp to the nearest endpoint. This can be misleading for sparsely analyzed sources, so complete the source analysis where possible.

For M target units, sample the source at `t_j = (j-1)/(M-1)`; a single target unit samples the midpoint. At strength `s`, the requested coordinate is `q_j = (1-s)*b_j + s*p(t_j)`, where `b_j` is the original target coordinate. If the original target has no supported direction, a complete baseline point is unavailable and the source point is used directly. The displayed surface's tessellation, PCA projection, chosen color and Loop smoothing are not used as emotional constraints. The underlying original emotional coordinates are used instead.

Different unit counts resample the trajectory and do not guarantee the same hull, surface volume or topology. A one-unit target cannot reproduce an entire evolving shape. Transfer changes emotional expression through wording and emphasis; the source's events, objects and phrases are not copied.

## How candidates are checked in Preserve meaning mode

1. Score the original target with Atlas's existing emotional analysis and evidence validation.
2. Ask the LLM to revise a batch toward the requested coordinates while preserving target language, facts, entities, events, agency, chronology, negation, uncertainty and viewpoint.
3. Make a separate model call to review semantic fidelity without showing the desired coordinates. Concrete numeric tokens are also compared locally; changed numeric content rejects a candidate.
4. Score the candidate using the original Atlas scoring prompt, without the desired scores in that prompt.
5. Retain a changed candidate only when the meaning review passes without concerns, the direction is supported, and its distance is lower than the current best. Otherwise keep the original or a previously accepted candidate. A second attempt receives the first attempt's review and scores.
6. Score the assembled revised text again in its final neighboring context. These final scores may differ from batch scores, and can reveal a worse fit despite provisional acceptance.

Distance is Euclidean coordinate error divided by `2*sqrt(3)`, the cube's diagonal. It is not a calibrated quality score. Mean errors display their scored-unit counts; units lacking supported direction cannot contribute. Source and target scoring use the same provider/model but model variability still affects comparability. A meaning checker can miss changes or reject good revisions. When explicit target emotions conflict with the source, semantic fidelity takes precedence and the original may remain unchanged. Human review is necessary; this is not a guarantee of semantic equivalence or of an exact geometric match.

## Limits, stopping and exports

There is no fixed document-length or unit-count limit. Oversized target units are automatically divided into passages of at most 3,000 characters, preferring sentence boundaries and then whitespace. Requests contain up to 6,000 characters of target text. The full document remains one transfer; exports preserve original separators and paragraph structure, including for unchanged passages. Geometry is aligned across all processing passages in document order. Reports include original-text spans for those passages. One attempt normally uses baseline scoring, rewriting, meaning review, candidate scoring and final scoring: roughly five model calls per batch of up to six units, before bounded API/evidence retries. Two attempts add a rewrite/review/score cycle. Actual batches can be smaller because of character budgets. Review your API usage before processing a long target. Usage counters include successful responses returned to the app; interrupted or invalid responses may incur additional usage.

Stop takes effect after the current API call (up to 150 seconds). Completed units remain available, and Resume continues in the same window. Closing the window discards unsaved results after confirmation. Use Save transfer to preserve a resumable checkpoint across app sessions. Audit reports are separate exports and are not checkpoint files.

- **Export revised .txt** writes the current assembled target. Pending units in an interrupted run remain original.
- **Export transfer report .json** writes format `emotional-atlas-transfer-v1`, original/revised target text, source profile, source/provider metadata, alignment settings, per-attempt drafts and meaning reviews, baseline/candidate/final emotional scores, distances, observed usage and completion state. API keys are excluded. Reports include the mathematical alignment formula and limitations.

Transfer reports preserve draft attempts, including rejected ones; the text export contains only selected revisions and retained originals. Exporting or rewriting never modifies the source file or replaces the main analysis.

## Verification and implementation

Unit tests cover trajectory interpolation, clamping/single-unit alignment, normalized distances, missing directions, input limits, semantic rejection, attempt bounds, cancellation and resume behavior. Native tests exercise the window and exports with an explicitly synthetic response stream. They do not establish live-model rewriting quality. A live evaluation should compare factual fidelity and measured emotional fit on representative English, Arabic and Chinese text, with independent human review.

OpenAI calls use strict structured JSON outputs and store=false; VT ARC uses its existing chat/JSON-mode adapter with the same local validation. Reference: [OpenAI structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). This validates response structure, not factual or semantic correctness.

### Rewritten boundaries

Target units are stable spans of the original target. Replacements can contain multiple sentences or paragraph breaks within a span, in both editing policies. The entire replacement is scored as one unit under the original ID, preserving trajectory correspondence. Response IDs must still be complete, unique and ordered. Reanalyzing the exported text with sentence segmentation may produce a different number of points.

### Failure handling

Content-specific failures in a batch are isolated into individual passages. A passage that still fails is flagged and processing continues automatically. Its original text is retained unless an earlier attempt was already accepted. Final scoring failures are flagged without discarding a revision; its earlier score remains provisional. Reports contain `processing_errors` with stage/message per unit and a top-level `flagged_units` list. Completed transfers may contain flagged units. Provider/account/transport errors and explicit cancellation still stop the run. Batch isolation can add API calls. Usage counters remain a lower bound when responses fail before usage is returned.

### Save and resume transfers (v0.9.9)

Use **Save transfer** to create a timestamped checkpoint, including while requests are running. It saves the source analysis snapshot and provider/model, original target, processing settings, completed units, review/errors, usage and completion status. API keys are excluded. **Open saved transfer…** in the main window, or **Open transfer** in a transfer window, restores it in a separate window without needing an active source analysis. Enter the saved provider's key in the main window and press **Transfer / Resume**. Completed rewrites and final scores are skipped; flagged units remain flagged.

A checkpoint includes work completed when Save was pressed. In-flight requests and unfinished batches are not captured and may incur usage again on resume. It is a manual checkpoint, not continuous autosave. Write failures leave an existing checkpoint intact. Revised TXT and audit-report JSON exports remain separate from the resumable `emotional-atlas-transfer-session-v1` checkpoint format. Reopening a completed checkpoint allows inspection/export without API calls.
