#!/usr/bin/env python3
"""Score a home-service contractor's Google Ads account from its own exported reports.

Usage:
    python3 score.py --campaigns campaigns.csv --search-terms search_terms.csv \
        [--answers answers.json] [--format markdown|json]

Reads only the files it is given, uses only the Python standard library, and never
sends anything anywhere. Every number in the report is computed here, so the result
is the same whichever AI model runs it.

The checks are described in references/checks.md. The answers file holds the owner's
replies to the questions in SKILL.md; see examples/answers.json.
"""

import argparse
import csv
import io
import json
import re
import sys

SKILL_VERSION = "1.1"
CTA_URL = ("https://webnwell.com/free-google-ads-audit/"
           "?utm_source=agent-skill&utm_medium=skill&utm_campaign=google-ads-audit#ask-a-person")

# ---------------------------------------------------------------- reading the exports

COLUMNS = {
    "campaign": ["campaign", "campaign name"],
    "campaign_type": ["campaign type", "advertising channel type", "channel type"],
    "status": ["campaign status", "status", "campaign state"],
    "bid_strategy": ["bid strategy type", "campaign bid strategy type", "bid strategy"],
    "cost": ["cost", "spend", "amount spent"],
    "clicks": ["clicks"],
    "impressions": ["impr.", "impressions", "impr"],
    "conversions": ["conversions", "conv.", "all conv."],
    "lost_budget": ["search lost is (budget)", "search lost impression share (budget)"],
    "lost_rank": ["search lost is (rank)", "search lost impression share (rank)"],
    "currency": ["currency code", "currency"],
    "search_term": ["search term", "search terms", "query"],
    "match_type": ["match type", "search term match type", "keyword match type"],
    "added_excluded": ["added/excluded", "added / excluded", "status (search term)"],
}


def _decode(raw):
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if len(raw) > 3 and raw[1:2] == b"\x00" and raw[3:4] == b"\x00":
        return raw.decode("utf-16-le")
    return raw.decode("utf-8-sig", errors="replace")


