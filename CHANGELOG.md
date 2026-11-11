# 0.9.10

- Add a Dark/Light appearance selector beside Method. Switch existing and newly opened main, expanded, object and transfer windows between dark and white-background palettes while preserving data colors and chosen surface colors. Dark remains the startup default.

# 0.9.9

- Save and reopen transfer checkpoints, including while processing. Persist source geometry/provider, target/settings, completed units, review/errors, usage and timestamps without API keys. Resume without reopening the source analysis; skip already completed rewrites and final scores. Save atomically.

# 0.9.8

- Automatically isolate and skip passage-specific analysis, rewrite, review, and scoring failures. Preserve originals or accepted earlier revisions, record stage/errors in transfer reports, and continue later passages. Provider/transport failures and cancellation still stop the run.

# 0.9.7

- Move Emotional shape transfer progress to plain, right-aligned text in the upper-right header, with a fixed height to avoid layout shifts.

# 0.9.6

- Allow rewritten passages to contain additional sentences or paragraph breaks. Keep source-span IDs and score each complete replacement under its original ID, rather than aborting on changed segmentation.

# 0.9.5

- Default shape transfer to Flexible transformation: permit semantic mutation and select the closest reasonable scored revision among attempts. Report meaning changes without vetoing them. Retain the strict Preserve meaning option and export the selected policy and selection notes.

# 0.9.4

- Display header progress as plain text beside Method, removing the red box, border, and visible scrollbar.

# 0.9.3

- Accept whole long documents for emotional shape transfer, with automatic bounded passage processing and no fixed document/unit cap. Preserve original separators in revised-text exports and report passage spans. Coalesce progress redraws for long targets.

# 0.9.2

- Move live progress and status messages into a red box in the header, immediately left of Method. Keep its height fixed and allow scrolling for longer messages.

# 0.9.1

- Give each analysis a stable unique session name, ID, and creation timestamp; show the name in the window title. Save with a separate timestamp and distinct suggested filename. Restore existing identities and support older sessions.

# 0.9.0 — emotional shape transfer

- Add a separate target-rewriting module guided by the source emotional trajectory.
- Align texts by normalized unit position; expose transfer strength and bounded attempts.
- Review meaning, reject numeric changes and retain candidates only when measured fit improves.
- Compare requested/original/revised geometry; export revised text and an auditable transfer report.
- Preserve source analysis and support stopping/resuming within the transfer window.
- Live-model semantic fidelity and transfer quality have not yet been evaluated.

# 0.8.0 — optional sentence-level analysis

- Add Sentence-level analysis (granular), off by default.
- Score individual sentences with neighboring-sentence context and preserve granularity in sessions/CSV/object exports.
- Apply sentence ordering to playback, idiom scans and evolving objects.
- Keep paragraph mode and older sessions supported.

# 0.7.6 — session buttons beside source opening

- Move Open session and Save session to the right of Open .txt at the top.

# 0.7.5 — bounded evolution exports

- Default to compact complete evolution data without recomputing geometry.
- Offer optional meshes at up to 60 sampled frames with point/triangle budgets.
- Stream evolution JSON, cancel cooperatively, and atomically replace finished exports.
- Pause animation during export; omit unevaluated hypervolume rather than imply it was computed.

# 0.7.4 — stable animation footer

- Reserve fixed space for snapshot/status messages so animation does not resize the plot.
- Add a draggable details panel and Expand details control.
- Retain the previous snapshot message while the next frame builds and preserve description scroll position.

# 0.7.3 — expandable paragraph panel

- Add a draggable divider and Expand text control beneath the 2× plot.
- Show the complete selected paragraph in a scrollable, selectable text panel.
- Preserve text scroll position when rotating or zooming the plot.

# 0.7.2 — labeled object axes

- Show X/Y/Z axes, ticks and coordinate labels in the solid/evolving view.
- Match labels to emotional coordinates or PCA; retain fixed bounds across frames.
- Add an Axes visibility toggle and label normalized paragraph time explicitly.

