# State of AI Startups 2026 — the open dataset

Data and counting script behind **State of AI Startups 2026: what business to build when AI writes the code**,
a study of the Y Combinator directory by Michael Kokin (AIGENCY, November 2026):

- landing: https://aigency.michaelkokin.com/en/research/yc-agentic-economy ([in Russian](https://aigency.michaelkokin.com/ru/research/yc-agentic-economy))
- full report: https://aigency.michaelkokin.com/en/research/yc-agentic-economy/report (PDF on the page)

4,720 Y Combinator companies from 21 batches (W19 → F26), classified with transparent text
proxies: AI-core, AI-use, AI-tag, agents, products for agents, machine-to-machine commerce,
physical AI / hard tech, defense, services and software for specific jobs (Service-as-Software), B2B —
plus team size. Industrial startups in the report follow YC's own sector, **Industrials** (`industry_mix.csv`).

## Snapshot

| | |
|---|---|
| Source | [yc-oss/api](https://github.com/yc-oss/api) — public mirror of the YC Startup Directory |
| Source commit | `e06fbbcb55fab7c82a1f6d2e3e681d76af1a1908` |
| Source `last_updated` | 2026-11-23T04:50:38Z |
| Downloaded | 2026-11-23 |
| Batches | W19, S19, W20, S20, W21, S21, W22, S22, W23, S23, W24, S24, F24, W25, X25, S25, F25, W26, X26, S26, F26 |

F26 was still in progress on the snapshot date. X = Spring (S is taken by Summer).

## Files

```
data/raw/                 frozen yc-oss files used for every number (batches/*.json, meta.json, top.json)
data/processed/
  companies.csv           one row per company: batch, one-liner, industry, tags, team size,
                          every flag below and the exact words that triggered it
  batch_metrics.csv/.json shares per batch
  year_metrics.csv        shares per calendar year
  term_heatmap.csv        % of companies per batch whose description contains a term
  industry_mix.csv        YC industry shares per batch
  top_tags.csv            top-15 YC tags per year
  audit_*.csv             flagged companies 2025–2026 for hand review
  audit_w26_manual.csv    hand classification of all 198 W26 companies
  f26_rfs_manual.csv      hand mapping of F26 companies to YC's Requests for Startups
                          (Fall 2026, Winter 2027, Summer 2026 lists)
scripts/count_yc.py       the whole method, standard library only
```

Reproduce:

```bash
python3 -I scripts/count_yc.py --raw data/raw --out data/processed
```

## Method

Every metric is a **text proxy** over `one_liner` + `long_description` (and YC sub-industry where
stated). It is not YC's own classification. The full dictionaries are in `scripts/count_yc.py`.

| Flag | Rule |
|---|---|
| `ai_core` | explicit AI/ML wording: AI, LLM, machine learning, computer vision, foundation/speech/world model, fine-tuning, RAG… ("AI" and "ML" are case-sensitive) |
| `ai_use` | `ai_core` OR agent / copilot / assistant / autonomous |
| `ai_tag` | an official YC tag from the AI group; share is measured **among tagged companies only** and left empty when fewer than 60% of a batch have tags (W26, X26) |
| `agent` | the product is described as an agent or an "AI employee"; human agents (real-estate, insurance, travel…) are excluded |
| `agent_infra` | products for agents — the customer is an agent: sandboxes, VMs and computers for agents, agent payments and wallets, MCP, agent evals/observability/security/memory, "for (AI) agents" |
| `m2m` | agent-to-agent / agentic commerce / agents that pay or transact |
| `physical` | robots, drones, autonomous vehicles, space, manufacturing — text or YC sub-industry (Manufacturing and Robotics, Drones, Aviation and Space, Defense). Tags are not used: W26/X26 are mostly untagged |
| `defense` | defense / military / counter-UAS… (not cyber or fraud "defense") or sub-industry Defense |
| `sas` = `sas_firm` ∪ `sas_worker` | services and software for specific jobs. `sas_firm`: the company delivers a service to clients itself, with AI (law firm, brokerage, accounting, billing…) — Service-as-Software; `sas_worker`: software sold as an "AI employee" for a named role. In 2026: 36 + 46 − 2 in both = 80 companies |
| `b2b` | YC industry = B2B |
| `renamed` | the directory keeps a former name that is not just a spelling variant of the current one (a pivot proxy: a rename is not always a product change) |
| `status` | Active / Inactive / Acquired, as the directory shows it today |

The term heatmap counts 35+ words (agent, autonomous, reasoning, copilot, generative, robot, defense, MCP…) per batch.

**Accuracy.** Hand check of all 198 W26 companies: `agent_infra` 23 by hand vs 24 flagged
(precision 0.92, recall 0.96); `sas` 23 by hand vs 26 flagged (precision 0.88, recall 1.00).
The dictionaries were tuned on W26, so this is not an independent test; a precision read of F26
flags gave a similar picture (~0.85–0.9).

**Limitations.**
- The directory lists the companies YC shows today. On the archived directory of November 23, 2025
  the 2025 batches held 635 companies; on this snapshot — 619. Older batches can be undercounted.
- `team_size` is today's team size, not the size at Demo Day; newer batches look smaller partly
  because they are younger.
- Companies rewrite their descriptions; the same method on the 15 Dec 2025 snapshot gave AI-core
  16.9% (W19) → 78.5% (2025); this snapshot gives 19.6% → 72.5%.

## Headline numbers (snapshot 2026-11-23)

Shares of all companies of the year; flags can overlap. `Physical` is the text proxy; the report's industrial
startups are YC's Industrials sector: 63 companies (10.2%) in 2025, 167 (19.5%) in 2026.

| Year | Companies | AI-core | AI-use | Agents | Infra for agents | Physical | Defense | SaS | B2B | Median team | Team ≤3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019 | 368 | 18.5% | 22.6% | 4.3% | 1.4% | 6.0% | 1.1% | 0.8% | 40.8% | 12 | 19.9% |
| 2023 | 494 | 57.7% | 63.6% | 23.7% | 4.3% | 2.4% | 0.4% | 5.1% | 67.6% | 5 | 36.9% |
| 2024 | 590 | 68.3% | 76.1% | 31.4% | 5.9% | 7.8% | 2.4% | 6.3% | 62.9% | 4 | 43.1% |
| 2025 | 619 | 72.5% | 80.6% | 40.2% | 9.2% | 10.3% | 2.7% | 9.0% | 65.3% | 4 | 47.6% |
| 2026 | 855 | 69.9% | 83.3% | 43.2% | 14.2% | 19.2% | 4.8% | 9.4% | 56.5% | 3 | 68.6% |

## License

Code — MIT (`LICENSE`). Processed data — CC BY 4.0 (please cite «Michael Kokin / AIGENCY, State of AI
Startups 2026 dataset, YC directory snapshot 2026-11-23»). Company descriptions belong to their authors and come from the public YC
directory via yc-oss.
