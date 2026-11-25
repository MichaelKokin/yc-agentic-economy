#!/usr/bin/env python3
"""Count AI / agent / physical / defense / Service-as-Software shares across YC batches.

Input: a frozen snapshot of yc-oss/api (https://github.com/yc-oss/api) — batch JSON files
`batches/<season>-<year>.json` plus `meta.json` and `YC_OSS_COMMIT.txt`.

Output (to --out): companies.csv, batch_metrics.csv/.json, year_metrics.csv,
term_heatmap.csv, industry_mix.csv, top_tags.csv, audit_*.csv, snapshot.json.

Every metric is a text proxy over the public one_liner + long_description (and YC tags where
stated). It is NOT YC's own classification. Methods are documented in METHOD below and in the
README of the dataset.

Usage:
  python3 -I count_yc.py --raw <snapshot dir> --out <processed dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, OrderedDict
from pathlib import Path

SEASONS = OrderedDict([("winter", "W"), ("spring", "X"), ("summer", "S"), ("fall", "F")])
YEARS = range(2019, 2027)

# ---------------------------------------------------------------- AI-core (2025 method)
# Explicit AI/LLM/ML markers in one_liner or long_description. "AI" and "ML" are
# case-sensitive so domains like "acme.ai" and words like "html" never match.
AI_CORE = [
    r"\bA\.?I\b", r"GenAI", r"(?i:\bartificial intelligence\b)",
    r"(?i:\bLLMs?\b)", r"(?i:\b(large )?language models?\b)", r"(?i:\bfoundation models?\b)",
    r"(?i:\bmachine learning\b)", r"\bML\b", r"(?i:\bdeep learning\b)",
    r"(?i:\bneural (networks?|nets?)\b)", r"(?i:\bcomputer vision\b)", r"\bNLP\b",
    r"(?i:\bnatural language processing\b)", r"\bGPT(-?\d+(\.\d+)?)?\b",
    r"(?i:\breinforcement learning\b)", r"(?i:\bdiffusion models?\b)",
    r"(?i:\bvision[- ]language\b)", r"\bVLMs?\b", r"\bVLAs?\b",
    r"(?i:\bspeech recognition\b)", r"(?i:\btext[- ]to[- ](speech|image|video)\b)",
    # added 2026-11: unambiguous model-building language that 2025 descriptions rarely used
    r"(?i:\b(speech|voice|video|audio|frontier|open[- ]weights?|small|reasoning|robotics?|world|"
    r"generative|multimodal|interaction|embedding|AI|ML) models?\b)",
    r"(?i:\bfine[- ]tun\w+\b)", r"(?i:\bembeddings?\b)", r"\bRAG\b", r"(?i:\bchatbots?\b)",
    r"(?i:\bmodel (training|inference)\b)", r"(?i:\binference (engine|platform|stack|chips?|cost)\b)",
]
# AI-use (wider): AI-core OR agent/copilot/assistant/autonomous product language.
AI_USE_EXTRA = [
    r"(?i:\bagent(s|ic)?\b)", r"(?i:\bco-?pilots?\b)", r"(?i:\bassistants?\b)",
    r"(?i:\bautonomous(ly)?\b)", r"(?i:\bautopilot\b)",
]
# AI-tag: official YC Directory tags.
AI_TAGS = {
    "AI", "Artificial Intelligence", "Generative AI", "Machine Learning", "Conversational AI",
    "AI Assistant", "Deep Learning", "Computer Vision", "NLP", "AIOps",
    "Reinforcement Learning", "AI-powered Drug Discovery", "AI-Enhanced Learning", "Swarm AI",
}

# ---------------------------------------------------------------- agents
AGENT_TOKEN = re.compile(r"\b(multi-)?agent(s|ic)?\b", re.I)
# "real estate agent", "insurance agents", "user agent" etc. are people/roles, not AI agents.
AGENT_EXCLUDE_BEFORE = re.compile(
    r"(real[- ]estate|insurance|travel|leasing|listing|buyer'?s?|seller'?s?|user|free|border|"
    r"patrol|cleaning|chemical|biological|therapeutic|contrast|sports|talent|booking|shipping|"
    r"customs|freight|loan|mortgage|rental|property|claims|support|field|human|secret|double|"
    r"bonding|antimicrobial|anti-?cancer|imaging)\s*$",
    re.I,
)
AGENT_EXTRA = [
    r"(?i:\bAI (employees?|workers?|teammates?|coworkers?|co-workers?|SDRs?|BDRs?|receptionists?)\b)",
    r"(?i:\b(digital|virtual) (employees?|workers?|workforce)\b)", r"(?i:\bAI workforce\b)",
]

# Infrastructure where agents are the user/customer ("agents for agents", "make something
# agents want"): tooling to build/run/secure/pay/observe agents, MCP, A2A, computer use.
AGENT_INFRA = [
    r"(?i:\bfor (the |your |their |all |any |every |autonomous |AI |LLM |coding |voice |browser |"
    r"enterprise |production |computer[- ]use |building |hiring |deploying |running |testing )*agents\b)",
    r"(?i:\bagent(s|ic)? (infrastructure|infra|observability|monitoring|evals?|evaluations?|"
    r"testing|security|identity|auth|authentication|authorization|memory|payments?|wallets?|"
    r"browsers?|sandbox(es)?|orchestration|frameworks?|tooling|toolkit|SDKs?|APIs?|"
    r"runtime|hosting|marketplace|harness|gateway|firewall|reliability|analytics|"
    r"simulation|environments?|ops|governance|guardrails|compute|commerce|economy|internet|web|"
    r"experience|control plane)\b)",
    r"(?i:\bagent[- ]native\b)", r"(?i:\bAgentOps\b)", r"\bMCPs?\b", r"(?i:\bmodel context protocol\b)",
    r"\bA2A\b", r"(?i:\bagent[- ]?(to|2)[- ]?agent\b)",
    r"(?i:\b(LLM|AI) (observability|evals?|evaluations?|gateway|firewall|red[- ]teaming|guardrails)\b)",
    r"(?i:\bcomputer[- ]use (API|infrastructure|infra|platform|SDK|sandbox|environments?|models?)\b)",
    r"(?i:\b(helps?|lets?|enables?|allows?|empowers?)( you| teams| developers| companies| engineers| builders|"
    r" enterprises| businesses)?( to)? (build|ship|deploy|run|host|train|test|evaluate|monitor|secure|improve|"
    r"engineer|debug|scale|observe|govern|orchestrate)\w* (better |reliable |production |your |their |custom |"
    r"AI |autonomous |LLM |voice |coding )*agents\b)",
    r"(?i:\b(monitor|test|evaluat|secur|orchestrat|debug|govern|observ|sandbox|host)\w* (your |their |AI |"
    r"autonomous |LLM |voice |coding )+agents\b)",
    r"(?i:\b(AI |autonomous |LLM |coding )?agents? (to|can|could) (access|use|pay|browse|call|read|interact|"
    r"transact|log ?in|sign|navigate|discover|buy|purchase|hire|talk|communicate|negotiate|hold|spend)\b)",
    r"(?i:\b(lets|let|allows?|enables?|gives?) (AI |autonomous |LLM |coding )?agents\b)",
    r"(?i:\bfor conversational agents\b)", r"(?i:\bagent'?s (actions?|session|memory|context|tools?)\b)",
    r"(?i:\bagent session\b)", r"(?i:\b(train|eval\w*|build)( and|,)? (eval\w*|build|train|deploy)\w*( and build)? (autonomous |AI )?agents\b)",
    r"(?i:\bevals? for ([\w-]+ ){0,3}agents\b)", r"(?i:\bfor AI to (interact|use|operate|access|browse)\b)",
    r"(?i:\b(Open ?Claw|Clawdbot|Moltbot)\b)", r"(?i:\b(use|run|using|running|on|with) (Claude Code|Codex)\b)",
]
# Machine-to-machine / agent commerce.
M2M = [
    r"\bA2A\b", r"(?i:\bagent[- ]?(to|2)[- ]?agent\b)", r"(?i:\bagentic (commerce|payments?)\b)",
    r"(?i:\bagent (payments?|wallets?|commerce|economy)\b)",
    r"(?i:\bpayments? (for|between) (AI )?agents\b)", r"(?i:\bmachine[- ]to[- ]machine\b)",
    r"(?i:\bagents? (that |can |to )?(pay|transact|buy|purchase|hire)\b)",
]

# ---------------------------------------------------------------- physical / defense
PHYSICAL_TEXT = [
    r"(?i:\brobot(s|ic|ics)?\b)", r"(?i:\bhumanoids?\b)", r"(?i:\bdrones?\b)", r"\bUAVs?\b",
    r"(?i:\bembodied\b)", r"(?i:\bactuators?\b)", r"(?i:\bphysical AI\b)", r"(?i:\bself-driving\b)",
    r"(?i:\bautonomous (vehicles?|trucks?|driving|ships?|vessels?|boats?|aircraft|tractors?|"
    r"machines?|systems?|delivery|mining|construction)\b)",
    r"(?i:\bexoskeletons?\b)", r"(?i:\bsatellites?\b)", r"(?i:\brockets?\b)", r"(?i:\bspacecraft\b)",
    r"(?i:\bmanipulat(ors?|ion)\b)", r"(?i:\bVLAs?\b)", r"(?i:\bworld models?\b)",
]
PHYSICAL_TAGS = {
    "Robotics", "Drones", "Hard Tech", "Hardware", "Swarm Robotics", "Robotic Surgery",
    "Autonomous Delivery", "Autonomous Shipping", "Space Exploration", "Commercial Space Launch",
    "Aerospace", "Airplanes", "Autonomous Trucking", "Manufacturing",
}
PHYSICAL_SUB = {
    "Industrials -> Manufacturing and Robotics", "Industrials -> Drones",
    "Industrials -> Aviation and Space", "Industrials -> Defense",
}
DEFENSE_TEXT = re.compile(
    r"\b(defen[cs]e|military|national security|warfighters?|DoD|Pentagon|munitions?|"
    r"counter-?(drone|UAS)s?|dual-use|battlefield|armed forces|weapons?|navy|army|air force|"
    r"missiles?|ISR)\b",
    re.I,
)
DEFENSE_EXCLUDE_BEFORE = re.compile(r"(cyber|fraud|legal|bot|threat|DDoS|claims|criminal|insurance|"
                                    r"email|phishing|identity|account|chargeback|return)[\s-]*$", re.I)

# ---------------------------------------------------------------- Service-as-Software (proxy)
# Companies that sell the finished work (an AI-native firm or an "AI employee") rather than a
# tool for a human. Proxy, audited by hand on a sample (audit_sas.csv).
SAS_FIRM = [
    r"(?i:\bAI(-| )?(native|first|powered|enabled|led)?,? ((?!for\b|to\b|that\b|and\b|with\b)[\w&-]+ ){0,3}(law firm|accounting firm|firm|brokerage|"
    r"agency|services? (firm|company|provider)|staffing (firm|agency)|consultancy|tax firm|CRO|"
    r"recruiting firm|dev shop|BPO|call center|hedge fund|bank|lender|insurer|insurance carrier|pharmacy|clinic|"
    r"medical practice|title company|property manager|general contractor|freight forwarder|customs broker|"
    r"billing services|bookkeeping (firm|service))s?\b)",
    r"(?i:\bfull[- ]stack (AI )?(law firm|accounting|agency|insurance|brokerage|bank|services|"
    r"company|firm|lender|CRO|pharmacy)\b)",
    r"(?i:\bdone[- ]for[- ]you\b)",
    r"(?i:\breplac(es?|ing) (your |the |entire |an? )*(team|teams|staff|humans?|employees|agency|"
    r"agencies|outsourc\w+|BPOs?|call centers?|offshore)\b)",
    r"(?i:\boutcome[- ]based pricing\b)", r"(?i:\bpay(s)? (only )?(per|for) (outcomes?|results?)\b)",
    r"(?i:\bservices?[- ]as[- ](a[- ])?software\b)",
]
SAS_WORKER = [
    r"(?i:\bAI(-powered)? ((?!for\b|to\b|that\b|and\b|with\b|your\b)[\w&-]+ ){0,2}(employees?|workers?|teammates?|coworkers?|co-workers?|accountants?|bookkeepers?|"
    r"lawyers?|attorneys?|paralegals?|SDRs?|BDRs?|recruiters?|recruiting coordinators?|nurses?|receptionists?|"
    r"billers?|scribes?|underwriters?|adjusters?|auditors?|CFOs?|controllers?|associates?|operators?|staff|"
    r"workforce|analysts?|data analysts?|consultants?|tax preparers?|brokers?|dispatchers?|coordinators?|"
    r"case managers?|medical coders?|SREs?|DevOps engineers?|production engineers?|research engineers?|"
    r"software engineers?|QA engineers?|security engineers?|doctors?|physicians?|therapists?|tutors?|"
    r"designers?|marketers?|copywriters?|bankers?|chiefs? of staff|executive assistants?)\b)",
    r"(?i:\b(digital|virtual) (employees?|workers?|workforce)\b)",
]
SAS = SAS_FIRM + SAS_WORKER
SAS_EXCLUDE = re.compile(r"(?i)\b(for|helps?|to) (AI |human |the )?(engineers|analysts|consultants|recruiters|lawyers|"
                         r"accountants|brokers|doctors|designers|marketers)\b")

# ---------------------------------------------------------------- heatmap terms
TERMS = OrderedDict([
    ("agent", r"(?i:\bagent(s|ic)?\b)"),
    ("copilot", r"(?i:\bco-?pilots?\b)"),
    ("assistant", r"(?i:\bassistants?\b)"),
    ("autonomous", r"(?i:\bautonomous(ly)?\b)"),
    ("LLM", r"(?i:\bLLMs?\b)"),
    ("reasoning", r"(?i:\breason(ing|s)?\b)"),
    ("generative", r"(?i:\bgenerative\b|\bgen[- ]?AI\b)"),
    ("GPT", r"\bGPT\b"),
    ("AI-native", r"(?i:\bAI[- ]native\b)"),
    ("voice", r"(?i:\bvoice\b)"),
    ("MCP", r"\bMCPs?\b|(?i:model context protocol)"),
    ("evals", r"(?i:\bevals?\b|\bevaluations?\b)"),
    ("observability", r"(?i:\bobservability\b)"),
    ("security", r"(?i:\bsecurity\b)"),
    ("compliance", r"(?i:\bcomplian(ce|t)\b)"),
    ("infrastructure", r"(?i:\binfrastructure\b)"),
    ("open-source", r"(?i:\bopen[- ]source\b)"),
    ("browser", r"(?i:\bbrowsers?\b)"),
    ("memory", r"(?i:\bmemory\b)"),
    ("RL", r"(?i:\breinforcement learning\b|\bRL\b)"),
    ("world model", r"(?i:\bworld models?\b)"),
    ("synthetic data", r"(?i:\bsynthetic data\b)"),
    ("robot", r"(?i:\brobot(s|ic|ics)?\b)"),
    ("drone", r"(?i:\bdrones?\b)"),
    ("defense", r"(?i:\bdefen[cs]e\b)"),
    ("healthcare", r"(?i:\bhealth ?care\b|\bclinical\b|\bpatients?\b|\bhospitals?\b)"),
    ("legal", r"(?i:\blegal\b|\blaw firms?\b|\blawyers?\b|\battorneys?\b)"),
    ("insurance", r"(?i:\binsurance\b)"),
    ("accounting", r"(?i:\baccounting\b|\bbookkeeping\b|\baccountants?\b)"),
    ("government", r"(?i:\bgovernment\b|\bpublic sector\b|\bmunicipal\w*\b)"),
    ("data center", r"(?i:\bdata cent(er|re)s?\b|\bGPUs?\b)"),
    ("crypto", r"(?i:\bcrypto\w*\b|\bblockchain\b|\bweb3\b|\bstablecoins?\b)"),
    ("vibe coding", r"(?i:\bvibe[- ]cod\w*\b)"),
    ("Cursor for X", r"(?i:\bCursor for\b)"),
    ("OpenClaw", r"(?i:\bOpen ?Claw\b|\bClawdbot\b|\bMoltbot\b)"),
])


def compile_all(patterns):
    return [re.compile(p) for p in patterns]


AI_CORE_RE = compile_all(AI_CORE)
AI_USE_RE = compile_all(AI_USE_EXTRA)
AGENT_EXTRA_RE = compile_all(AGENT_EXTRA)
AGENT_INFRA_RE = compile_all(AGENT_INFRA)
M2M_RE = compile_all(M2M)
PHYSICAL_RE = compile_all(PHYSICAL_TEXT)
SAS_RE = compile_all(SAS)
SAS_FIRM_RE = compile_all(SAS_FIRM)
SAS_WORKER_RE = compile_all(SAS_WORKER)
TERMS_RE = OrderedDict((k, re.compile(v)) for k, v in TERMS.items())


def hits(regexes, text):
    out = []
    for rx in regexes:
        m = rx.search(text)
        if m:
            out.append(m.group(0))
    return out


def agent_hits(text):
    found = []
    for m in AGENT_TOKEN.finditer(text):
        before = text[max(0, m.start() - 30):m.start()]
        if AGENT_EXCLUDE_BEFORE.search(before):
            continue
        found.append(m.group(0))
    found += hits(AGENT_EXTRA_RE, text)
    return found


def defense_hits(text):
    found = []
    for m in DEFENSE_TEXT.finditer(text):
        before = text[max(0, m.start() - 20):m.start()]
        if DEFENSE_EXCLUDE_BEFORE.search(before):
            continue
        found.append(m.group(0))
    return found


def _norm_name(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(inc|llc|labs?|ai|technologies|technology|hq|app|io|co|corp|corporation|the|formerly)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def renamed(c):
    """True when the directory keeps a former name that is not just a spelling variant of the current one."""
    cur = _norm_name(c.get("name") or "")
    for f in c.get("former_names") or []:
        fn = _norm_name(f)
        if fn and fn != cur and fn not in cur and cur not in fn:
            return True
    return False


def classify(c):
    one = c.get("one_liner") or ""
    desc = c.get("long_description") or ""
    text = f"{one}\n{desc}"
    tags = set(c.get("tags") or [])
    sub = c.get("subindustry") or ""
    ind = c.get("industry") or ""

    ai_core = hits(AI_CORE_RE, text)
    ai_use_extra = hits(AI_USE_RE, text)
    ai_tag = sorted(tags & AI_TAGS)
    agent = agent_hits(text)
    infra = hits(AGENT_INFRA_RE, text)
    m2m = hits(M2M_RE, text)
    physical = hits(PHYSICAL_RE, text)
    physical_tag = sorted(tags & PHYSICAL_TAGS)
    physical_sub = sub in PHYSICAL_SUB
    defense = defense_hits(text)
    defense_meta = sub == "Industrials -> Defense"
    sas_firm = hits(SAS_FIRM_RE, text)
    sas_worker = [] if SAS_EXCLUDE.search(one) else hits(SAS_WORKER_RE, text)
    sas = sas_firm + sas_worker

    return {
        "ai_core": bool(ai_core),
        "ai_use": bool(ai_core or ai_use_extra),
        "ai_tag": bool(ai_tag),
        "agent": bool(agent),
        "agent_infra": bool(infra),
        "m2m": bool(m2m),
        "physical": bool(physical or physical_sub),
        "defense": bool(defense or defense_meta),
        "sas": bool(sas),
        "sas_firm": bool(sas_firm),
        "sas_worker": bool(sas_worker),
        "b2b": ind == "B2B",
        "_ai_core_hits": ai_core,
        "_agent_hits": agent,
        "_infra_hits": infra,
        "_m2m_hits": m2m,
        "_physical_hits": physical + ([sub] if physical_sub else []),
        "_defense_hits": defense + (["sub:Defense"] if defense_meta else []),
        "_sas_hits": sas,
        "_terms": [k for k, rx in TERMS_RE.items() if rx.search(text)],
    }


FLAGS = ["ai_core", "ai_use", "ai_tag", "agent", "agent_infra", "m2m", "physical", "defense", "sas", "sas_firm", "sas_worker", "b2b"]


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def summarize(rows):
    n = len(rows)
    out = OrderedDict(n=n)
    for f in FLAGS:
        k = sum(1 for r in rows if r[f])
        out[f + "_n"] = k
        out[f + "_pct"] = pct(k, n)
    sizes = [r["team_size"] for r in rows if isinstance(r["team_size"], int) and r["team_size"] > 0]
    out["renamed_pct"] = pct(sum(1 for r in rows if r["renamed"]), n)
    out["inactive_pct"] = pct(sum(1 for r in rows if r["status"] == "Inactive"), n)
    out["acquired_pct"] = pct(sum(1 for r in rows if r["status"] == "Acquired"), n)
    tagged = sum(1 for r in rows if r["tags"])
    out["tagged_pct"] = pct(tagged, n)
    # AI-tag is measured among companies that have any YC tag at all: tag coverage fell from
    # ~97% (2019) to ~70-80% (2025) and ~30% (W26, X26), so untagged != "not AI".
    out["ai_tag_pct"] = pct(out["ai_tag_n"], tagged) if tagged >= 0.6 * n else None
    out["team_size_known_n"] = len(sizes)
    out["team_size_median"] = statistics.median(sizes) if sizes else None
    out["team_le3_pct"] = pct(sum(1 for s in sizes if s <= 3), len(sizes))
    out["team_le5_pct"] = pct(sum(1 for s in sizes if s <= 5), len(sizes))
    out["agent_among_ai_core_pct"] = pct(sum(1 for r in rows if r["agent"] and r["ai_core"]),
                                         sum(1 for r in rows if r["ai_core"]))
    out["infra_among_agent_pct"] = pct(sum(1 for r in rows if r["agent_infra"] and r["agent"]),
                                       sum(1 for r in rows if r["agent"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    meta = json.loads((raw / "meta.json").read_text())
    commit = (raw / "YC_OSS_COMMIT.txt").read_text().split()[0] if (raw / "YC_OSS_COMMIT.txt").exists() else None
    downloaded = (raw / "SNAPSHOT_DOWNLOADED_AT.txt").read_text().strip() if (raw / "SNAPSHOT_DOWNLOADED_AT.txt").exists() else None

    rows = []
    for y in YEARS:
        for season, letter in SEASONS.items():
            f = raw / "batches" / f"{season}-{y}.json"
            if not f.exists():
                continue
            code = f"{letter}{str(y)[2:]}"
            for c in json.loads(f.read_text()):
                cl = classify(c)
                ts = c.get("team_size")
                rows.append(OrderedDict(
                    batch=code, season=season, year=y, order=y * 10 + list(SEASONS).index(season),
                    name=c.get("name"), slug=c.get("slug"), one_liner=c.get("one_liner") or "",
                    industry=c.get("industry") or "", subindustry=c.get("subindustry") or "",
                    tags="|".join(c.get("tags") or []), team_size=ts if isinstance(ts, int) else None,
                    status=c.get("status") or "", top_company=bool(c.get("top_company")),
                    former_names="|".join(c.get("former_names") or []), renamed=renamed(c),
                    website=c.get("website") or "", yc_url=c.get("url") or "",
                    **{k: cl[k] for k in FLAGS},
                    ai_core_hits="; ".join(cl["_ai_core_hits"]),
                    agent_hits="; ".join(cl["_agent_hits"]),
                    agent_infra_hits="; ".join(cl["_infra_hits"]),
                    m2m_hits="; ".join(cl["_m2m_hits"]),
                    physical_hits="; ".join(cl["_physical_hits"]),
                    defense_hits="; ".join(cl["_defense_hits"]),
                    sas_hits="; ".join(cl["_sas_hits"]),
                    terms="|".join(cl["_terms"]),
                    long_description=(c.get("long_description") or "").replace("\r", " "),
                ))
    rows.sort(key=lambda r: (r["order"], (r["name"] or "").lower()))

    # companies.csv (full text kept for audit; public CSV drops long_description? keep, it is public data)
    with open(out / "companies.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    batches = OrderedDict()
    for r in rows:
        batches.setdefault(r["batch"], []).append(r)
    bm = []
    for code, rs in batches.items():
        s = summarize(rs)
        bm.append(OrderedDict(batch=code, year=rs[0]["year"], season=rs[0]["season"], **s))
    years = OrderedDict()
    for r in rows:
        years.setdefault(r["year"], []).append(r)
    ym = [OrderedDict(year=y, batches="+".join(sorted({r["batch"] for r in rs}, key=lambda b: "WXSF".index(b[0]))), **summarize(rs))
          for y, rs in years.items()]

    for name, data in (("batch_metrics", bm), ("year_metrics", ym)):
        with open(out / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    # term heatmap: share of companies in batch mentioning each term (2023+ only, the readable window)
    hm = []
    for code, rs in batches.items():
        n = len(rs)
        row = OrderedDict(batch=code, n=n)
        for t in TERMS:
            row[t] = pct(sum(1 for r in rs if t in r["terms"].split("|")), n)
        hm.append(row)
    with open(out / "term_heatmap.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hm[0].keys()))
        w.writeheader()
        w.writerows(hm)

    # industry mix
    inds = sorted({r["industry"] for r in rows if r["industry"]})
    im = []
    for code, rs in batches.items():
        n = len(rs)
        row = OrderedDict(batch=code, n=n)
        for i in inds:
            row[i] = pct(sum(1 for r in rs if r["industry"] == i), n)
        im.append(row)
    with open(out / "industry_mix.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(im[0].keys()))
        w.writeheader()
        w.writerows(im)

    # top tags per year
    tt = []
    for y, rs in years.items():
        cnt = Counter(t for r in rs for t in r["tags"].split("|") if t)
        for rank, (t, k) in enumerate(cnt.most_common(15), 1):
            tt.append(OrderedDict(year=y, rank=rank, tag=t, n=k, pct=pct(k, len(rs))))
    with open(out / "top_tags.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tt[0].keys()))
        w.writeheader()
        w.writerows(tt)

    # audit files for hand checks
    for flag in ("agent_infra", "sas", "m2m", "defense"):
        with open(out / f"audit_{flag}.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["batch", "name", "one_liner", f"{flag}_hits", "yc_url"])
            for r in rows:
                if r[flag] and r["year"] >= 2025:
                    w.writerow([r["batch"], r["name"], r["one_liner"], r[f"{flag}_hits"] if flag != "sas" else r["sas_hits"], r["yc_url"]])

    snapshot = OrderedDict(
        source="yc-oss/api (public YC Startup Directory mirror)",
        source_repo="https://github.com/yc-oss/api",
        source_commit=commit,
        source_last_updated=meta.get("last_updated"),
        downloaded_at=downloaded,
        batches={code: len(rs) for code, rs in batches.items()},
        companies=len(rows),
        flags=FLAGS,
        note=("Directory lists companies YC currently shows; companies removed from the directory "
              "are absent, so older batches may be undercounted. team_size is today's team size, "
              "not the size at Demo Day. F26 was still in progress on the snapshot date."),
    )
    (out / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    (out / "batch_metrics.json").write_text(json.dumps({"snapshot": snapshot, "batches": bm, "years": ym, "terms": hm, "industries": im},
                                                        ensure_ascii=False, indent=1))
    print(json.dumps(snapshot, indent=1))


if __name__ == "__main__":
    main()
