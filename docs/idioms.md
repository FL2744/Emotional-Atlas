# Idioms and dream imagery

Choose **Scan idioms / Resume** after adding text or opening a session. It uses the selected OpenAI or VT ARC key and model, independently of emotional scoring. Each paragraph uses up to two API requests. The paragraph range selector also applies. Stop retains completed paragraphs; Resume skips them. Rescan all idioms reprocesses the selected range, replacing each paragraph's previous matches only after a successful response.

Candidates appear yellow in the plot and have a **Possible idiom** label in the table. Use the **Idiom candidates** filter and select a paragraph for the original phrase, language, meaning, exact evidence, explanation, alternative reading, and dictionary provenance. Paragraphs without emotional coordinates remain accessible in the table; idiom scanning does not invent plot coordinates. Matches survive Save/Open session, including dictionary entry snapshots and per-paragraph provider/model metadata. Older sessions remain supported.

## What a match means

The detector distinguishes direct figurative use, transformed expressions, and possible imagery echoes. The imagery pass considers English, Arabic, and Chinese expressions even when the report is in a different language. Taking someone's goat may echo *get your goat*. A goat merely grazing is insufficient evidence. These are hypotheses for readers to consider, not conclusions about a dreamer's psychology or intentions. The app does not produce calibrated confidence probabilities.

The first API call proposes canonical expressions. Local matching retrieves only entries present in the dictionaries; direct phrase matches and a small set of imagery examples are also included. The second API call judges those candidates. Local validation requires a known dictionary ID and a contiguous quote from the paragraph. This prevents invented citations, but does not guarantee a good interpretation. Model recall, spelling variants, translation, dialect and dictionary coverage can cause omissions or false positives. No live-model accuracy study has been performed.

## Bundled coverage and provenance

- Chinese: 30,895 nonempty records from [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua), revision `fe6d6c2e8baa82187f4c96bbe042e43f96c05666`, `data/idiom.json`. Repository declares MIT; license preserved in `licenses/chinese-xinhua.txt`. Transformation retains word and explanation, adds IDs, language and attribution, and flags ten expressions as imagery retrieval seeds. Definitions are in Chinese; the model explains the connection in English. Traditional/simplified equivalence is not automatically normalized.
- English: 20 traditional expressions with original short English glosses in `datasets/starter.json`.
- Arabic: 10 traditional expressions/proverbs with original short English glosses in the same file. This is a small starter collection, not comprehensive dialect coverage. The starter glosses and selections require further native-speaker review. They are project-authored data under the repository MIT license, not copied dictionary definitions.

The [ChengyuBench](https://github.com/sofyc/ChengyuBench) project is a potential Chinese evaluation resource for connotation, contextual appropriateness and cloze tasks. It is not bundled and does not establish dream-imagery detection accuracy. The inspected [IdiomX generated inventory](https://github.com/aymanshar/idiomx-dataset/tree/main/data/generated) includes synthetic expressions, so it was not used as an inventory of established idioms. Its dataset terms are distinct from its software license.

## Importing dictionaries

Use **Import idiom dictionary** with a UTF-8 JSON array. Every entry must have nonempty string fields `id`, `language`, `phrase`, `meaning`, `source`, and `license`. IDs must be unique across bundled and imported dictionaries. Other languages are accepted, although model discovery currently prioritizes English, Arabic and Chinese. Example:

```json
[{"id":"custom-en-001","language":"en","phrase":"cross that bridge when we come to it","meaning":"Address a problem when it arises.","source":"Your dictionary citation","license":"Your redistribution terms"}]
```

Import is local to the running app. Reimport after restarting to scan more text; saved matches retain their dictionary entries. Use **Rescan all idioms** to reconsider already matched paragraphs after importing. Imported entries are supplied to the selected provider when retrieved as candidates. Do not set the internal `imagery` flag on large imported dictionaries: flagged entries are included in every verification request.

## Testing and evaluation

`python -m unittest discover` tests dictionary grounding, multilingual retrieval, fabricated evidence rejection, session restoration, provider request formats and cancellation. The native smoke test checks yellow markers, expanded plot synchronization, filtering and evidence rendering. Mocked responses validate plumbing only, not model interpretation. A future accuracy evaluation needs native-speaker annotation of direct, transformed, imagery and literal-negative examples in each language, including cross-language dreams and counterexamples with similar objects but different actions.
