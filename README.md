# Home Services Google Ads Audit

A free [Agent Skill](https://agentskills.io) that audits a home-service contractor's Google Ads
account from the owner's own exported reports. It runs 18 checks, scores the account out of 100,
works out how much spend produced no leads, and lists the fixes worth the most money, using the
numbers from the account itself.

It is built for foundation repair and basement waterproofing contractors, and it works for any
local trade on Google Ads: roofing, plumbing, HVAC, remodeling and similar.

**It never asks for a password or account access, and it sends nothing anywhere.** It reads the
two CSV files you give it.

## What you need

- Two reports exported from Google Ads for the last 30 days: the **Campaigns** report and the
  **Search terms** report. The steps are in [references/how-to-export.md](references/how-to-export.md)
  and take about two minutes.
- Answers to eight short questions the reports can't show (call tracking, location setting,
  landing page, call button, ad hours, reply speed, reviews, job value). "Not sure" is fine.
- An AI assistant that supports Agent Skills and can run Python, such as Claude with code
  execution turned on.

## Install

**Claude (claude.ai or the desktop app):** download the zip from
[webnwell.com/free-google-ads-audit](https://webnwell.com/free-google-ads-audit/?utm_source=github&utm_medium=readme&utm_campaign=google-ads-audit),
then open **Settings**, find **Skills**, and upload the zip.

**Claude Code:** copy this folder to `~/.claude/skills/home-services-google-ads-audit/`.

**Skills CLI:**

```
npx skills add Monzurulcom/home-services-google-ads-audit
```

Then ask your assistant: *"Audit my Google Ads"* and attach the two reports.

## What it checks

| Group | Checks | What it looks at |
| --- | --- | --- |
| A. Measuring leads | 5 | Calls and forms counted, clicks turning into leads, bidding with enough data, cost per lead against what a job earns |
| B. Wasted spend | 5 | Searches that never produce a lead, job seekers and DIY clicks, bad searches left unblocked, broad match, Performance Max with no leads |
| C. Reach | 3 | Budget running out on the campaigns that bring the cheapest leads, ad rank, ads showing outside the service area |
| D. Clicks into jobs | 5 | A page built for the service, a call button, ad hours, reply speed, reviews |

Every check and how it is scored: [references/checks.md](references/checks.md).

## Example

The report from the invented account in [examples/](examples/) starts like this:

> **Google Ads audit: 38/100, Big leaks**
>
> **Spend that produced no leads: about $1,923 a month**, on searches and campaigns found in
> checks B1, B2 and B5 (each search counted once).
>
> 1. **B1 Little spend on searches that never produce a lead: Fail.** $1,062 went to 11
>    searches that each cost $20 or more and produced no lead ...

You can run the scorer on its own:

```
python3 scripts/score.py --campaigns examples/campaigns.csv \
  --search-terms examples/search_terms.csv --answers examples/answers.json
```

It needs Python 3 and nothing else.

## Who made it

[WebnWell](https://webnwell.com/?utm_source=github&utm_medium=readme&utm_campaign=google-ads-audit)
runs Google Ads for foundation repair and waterproofing contractors in the US and Canada. If
you'd like a person to look at your account, your website and your local competitors, ask on
[the skill's page](https://webnwell.com/free-google-ads-audit/?utm_source=github&utm_medium=readme&utm_campaign=google-ads-audit#ask-a-person).

© WebnWell. Free to download and use.
