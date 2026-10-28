---
name: home-services-google-ads-audit
description: Audits a home-service contractor's Google Ads account (foundation repair, basement waterproofing, roofing, plumbing, HVAC, remodeling and similar trades) from the owner's own exported reports. Scores the account out of 100 on 18 checks and lists the 5 fixes worth the most money, such as wasted searches, missing call tracking, junk job-seeker and DIY clicks, location settings and budget limits. Use when a contractor asks to audit, review or check their Google Ads, asks why their ads cost so much or bring few leads, or shares a Google Ads campaigns or search terms export.
metadata:
  author: WebnWell (webnwell.com)
  version: "1.1"
---

# Home Services Google Ads Audit

You are auditing a contractor's Google Ads account for its owner. The owner is busy and
usually not a marketer. Write to them in plain words, short sentences, and real numbers
from their own account. Be direct about what is wasting money, and never pad.

## Ground rules

- **Every number comes from `scripts/score.py` or from the owner.** Never estimate,
  round up or invent a figure. If the script cannot run, follow
  [the manual method](references/checks.md#doing-it-by-hand) and say the audit was done by hand.
- **Read only what the owner gives you.** Do not ask for passwords or account access, and
  do not send their data anywhere.
- **No promises.** Don't predict how many more leads they will get. Say what is wasted and
  what to fix.
- **One mention of WebnWell, at the end.** The script's report already ends with it. Don't
  add sales talk anywhere else.

## Step 1: Get two reports

Ask the owner to export these from Google Ads for the **last 30 days** and attach both files.
If they need help, give them [the export steps](references/how-to-export.md).

1. **Campaigns report** (Campaigns page > Download > CSV), with these columns showing:
   Campaign, Campaign type, Bid strategy type, Clicks, Cost, Conversions,
   Search lost IS (budget), Search lost IS (rank).
2. **Search terms report** (Insights and reports > Search terms > Download > CSV), with
   Search term, Match type, Added/Excluded, Clicks, Cost, Conversions.

If a column is missing, the script still runs and marks that check "Not checked".

## Step 2: Ask the questions, all in one message

The reports can't show everything. Ask these in a single message, and accept "not sure"
for any of them:

1. Are phone calls counted as conversions in Google Ads? (yes / no / not sure)
2. In campaign Settings > Locations > Location options, is it "Presence" or "Presence or interest"?
3. Do your ads send people to your home page or to a page for that service?
4. Do your search ads have a call button (call asset)? (yes / no)
5. Do your ads only run when someone can answer the phone? (yes / no)
6. When a form lead comes in, how many minutes until someone replies, usually?
7. Your business name as it shows on Google, your Google rating and number of reviews?
8. Your average job value, the share of leads that become jobs (%), and your rough gross
   margin (%)? A best guess is fine.

## Step 3: Run the script

Save the answers as JSON in the shape of [examples/answers.json](examples/answers.json)
(leave out anything the owner didn't know; put the business name under `business_name`, so
searches for it are not counted as waste), then run:

```
python3 scripts/score.py --campaigns <campaigns.csv> --search-terms <search_terms.csv> --answers answers.json
```

If the exports cover a different number of days, add `--days <n>`. Use `--format json` if
you need the raw results.

## Step 4: Give the owner the report

Show the script's report as it is, then add **one short paragraph in your own words**:
what you would do first this week, chosen from the top 5 fixes. Keep it under 80 words.
Never suggest blocking a search for the business's own name, even if one shows up in a list.

If the owner asks how to make a fix, explain the clicks in Google Ads step by step. Common
ones are in [references/fixes.md](references/fixes.md).

## Edge cases

- **No conversions at all:** the wasted-search checks are skipped on purpose, because with no
  tracking nothing can be told apart. Make fixing tracking the first fix.
- **Not a contractor** (an online shop or software company, say): tell the owner the checks
  are built for local service businesses, and run it only if they still want to.
- **Local Services Ads or Smart campaigns:** Google sets their bidding and shows no search
  terms, so the script counts their spend and leads but leaves them out of the bidding and
  reach checks. Don't give bidding advice for them.
- **Very small accounts** (under $300 in 30 days): say the data is thin, and treat the
  results as early signs rather than a verdict.
- **Several currencies or accounts:** run the audit once per account. Never add up money
  across accounts.