def _norm(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def read_report(path, key_column):
    """Return a list of dicts keyed by our column names. Finds the header row itself,
    because Google Ads puts a report title and a date range above it."""
    with open(path, "rb") as fh:
        text = _decode(fh.read())
    lines = text.splitlines()
    sample = "\n".join(lines[:10])
    delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    aliases = {alias: key for key, names in COLUMNS.items() for alias in names}
    for i, row in enumerate(rows[:15]):
        header = [_norm(c) for c in row]
        if any(aliases.get(h) == key_column for h in header):
            mapping = {}
            for idx, h in enumerate(header):
                key = aliases.get(h)
                if key and key not in mapping:
                    mapping[key] = idx
            out = []
            for data in rows[i + 1:]:
                if not data or all(not c.strip() for c in data):
                    continue
                first = (data[0] if data else "").strip().lower()
                if first.startswith("total") or first.startswith("--"):
                    continue
                rec = {k: (data[idx].strip() if idx < len(data) else "") for k, idx in mapping.items()}
                if key_column in rec and rec[key_column].lower().startswith("total"):
                    continue
                out.append(rec)
            return out, set(mapping)
    raise SystemExit(
        f"Could not find a '{key_column.replace('_', ' ')}' column in {path}. "
        "Export the report from Google Ads as CSV with that column included.")


def num(value):
    """Parse '1,234.50', '$12.30', '12.5%', '< 10%', '--' into a float, or None."""
    if value is None:
        return None
    v = str(value).strip()
    if v in ("", "--", "—", " --"):
        return None
    pct = "%" in v
    if v.startswith("<"):
        v, nudge = v[1:], -1
    elif v.startswith(">"):
        v, nudge = v[1:], 1
    else:
        nudge = 0
    v = re.sub(r"[^0-9.\-]", "", v.replace(",", ""))
    if v in ("", "-", "."):
        return None
    try:
        n = float(v)
    except ValueError:
        return None
    if pct:
        n = n / 100.0
        if nudge:  # "< 10%" -> 5%, "> 90%" -> 95%
            n = n - 0.05 if nudge < 0 else n + 0.05
    return n


def money(n, cur):
    sign = "$" if cur in ("USD", "CAD", "AUD", "") else ""
    suffix = "" if sign else f" {cur}"
    return f"{sign}{n:,.0f}{suffix}"


# ---------------------------------------------------------------- word lists

# Searches that almost never become a paying job for a contractor. Whole-word matches.
# Left out on purpose, after a check on real accounts: "what is" (installers' buyers ask "what is
# the best ... system"), "video" (sewer video inspection is a service), "supply" (water supply
# line repair) and "rental" (dumpster rental).
JUNK = {
    "jobs and hiring": ["job", "jobs", "hiring", "salary", "salaries", "career", "careers",
                        "employment", "apprentice", "apprenticeship", "internship", "resume",
                        "indeed", "glassdoor", "wage", "wages"],
    "do it yourself": ["diy", "do it yourself", "how to", "how do i", "youtube", "reddit",
                       "tutorial", "step by step", "kit", "kits"],
    "research and school": ["definition", "meaning", "wiki", "wikipedia", "pdf", "course",
                            "courses", "class", "classes", "school", "training", "certification",
                            "exam"],
    "shopping for parts": ["home depot", "lowes", "lowe's", "amazon", "walmart", "menards",
                           "supplies", "supply store", "supply house", "wholesale", "for sale",
                           "used", "parts", "tools"],
    "wrong meaning": ["makeup", "concealer", "shade", "skincare", "skin", "charity", "grant",
                      "grants", "nonprofit", "apartment", "apartments", "for rent", "airbnb"],
}

SMART_BIDDING = ("maximize conversions", "target cpa", "maximize conversion value", "target roas")
NON_SEARCH = ("display", "performance max", "pmax", "video", "demand gen", "discovery")
# Campaigns Google runs on its own terms: no bid strategy to choose, no impression share, no
# search terms. They count in spend and leads, and are left out of A4, C1, C2 and B4.
SELF_RUN = ("local services", "smart")
# Words that say what a business does, not who it is. A brand search contains the business name
# up to the first of these after a distinctive word: "Mr. Rooter Plumbing of Charlotte" ->
# "mr rooter", "Water Wizards" -> "water wizards". Legal words are dropped first.
LEGAL = {"the", "a", "an", "llc", "inc", "co", "corp", "ltd", "company", "group"}
GENERIC = {
    "of", "and", "pros", "pro", "services", "service", "solutions", "systems", "contractors", "contractor",
    "construction", "home", "homes", "plumbing", "plumber", "plumbers", "foundation",
    "foundations", "repair", "repairs", "waterproofing", "basement", "basements", "roofing",
    "roofers", "roofer", "hvac", "heating", "cooling", "air", "electric", "electrical",
    "electrician", "remodeling", "restoration", "pest", "control", "garage", "door", "doors",
    "fence", "fencing", "junk", "removal", "water", "treatment", "filtration", "drain", "drains",
    "sewer", "crawl", "space", "structural", "concrete", "local", "your",
}


def _words(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").lower().replace("'", ""))).split()


def self_run(camp):
    kind = (camp.get("campaign_type") or "").lower()
    name = (camp.get("campaign") or "").lower().replace(" ", "")
    return any(k in kind for k in SELF_RUN) or name.startswith("localservicescampaign")


def brand_core(business_name):
    """The part of the business name a brand search contains, with spaces taken out so
    "Water Wizards" also matches "waterwizards". None when nothing distinctive is left."""
    words = [w for w in _words(business_name) if w not in LEGAL]
    first = next((i for i, w in enumerate(words) if w not in GENERIC), None)
    if first is None:
        return None
    end = next((j for j in range(first + 1, len(words)) if words[j] in GENERIC), len(words))
    core = "".join(words[:end])
    if len(core) < 4 and end < len(words):  # "ABC Foundation Repair" -> "abc foundation"
        core += words[end]
    return core if len(core) >= 4 else None


def brand_campaigns(campaigns):
    """Search campaigns whose name says brand: their searches are people asking for you."""
    return {c.get("campaign", "").strip().lower() for c in campaigns
            if "brand" in _words(c.get("campaign"))
            and not any(n in (c.get("campaign_type") or "").lower() for n in NON_SEARCH)}


def is_brand(term, core, brand_names):
    if core and core in "".join(_words(term.get("search_term"))):
        return True
    return (term.get("campaign") or "").strip().lower() in brand_names


def junk_reason(term):
    t = " " + re.sub(r"[^a-z0-9' ]", " ", term.lower()) + " "
    t = re.sub(r"\s+", " ", t)
    for reason, words in JUNK.items():
        for w in words:
            if f" {w} " in t:
                return reason, w
    return None, None


# ---------------------------------------------------------------- the checks

class Check:
    def __init__(self, cid, group, title, weight):
        self.id, self.group, self.title, self.weight = cid, group, title, weight
        self.status = "unknown"   # pass | partial | fail | unknown
        self.points = 0.0
        self.finding = ""
        self.fix = ""
        self.monthly_waste = 0.0

    def set(self, status, finding, fix="", share=None, waste=0.0):
        self.status = status
        self.points = {"pass": 1.0, "partial": 0.5, "fail": 0.0}.get(status, 0.0) * self.weight
        if share is not None and status != "unknown":
            self.points = round(self.weight * max(0.0, min(1.0, share)), 1)
        self.finding, self.fix, self.monthly_waste = finding, fix, waste
        return self

    def as_dict(self):
        return {k: getattr(self, k) for k in
                ("id", "group", "title", "weight", "status", "points", "finding", "fix",
                 "monthly_waste")}


def answer(answers, key):
    v = answers.get(key)
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip().lower()
        if v in ("", "unsure", "not sure", "don't know", "dont know", "unknown", "?"):
            return None
    return v


def yes(v):
    return v in (True, "yes", "y", "true", 1)


def run_checks(campaigns, terms, answers, days):
    cur = next((c.get("currency") for c in campaigns if c.get("currency")), "USD") or "USD"
    month = 30.0 / days if days else 1.0

    live = [c for c in campaigns if (num(c.get("cost")) or 0) > 0]
    spend = sum(num(c.get("cost")) or 0 for c in live)
    clicks = sum(num(c.get("clicks")) or 0 for c in live)
    conv = sum(num(c.get("conversions")) or 0 for c in live)
    term_spend = sum(num(t.get("cost")) or 0 for t in terms)
    # Campaigns we can judge on bidding and reach, and the spend a search terms report can show.
    tuned = [c for c in live if not self_run(c)]
    # Search campaigns, plus any other campaign the search terms report itself names
    # (Performance Max terms appear there in newer exports).
    in_report = {(t.get("campaign") or "").strip().lower() for t in terms}
    searchable = sum(num(c.get("cost")) or 0 for c in tuned
                     if not any(n in (c.get("campaign_type") or "").lower() for n in NON_SEARCH)
                     or (c.get("campaign") or "").strip().lower() in in_report)
    coverage = min(1.0, term_spend / searchable) if searchable > 0 else None
    seen = (f"{{:.0%}} of the search spend this report shows; it shows {coverage:.0%} of your "
            "search spend" if coverage is not None and coverage < 0.95 else "{:.0%} of search spend")
    core = brand_core(answers.get("business_name") if isinstance(answers.get("business_name"), str) else "")
    brand_names = brand_campaigns(campaigns)
    brand = [t for t in terms if is_brand(t, core, brand_names)]
    brand_ids = {id(t) for t in brand}

    checks = []
    add = lambda *a: checks.append(Check(*a)) or checks[-1]

    # A. Can you measure leads?
    c = add("A1", "Measuring leads", "Leads are being recorded as conversions", 12)
    if spend <= 0:
        c.set("unknown", "No spend in the campaigns report, so tracking can't be judged.",
              "Export the campaigns report for a period when ads were running.")
    elif conv <= 0:
        c.set("fail", f"{money(spend, cur)} spent and 0 conversions recorded.",
              "Set up conversion tracking for calls and form fills before spending another dollar. "
              "Without it, Google is bidding blind.", waste=0)
    else:
        c.set("pass", f"{conv:,.0f} conversions recorded on {money(spend, cur)} of spend.")

    c = add("A2", "Measuring leads", "Phone calls are counted as leads", 8)
    v = answer(answers, "calls_tracked")
    if v is None:
        c.set("unknown", "Not answered.", "Check Goals > Conversions for a 'Calls from ads' and a "
              "'Calls from website' action. Most contractor leads are calls.")
    elif yes(v):
        c.set("pass", "Calls are tracked as conversions.")
    else:
        c.set("fail", "Calls are not tracked, so most of your leads are invisible to Google.",
              "Add call tracking: a call asset with call reporting, plus a forwarding number on the "
              "website through Google's call tracking or a call-tracking tool.")

    c = add("A3", "Measuring leads", "Clicks turn into leads at a healthy rate", 4)
    if clicks <= 0 or conv <= 0:
        c.set("unknown", "Not enough clicks or conversions to judge.")
    else:
        rate = conv / clicks
        if rate >= 0.05:
            c.set("pass", f"{rate:.1%} of clicks became a lead.")
        elif rate >= 0.02:
            c.set("partial", f"{rate:.1%} of clicks became a lead. Good contractor pages reach 5% or more.",
                  "Send ads to a page about that one service, with the phone number and a short "
                  "form at the top.")
        else:
            c.set("fail", f"Only {rate:.1%} of clicks became a lead.",
                  "Either calls aren't counted or the landing page loses people. Fix tracking first, "
                  "then the page.")

    c = add("A4", "Measuring leads", "The bidding strategy fits the amount of data", 4)
    problems = []
    skipped = [cp for cp in live if self_run(cp)]
    for camp in tuned:
        bs = (camp.get("bid_strategy") or "").lower()
        cc = num(camp.get("conversions")) or 0
        if not bs:
            continue
        if "target impression share" in bs:
            problems.append(f"'{camp.get('campaign')}' pays for visibility, not leads")
        elif any(s in bs for s in SMART_BIDDING) and cc * month < 15:
            got = f"only {cc:,.0f} conversions" if cc else "no conversions"
            problems.append(f"'{camp.get('campaign')}' uses {camp.get('bid_strategy')} with {got} "
                            "in the period, too few to learn from")
    note = (f" {len(skipped)} Local Services or Smart campaign{'' if len(skipped) == 1 else 's'} "
            "left out: Google sets {} bidding.".format("its" if len(skipped) == 1 else "their")
            if skipped else "")
    if not tuned:
        c.set("unknown", "Only Local Services or Smart campaigns, where Google sets the bidding." + note)
    elif not any(camp.get("bid_strategy") for camp in tuned):
        c.set("unknown", "The campaigns report has no 'Bid strategy type' column.",
              "Add that column to the export to check this.")
    elif problems:
        c.set("partial" if len(problems) < len(tuned) else "fail", "; ".join(problems[:3]) + "." + note,
              "Use Maximize clicks with a bid cap, or Manual CPC, until a campaign records about "
              "15 leads a month; then switch to Maximize conversions.")
    else:
        c.set("pass", "Each campaign's bidding fits its conversion volume." + note)

    c = add("A5", "Measuring leads", "Each lead costs less than it earns", 8)
    job = num(answer(answers, "average_job_value"))
    close = num(answer(answers, "close_rate_percent"))
    margin = num(answer(answers, "gross_margin_percent"))
    if None in (job, close, margin) or conv <= 0:
        c.set("unknown", "Needs the average job value, close rate and gross margin, plus recorded leads.",
              "Work out the most you can pay for a lead: average job value x gross margin x close rate.")
    else:
        close, margin = close / 100.0, margin / 100.0
        breakeven = job * margin * close
        cpl = spend / conv
        if cpl <= breakeven * 0.7:
            c.set("pass", f"A lead costs {money(cpl, cur)}; you break even at {money(breakeven, cur)}.")
        elif cpl <= breakeven:
            c.set("partial", f"A lead costs {money(cpl, cur)}, close to your break-even of "
                  f"{money(breakeven, cur)}.", "Cut wasted searches (below) to bring the cost per lead down.")
        else:
            c.set("fail", f"A lead costs {money(cpl, cur)} but you only break even at "
                  f"{money(breakeven, cur)}. Every lead loses money on the first job.",
                  "Stop the worst campaigns, cut wasted searches, and fix the landing page before "
                  "raising budget.")

    # B. Wasted spend
    zero = [t for t in terms if (num(t.get("conversions")) or 0) <= 0]
    avg_cpc = (term_spend / sum(num(t.get("clicks")) or 0 for t in terms)) if terms and any(
        num(t.get("clicks")) for t in terms) else 0
    floor = max(20.0, 3 * avg_cpc)
    dead = [t for t in zero if (num(t.get("cost")) or 0) >= floor and id(t) not in brand_ids]
    dead_spend = sum(num(t.get("cost")) or 0 for t in dead)

    c = add("B1", "Wasted spend", "Little spend on searches that never produce a lead", 12)
    if term_spend <= 0:
        c.set("unknown", "The search terms report has no spend.")
    elif conv <= 0:
        c.set("unknown", "No conversions are recorded, so wasted searches can't be told apart from "
              "good ones yet. Fix tracking first.")
    else:
        share = dead_spend / term_spend
        top = sorted(dead, key=lambda t: -(num(t.get("cost")) or 0))[:5]
        names = ", ".join(f"\"{t.get('search_term')}\" ({money(num(t.get('cost')) or 0, cur)})" for t in top)
        finding = (f"{money(dead_spend, cur)} ({seen.format(share)}) went to {len(dead)} searches "
                   f"that each cost {money(floor, cur)} or more and produced no lead"
                   + (f", led by {names}." if names else ".")
                   + (" Searches for your own name are left out." if brand else ""))
        status = "pass" if share < 0.10 else "partial" if share < 0.25 else "fail"
        c.set(status, finding, "Review these searches weekly. Add the ones that will never be a job as "
              "negative keywords; for the rest, tighten the keyword or the ad.",
              waste=dead_spend * month)

    junk = []
    for t in terms:
        reason, word = junk_reason(t.get("search_term", ""))
        if reason:
            junk.append((t, reason, word))
    junk_spend = sum(num(t.get("cost")) or 0 for t, _, _ in junk)

    c = add("B2", "Wasted spend", "No spend on job seekers, DIY and shoppers", 8)
    if term_spend <= 0:
        c.set("unknown", "The search terms report has no spend.")
    else:
        share = junk_spend / term_spend
        kinds = {}
        for t, reason, _ in junk:
            kinds[reason] = kinds.get(reason, 0) + (num(t.get("cost")) or 0)
        detail = ", ".join(f"{k} {money(v, cur)}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
        if not junk:
            c.set("pass", "No spend on job, DIY, school or shopping searches.")
        else:
            status = "pass" if share < 0.02 else "partial" if share < 0.08 else "fail"
            c.set(status, f"{money(junk_spend, cur)} ({share:.0%}) went to {len(junk)} searches from people "
                  f"who will never hire you: {detail}.",
                  "Add a negative keyword list with words like jobs, hiring, salary, diy, how to, "
                  "youtube, home depot and course, and apply it to every campaign.",
                  waste=junk_spend * month)

    c = add("B3", "Wasted spend", "Bad searches are already being blocked", 4)
    if not terms:
        c.set("unknown", "No search terms report.")
    else:
        open_junk = [t for t, _, _ in junk if "excluded" not in (t.get("added_excluded") or "").lower()]
        if not junk:
            c.set("pass", "Nothing obviously bad left unblocked.")
        elif len(open_junk) == 0:
            c.set("pass", "Every bad search found has been excluded.")
        else:
            c.set("partial" if len(open_junk) <= 5 else "fail",
                  f"{len(open_junk)} bad searches are still not excluded, e.g. "
                  + ", ".join(f"\"{t.get('search_term')}\"" for t in open_junk[:4]) + ".",
                  "Add them as negative keywords today; it takes ten minutes.")

    c = add("B4", "Wasted spend", "Broad match is kept on a short leash", 4)
    typed = [t for t in terms if t.get("match_type")]
    if not typed:
        c.set("unknown", "The search terms report has no match type column.")
    else:
        broad = sum(num(t.get("cost")) or 0 for t in typed if "broad" in t["match_type"].lower())
        total = sum(num(t.get("cost")) or 0 for t in typed) or 1
        share = broad / total
        smart = any(any(s in (cp.get("bid_strategy") or "").lower() for s in SMART_BIDDING)
                    and (num(cp.get("conversions")) or 0) * month >= 30 for cp in tuned)
        if share < 0.5 or smart:
            c.set("pass", f"{share:.0%} of search spend came through broad match"
                  + (", backed by enough conversions for smart bidding." if smart and share >= 0.5 else "."))
        else:
            c.set("partial" if share < 0.8 else "fail",
                  f"{share:.0%} of search spend came through broad match without enough conversion data "
                  "to steer it.", "Use phrase and exact match for your main services until the account "
                  "records about 30 leads a month.")

    c = add("B5", "Wasted spend", "Display, video and Performance Max earn their keep", 4)
    other = [cp for cp in live if any(n in (cp.get("campaign_type") or "").lower() for n in NON_SEARCH)]
    idle_nonsearch = sum(num(cp.get("cost")) or 0 for cp in other if (num(cp.get("conversions")) or 0) <= 0)
    if not any(cp.get("campaign_type") for cp in live):
        c.set("unknown", "The campaigns report has no 'Campaign type' column.")
    elif not other:
        c.set("pass", "All spend is on Search, where people are looking for a contractor now.")
    else:
        idle = [cp for cp in other if (num(cp.get("conversions")) or 0) <= 0]
        idle_spend = sum(num(cp.get("cost")) or 0 for cp in idle)
        if not idle:
            c.set("pass", "Non-search campaigns are producing leads.")
        else:
            c.set("fail", f"{money(idle_spend, cur)} went to {len(idle)} display, video or Performance Max "
                  f"campaign{'' if len(idle) == 1 else 's'} with no leads.",
                  f"Pause {'it' if len(idle) == 1 else 'them'} and move the budget to your best Search "
                  "campaign until tracking proves they work.", waste=idle_spend * month)

    # C. Reach
    def weighted(field):
        pairs = [(num(cp.get(field)), num(cp.get("cost")) or 0) for cp in tuned]
        pairs = [(v, w) for v, w in pairs if v is not None]
        if not pairs or sum(w for _, w in pairs) <= 0:
            return None
        return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)

    c = add("C1", "Reach", "Your best campaigns aren't running out of budget", 6)
    lb = weighted("lost_budget")
    if lb is None:
        c.set("unknown", "The campaigns report has no 'Search lost IS (budget)' column.",
              "Add that column to the export to check this.")
    elif conv > 0:
        # Judge the campaigns that bring the cheapest leads, not the account as a whole: a budget
        # cap on a campaign with dear leads is not the first thing to fix.
        cpl = spend / conv
        rows = []
        for cp in tuned:
            cc, cost, lost = num(cp.get("conversions")) or 0, num(cp.get("cost")) or 0, num(cp.get("lost_budget"))
            if lost is not None:
                rows.append((cp.get("campaign"), cost, cc, lost))
        best = [r for r in rows if r[2] > 0 and r[1] / r[2] <= cpl]
        held = sorted((r for r in best if r[3] >= 0.10), key=lambda r: -r[3])
        others = sorted((r for r in rows if r[3] >= 0.10 and r not in best), key=lambda r: -r[3])
        if held:
            worst = max(r[3] for r in held)
            c.set("partial" if worst < 0.30 else "fail",
                  "; ".join(f"'{n}' brings leads at {money(cost / cc, cur)} each (account average "
                            f"{money(cpl, cur)}) but missed {lost:.0%} of searches because its budget ran out"
                            for n, cost, cc, lost in held[:2]) + ".",
                  "Move money from wasted searches (above) and from campaigns with dearer leads into "
                  f"{'it' if len(held) == 1 else 'them'}, before adding new budget.")
        elif others:
            n, cost, cc, lost = others[0]
            dear = (f"its leads cost {money(cost / cc, cur)} each against {money(cpl, cur)} on average"
                    if cc else f"it recorded no leads on {money(cost, cur)}")
            c.set("pass", f"The campaigns with the cheapest leads aren't held back by budget. '{n}' missed "
                  f"{lost:.0%} of searches for lack of budget, but {dear}, so more budget there isn't "
                  "the first fix.")
        else:
            c.set("pass", f"Ads missed {lb:.0%} of searches for lack of budget.")
    elif lb < 0.10:
        c.set("pass", f"Ads missed {lb:.0%} of searches for lack of budget.")
    else:
        c.set("partial", f"Ads missed {lb:.0%} of searches for lack of budget, but with no leads "
              "recorded, more budget would only buy more unmeasured clicks.", "Fix tracking first.")

    c = add("C2", "Reach", "Ads show high enough to be seen", 4)
    lr = weighted("lost_rank")
    if lr is None:
        c.set("unknown", "The campaigns report has no 'Search lost IS (rank)' column.")
    elif lr < 0.30:
        c.set("pass", f"Ads missed {lr:.0%} of searches because of low ad rank.")
    else:
        c.set("partial" if lr < 0.6 else "fail", f"Ads missed {lr:.0%} of searches because of low ad rank.",
              "Tighter ad groups, ads that repeat the service and city, and a faster landing page "
              "raise ad rank without raising bids.")

    c = add("C3", "Reach", "Ads only show to people in your service area", 6)
    v = answer(answers, "location_setting")
    if v is None:
        c.set("unknown", "Not answered.", "In each campaign's Settings > Locations > Location options, "
              "choose 'Presence: people in or regularly in your included locations'.")
    elif "interest" in str(v):
        c.set("fail", "Location is set to 'Presence or interest', so people outside your area see your ads.",
              "Switch to 'Presence: people in or regularly in your included locations'.")
    else:
        c.set("pass", "Ads target people who are in your service area.")

    # D. Turning clicks into jobs
    c = add("D1", "Clicks into jobs", "Ads go to a page built for that service", 6)
    v = answer(answers, "landing_page")
    if v is None:
        c.set("unknown", "Not answered.", "Send each service's ads to a page about that service, with "
              "the phone number, reviews and a short form at the top.")
    elif "home" in str(v):
        c.set("fail", "Ads send people to the home page.", "Build one landing page per main service. "
              "It usually doubles the share of clicks that call.")
    else:
        c.set("pass", "Ads go to dedicated service pages.")

    c = add("D2", "Clicks into jobs", "Every search ad has a call button", 4)
    v = answer(answers, "call_assets")
    if v is None:
        c.set("unknown", "Not answered.", "Add a call asset under Ads > Assets to every search campaign.")
    elif yes(v):
        c.set("pass", "Call assets are on.")
    else:
        c.set("fail", "No call button on the ads.", "Add a call asset to every search campaign, scheduled "
              "for the hours someone answers.")

    c = add("D3", "Clicks into jobs", "Ads run when someone can answer the phone", 4)
    v = answer(answers, "schedule_matches_phones")
    if v is None:
        c.set("unknown", "Not answered.")
    elif yes(v):
        c.set("pass", "The ad schedule matches the hours calls are answered.")
    else:
        c.set("fail", "Ads run when nobody answers.", "Set an ad schedule for staffed hours, or send "
              "after-hours callers to an answering service.")

    c = add("D4", "Clicks into jobs", "Leads get a reply within 5 minutes", 6)
    mins = num(answer(answers, "reply_minutes"))
    if mins is None:
        c.set("unknown", "Not answered.")
    elif mins <= 5:
        c.set("pass", f"Form leads get a reply in about {mins:.0f} minutes.")
    elif mins <= 60:
        c.set("partial", f"Form leads wait about {mins:.0f} minutes.", "Reply within 5 minutes: an "
              "instant text back is the cheapest way to win more of the leads you already pay for.")
    else:
        c.set("fail", f"Form leads wait about {mins:.0f} minutes; most will have called a competitor.",
              "Set up an instant text reply and a call-back within 5 minutes.")

    c = add("D5", "Clicks into jobs", "Your reviews win the click", 4)
    rating = num(answer(answers, "google_rating"))
    count = num(answer(answers, "google_review_count"))
    if rating is None or count is None:
        c.set("unknown", "Not answered.")
    elif rating >= 4.6 and count >= 50:
        c.set("pass", f"{rating:.1f} stars from {count:.0f} reviews.")
    elif rating >= 4.3:
        c.set("partial", f"{rating:.1f} stars from {count:.0f} reviews.", "Ask every finished job for a "
              "review by text the same day; aim for 50+ reviews at 4.6 or higher.")
    else:
        c.set("fail", f"{rating:.1f} stars from {count:.0f} reviews.", "Fix the reviews before raising "
              "ad spend; low ratings cut both clicks and calls.")

    wasted = {id(t): t for t in dead} if conv > 0 else {}
    for t, _, _ in junk:
        if (num(t.get("conversions")) or 0) <= 0:
            wasted[id(t)] = t
    waste = sum(num(t.get("cost")) or 0 for t in wasted.values()) + idle_nonsearch
    return checks, {"currency": cur, "spend": spend, "clicks": clicks, "conversions": conv,
                    "days": days, "campaigns": len(live), "search_terms": len(terms),
                    "monthly_waste": round(waste * month),
                    "search_terms_spend": round(term_spend, 2),
                    "search_terms_coverage": round(coverage, 3) if coverage is not None else None,
                    "brand_searches": len(brand),
                    "brand_spend": round(sum(num(t.get("cost")) or 0 for t in brand), 2),
                    "self_run_campaigns": len(live) - len(tuned)}


# When leads aren't being measured, a high score on the rest would mislead: the score is held
# below the band it would otherwise reach, and the report says why.
CAPS = (("A1", 39, "no conversions are recorded, so nothing shows whether the ads bring work"),
        ("A3", 69, "so few clicks become a recorded lead that either leads go uncounted or the "
                   "landing page loses them"))


def summarise(checks):
    scored = [c for c in checks if c.status != "unknown"]
    possible = sum(c.weight for c in scored)
    got = sum(c.points for c in scored)
    score = round(100 * got / possible) if possible else 0
    by_id = {c.id: c for c in checks}
    held = None
    for cid, ceiling, why in CAPS:
        if by_id.get(cid) and by_id[cid].status == "fail" and score > ceiling:
            score, held = ceiling, {"check": cid, "at": ceiling, "why": why}
            break
    band = ("Strong" if score >= 80 else "A few leaks" if score >= 60
            else "Leaking money" if score >= 40 else "Big leaks")
    # With no conversions recorded nothing else can be judged properly, so tracking leads.
    lost = sorted((c for c in scored if c.points < c.weight),
                  key=lambda c: (not (c.id == "A1" and c.status == "fail"),
                                 -(c.monthly_waste), -(c.weight - c.points)))
    return {"score": score, "band": band, "checked": len(scored), "total": len(checks),
            "held": held, "top_fixes": [c.id for c in lost[:5]]}


# ---------------------------------------------------------------- output

ICON = {"pass": "Pass", "partial": "Partly", "fail": "Fail", "unknown": "Not checked"}


def markdown(checks, facts, summary):
    cur = facts["currency"]
    by_id = {c.id: c for c in checks}
    out = [f"# Google Ads audit: {summary['score']}/100, {summary['band']}", ""]
    left = summary["total"] - summary["checked"]
    out.append(f"Based on {money(facts['spend'], cur)} of spend, {facts['clicks']:,.0f} clicks and "
               f"{facts['conversions']:,.0f} recorded leads over {facts['days']} days, across "
               f"{facts['campaigns']} campaigns and {facts['search_terms']} search terms. "
               + (f"{summary['checked']} of {summary['total']} checks could be scored; the other {left} "
                  f"need{'s' if left == 1 else ''} an answer or a column in the export." if left
                  else f"All {summary['total']} checks could be scored."))
    if summary.get("held"):
        h = summary["held"]
        out += ["", f"The score is held at {h['at']} because {h['why']} (check {h['check']}). "
                "Fix that first: until leads are counted, the other results can't be trusted."]
    cov = facts.get("search_terms_coverage")
    if cov is not None and cov < 0.6:
        out += ["", f"The search terms report shows only {cov:.0%} of your search spend. Google hides "
                "searches made by only a few people, so the search checks below cover that part only."]
    if facts.get("brand_spend"):
        out += ["", f"Searches for your own business name ({money(facts['brand_spend'], cur)}, "
                f"{facts['brand_searches']} searches) are people looking for you, so they are not counted "
                "as waste."]
    if facts["monthly_waste"] > 0:
        out += ["", f"**Spend that produced no leads: about {money(facts['monthly_waste'], cur)} a month**, "
                "on searches and campaigns found in checks B1, B2 and B5 (each search counted once)."]
    n_fixes = len(summary["top_fixes"])
    out += ["", (f"## The {n_fixes} fix{'' if n_fixes == 1 else 'es'} worth the most" if n_fixes
                 else "## Nothing to fix in the checks that could be scored"), ""]
    for n, cid in enumerate(summary["top_fixes"], 1):
        c = by_id[cid]
        out.append(f"{n}. **{c.id} {c.title}: {ICON[c.status]}.** {c.finding} {c.fix}".rstrip())
    out += ["", "## Every check", "", "| Check | Result | Points | What we found |",
            "| --- | --- | --- | --- |"]
    for c in checks:
        pts = f"{c.points:g}/{c.weight}" if c.status != "unknown" else f"-/{c.weight}"
        out.append(f"| {c.id} {c.title} | {ICON[c.status]} | {pts} | {c.finding} |")
    out += ["", "---", "",
            "This audit was made by the free Home Services Google Ads Audit skill from WebnWell. "
            "It read only the files you gave it. If you'd like a person to look at your account, "
            f"your website and your local competitors, here's how: {CTA_URL}"]
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--campaigns", required=True, help="Campaigns report exported from Google Ads (CSV)")
    p.add_argument("--search-terms", required=True, help="Search terms report exported from Google Ads (CSV)")
    p.add_argument("--answers", help="JSON file with the owner's answers (see examples/answers.json)")
    p.add_argument("--days", type=int, default=30, help="Days covered by the exports (default 30)")
    p.add_argument("--format", choices=("markdown", "json"), default="markdown")
    a = p.parse_args(argv)

    campaigns, _ = read_report(a.campaigns, "campaign")
    terms, _ = read_report(a.search_terms, "search_term")
    answers = {}
    if a.answers:
        with open(a.answers, encoding="utf-8") as fh:
            answers = json.load(fh)
    checks, facts = run_checks(campaigns, terms, answers, a.days)
    summary = summarise(checks)
    if a.format == "json":
        json.dump({"version": SKILL_VERSION, "facts": facts, "summary": summary,
                   "checks": [c.as_dict() for c in checks], "cta": CTA_URL}, sys.stdout, indent=2)
        print()
    else:
        print(markdown(checks, facts, summary))


if __name__ == "__main__":
    main()
