# Blog Editorial Guidelines

This guide defines the editorial standard for articles in this repository. The blog is a public personal publication: it should turn genuine experience, curiosity, research, and independent thinking into useful writing that readers can understand and trust.

**Editorial principle: Personal perspective. Public value. Technical integrity.**

## Editorial purpose

- Start from real observations, questions, work, or ideas, then identify what readers can learn from them.
- Publish when the material offers understanding, a useful method, a reliable reference, considered analysis, or an authentic perspective.
- Treat existing articles as context for experience, terminology, and related work—not as limits on future subjects, formats, or depth.
- Do not turn every note into a standalone article. Update an existing article or leave material unpublished when that is more useful.

## Voice and structure

- Write naturally, clearly, and thoughtfully. Keep the author's perspective without self-promotion, exaggerated claims, or unnecessary formality.
- Use first person for genuine experience, decisions, and opinions; do not insert it mechanically.
- Raw notes, dated logs, commit messages, and task lists are source material, not finished prose. Find the underlying question, decision, problem, or insight and rebuild the narrative for readers.
- Avoid change-log openings, unnecessary date-first narration, repetitive transitions, inflated summaries, and generic AI-sounding phrasing.
- Do not force a universal article template, fixed length, or predetermined section sequence. Let the subject and reader's needs determine the structure.
- Explain technical terms, assumptions, trade-offs, limitations, and reproducible steps when they matter. Do not add them mechanically.

## Editorial decisions

- Choose the title after understanding the finished article. Make it accurate, specific, natural, and proportionate to the content.
- Use the actual experience or event date when that is what the article records. Do not replace it with the drafting or publication date; preserve intentional historical dates.
- Inspect existing tags before adding any. Reuse a tag only when its meaning fits; avoid near-synonyms, incidental labels, and one-off categories. Create a new tag when it describes a meaningful subject that readers may reuse to discover related work.
- Add links to other articles only when they genuinely help readers. Read the linked source before making claims about its content.
- Make routine decisions autonomously. Ask the author only when missing information materially affects factual accuracy, personal intent, privacy, licensing, or the conclusion.

## Research and integrity

- Match research depth to the article's claims and reader needs. Technical instructions, current product behavior, policies, versions, and comparisons need appropriate verification; personal reflections do not need citations for their own experience.
- Prefer official documentation, specifications, source code, release notes, and primary records. Use community discussions as useful leads, and attribute reports rather than presenting them as universal facts.
- Keep personal experience, verified facts, interpretation, opinion, and uncertainty distinct.
- Never invent experiences, dates, measurements, tests, quotations, sources, or technical behavior. Qualify uncertain explanations and preserve historical context when current behavior has changed.
- Do not add citations merely for appearance. Cite sources when they support claims or help readers verify and reproduce the work.

## Working with the archive

For blog tasks, read this guide and the generated `BLOG_INDEX.json` first. Use the index to find likely related subjects and tags, then inspect the relevant Markdown articles before drafting or changing their content. The index is a tracked discovery aid generated from article metadata, not an alternative editorial source; Markdown files under `posts/` remain authoritative. After article metadata changes, regenerate the index with `python scripts/blog_index.py --write` and verify with `python scripts/blog_index.py --check`.

For a complete article task:

1. Understand the supplied material and the author's actual intent.
2. Identify reader value, suitable format, and overlap with existing articles.
3. Research and verify claims at a depth appropriate to the subject.
4. Write or revise the article, choosing its title, date, and tags.
5. Review the complete result for usefulness, voice, accuracy, privacy, licensing, and long-term readability.
6. Regenerate and check the index when metadata changes, then run the relevant repository tests.

Do not change the author's substantive experience or opinion, publish sensitive information, or delete historically significant content without confirmation. Protect credentials, account identifiers, private contact details, and identifying information in screenshots, logs, and examples. Respect repository and third-party licenses.

## Review and delivery

An article should stand on its own outside the author's current website layout, temporary interface, or private workflow. Remove details that will confuse readers without removing the concrete context needed to understand or reproduce the experience.

Keep article changes focused. Use a PR for substantial editorial batches or changes that benefit from review and a durable record; use a normal commit for routine maintenance, following the repository's engineering conventions. When a PR is appropriate, briefly describe the purpose, material editorial changes, important sources or verification, metadata decisions, and checks performed. Do not include hidden reasoning or lengthy process narration. Never claim checks passed unless they actually ran, and do not merge or publish without the author's authorization.