# 0.7.1 — curved surfaces and color

- Add three Loop subdivision refinement levels for solid and evolving objects.
- Add a single user-selected surface color, preserved in JSON/TXT and OBJ/MTL exports.
- Recalculate mesh metrics and document smoothing and control geometry.

# 0.7.0 — solid and evolving objects

- Add an independent object workspace with convex hulls, spatial-neighbor envelopes and text-order tubes.
- Add cumulative and moving-window evolution with paragraph order as the fourth dimension.
- Export OBJ, mathematical TXT, mesh JSON and complete spacetime-slice JSON.
- Preserve the main scatter display and analysis behavior.
- Handle degenerate coordinates explicitly; add analytic geometry and native export tests.

# 0.6.0 — idioms and dream imagery

- Add a separate resumable idiom pass for OpenAI and VT ARC.
- Ground direct, transformed and possible imagery echoes in dictionaries and exact source quotes.
- Highlight candidates yellow in all plot views, with filtering and explanatory evidence.
- Preserve idiom annotations and source provenance in sessions; support JSON dictionary imports.
- Bundle 30,895 Chinese records and limited English (20) / Arabic (10) starter entries.
- Accuracy on live dream reports has not yet been evaluated.

# Changelog

## v0.5.2 — 2026-11-06

- Gave the desktop icon a transparent exterior so the charcoal tile has rounded edges in Finder and the Dock.
- Preserved the monochrome constellation artwork and application behavior.

## v0.5.1 — 2026-11-06

- Fixed immediate API connection failures in the packaged app by bundling the Python runtime’s required TLS trust-policy file.
- Preserved certificate verification and loaded the macOS certificate bundle directly.
- Distinguished actual timeouts, connection interruptions, and missing runtime files in error messages.
- Added a keyless packaged HTTPS connection check to release verification.

## v0.5 — 2026-11-06

- Added VT ARC API support, separate in-memory provider keys, and selectable ARC models.
- Preserved provider and model in sessions, with legacy OpenAI session compatibility.
- Refreshed the dark monochrome interface, icon, and GitHub logo while retaining colored plot points.
- Made the workspace scrollable with proportional trackpad scrolling and keyboard focus visibility.
- Reduced the source field height and removed the empty plot’s decorative cube.
- Distributed as a Developer ID signed, Apple-notarized macOS app.

## v0.3 — 2026-10-23

- Restored colored plot points: red for negative valence, gray for neutral, and blue for positive.
- Colored the app title blue and its Dreams / Literature / Semantic Inference subtitle red.
- Added red and blue constellation points to the icon and README logo.
- Preserved the grayscale interface, layout, and all existing functionality.

## v0.2 — 2026-10-23

- Changed the interface, plot, highlights, and scrollbars to black, white, and gray.
- Updated the application icon and README logo to match the grayscale palette.
- Preserved the retro layout, analysis, saved sessions, PCA, playback, and expanded plot behavior.

## v0.1 — 2026-10-23

Initial public release of Emotional Atlas.

- GPT-6 Luna paragraph inference with contextual evidence and emotional decomposition.
- Interactive 3D emotional plot with clickable points and synchronized 2× expansion.
- Text-order animation of existing analyses, speed control, scrubbing, and neighbor paths.
- Standardized 2D/3D PCA with component interpretation and export.
- Session saving/restoration, resumable batches, CSV export, and review flags.
- Retro royal-blue interface, white monospace text, square controls, and custom icon.
- Self-contained macOS 15+ Apple Silicon application.

### Known limitations

- The macOS binary is ad-hoc signed and not Apple-notarized; Gatekeeper may require explicit user approval.
- Intel Macs do not have a binary in this release.
- Source text and results are not auto-saved. Save the session before exiting.
- Unknown direction excludes a paragraph from emotional and PCA plots.
- Emotions are interpretive model judgments. PCA uses only the three scored features.
- API authentication, billing, and model access are supplied by each user.
