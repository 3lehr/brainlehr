# Data Card: LongMemEval-V2

## Dataset Summary

LongMemEval-V2 evaluates memory systems that must answer questions from long histories of web-agent trajectories. The dataset combines web-domain trajectories from customized shopping, shopping-admin, and forum sites with enterprise-domain trajectories from customized ServiceNow-style tasks.

## Contents

- 451 questions across static state recall, dynamic state tracking, workflow/procedure knowledge, environment gotchas, and premise-awareness/abstention categories.
- 1,870 trajectories with task goals, outcomes, ordered states, actions, agent thoughts, accessibility-tree observations, and screenshots.
- Two haystack tiers: LME-V2-Small and LME-V2-Medium. Each haystack file maps a question id directly to the trajectory ids that should be available to the memory system for that question.

## Intended Use

The dataset is intended for evaluating long-term memory and retrieval systems for agents. Systems should consume a question-specific haystack of trajectories and return evidence or answers using the released evaluation code.

## Out-of-Scope Use

The dataset should not be treated as a general web-browsing benchmark, a live environment replay dataset, or a source of real user behavior. The environments are customized benchmark environments and the task contents are synthetic or benchmark-generated.

## Data Fields

See `SCHEMA.md` for field-level documentation.

## Privacy and Sensitive Information

The data comes from benchmark environments rather than real user accounts. It may contain synthetic names, synthetic record identifiers, synthetic products, or synthetic enterprise records created by the environments. Local source paths and construction provenance have been removed from public records.

## Limitations

The benchmark covers specific web and ServiceNow-style environments. Results may not transfer directly to arbitrary live websites, private enterprise systems, or domains with different UI patterns. Screenshots and accessibility trees reflect the state of the benchmark environments at collection time.

## Large Files

Full trajectory screenshots are provided under `trajectory_screenshots/`. Hugging Face stores the uploaded screenshot bundles as `.tar.gz` archives; extract them into a local `screenshots/` directory before running screenshot-dependent evaluations. Kaggle exposes the same uploaded screenshot tarballs as expanded directories.

## License

This dataset is released under the Apache License 2.0.
