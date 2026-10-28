# The 18 checks

Each check has a weight. The score is the points earned out of the weight of the checks that
could be scored, so a check left "Not checked" neither helps nor hurts. "Partly" earns half the
weight.

| Group | Check | Weight | From | Pass | Partly | Fail |
| --- | --- | --- | --- | --- | --- | --- |
| Measuring leads | A1 Leads are recorded as conversions | 12 | Campaigns | Any conversions | | Spend and 0 conversions |
| Measuring leads | A2 Phone calls are counted as leads | 8 | Question 1 | Yes | | No |
| Measuring leads | A3 Clicks turn into leads | 4 | Campaigns | 5% or more | 2% to 5% | Under 2% |
| Measuring leads | A4 Bidding fits the data | 4 | Campaigns | Every campaign fits | Some don't | None fit |
| Measuring leads | A5 A lead costs less than it earns | 8 | Campaigns, question 8 | Under 70% of break-even | Up to break-even | Over break-even |
| Wasted spend | B1 Little spend on searches that never produce a lead | 12 | Search terms | Under 10% of the spend the report shows | 10% to 25% | Over 25% |
| Wasted spend | B2 Job seekers, DIY and shoppers | 8 | Search terms | Under 2% of spend | 2% to 8% | Over 8% |
| Wasted spend | B3 Bad searches already blocked | 4 | Search terms | All excluded | Up to 5 open | More than 5 open |
| Wasted spend | B4 Broad match on a short leash | 4 | Search terms, campaigns | Under 50% broad, or 30+ leads a month on smart bidding | 50% to 80% | Over 80% |
| Wasted spend | B5 Display, video and Performance Max earn their keep | 4 | Campaigns | None, or they produce leads | | Spend with no leads |
| Reach | C1 The cheapest-lead campaigns don't run out of budget | 6 | Campaigns | They lose under 10% to budget | 10% to 30% | Over 30% |
| Reach | C2 Ads show high enough | 4 | Campaigns | Under 30% lost to rank | 30% to 60% | Over 60% |
| Reach | C3 Ads only show in the service area | 6 | Question 2 | Presence | | Presence or interest |
| Clicks into jobs | D1 A page built for the service | 6 | Question 3 | Service page | | Home page |
| Clicks into jobs | D2 A call button on every search ad | 4 | Question 4 | Yes | | No |
| Clicks into jobs | D3 Ads run when the phone is answered | 4 | Question 5 | Yes | | No |
| Clicks into jobs | D4 Replies within 5 minutes | 6 | Question 6 | 5 minutes or less | Up to 60 minutes | Over 60 minutes |
| Clicks into jobs | D5 Reviews win the click | 4 | Question 7 | 4.6+ stars and 50+ reviews | 4.3+ stars | Under 4.3 |

## Definitions

- **A search that never produces a lead (B1):** a search term with no conversions that cost at
  least $20, or three times the average cost per click if that is higher, and that is not a
  search for the business itself. This is only judged when the account records conversions at all.
- **Brand searches:** a search served by a Search campaign with "brand" in its name, or one that
  contains the business name (from the answers, up to the first trade word: "Mr. Rooter Plumbing
  of Charlotte" gives "mr rooter"). People asking for the business by name are not waste, so B1
  leaves them out; the report shows their spend on its own line. A brand search with a junk word
  ("acme plumbing jobs") still counts in B2 and B3.
- **What the search terms report shows:** Google hides searches made by only a few people, so the
  report covers part of the spend. B1 says what share of the visible spend was wasted and how much
  of the Search campaigns' spend the report shows; under 60%, the report says so at the top.
- **Local Services and Smart campaigns:** Google sets their bidding and shows no impression share
  or search terms. Their spend and leads count; A4, B4, C1 and C2 leave them out.
- **The cheapest-lead campaigns (C1):** campaigns whose cost per lead is at or below the account's.
  A campaign with dearer leads that runs out of budget is named, but it doesn't fail the check:
  more budget there isn't the first fix.
- **Junk searches (B2):** search terms containing words from five lists: jobs and hiring (job,
  hiring, salary, career), do it yourself (diy, how to, youtube, kit), research and school
  (definition, course, training, pdf), shopping for parts (home depot, lowes, supplies, supply
  store, used) and wrong meaning (makeup, shade, skin, apartment, for rent, charity). Questions
  like "what is the best ... system" are buyers for an installer, so they are not on the list. The full lists are in
  `scripts/score.py`.
- **Break-even cost per lead (A5):** average job value x gross margin x close rate. Above it, the
  first job from each lead loses money.
- **Smart bidding (A4, B4):** Maximize conversions, Target CPA, Maximize conversion value or Target
  ROAS. It needs about 15 leads a month per campaign to learn, and about 30 to steer broad match.
- **Money that produced no leads:** the spend on B1 and B2 searches with no conversions, plus
  B5 campaigns with no conversions, each counted once, scaled to 30 days.

## Doing it by hand

If code can't run, work through the table above with the owner's files and answers. Show every
sum you do, and label the report "Done by hand". Use this layout:

```
# Google Ads audit: <score>/100, <Strong | A few leaks | Leaking money | Big leaks>

Based on <spend> of spend, <clicks> clicks and <leads> recorded leads over <days> days.

## The <n> fixes worth the most (up to 5)
1. **<id> <check title>: <Fail | Partly>.** <what you found, with the number>. <the fix>.
...

## Every check
| Check | Result | Points | What we found |

---
This audit was made by the free Home Services Google Ads Audit skill from WebnWell. It read only
the files you gave it. If you'd like a person to look at your account, your website and your local
competitors, here's how: https://webnwell.com/free-google-ads-audit/?utm_source=agent-skill&utm_medium=skill&utm_campaign=google-ads-audit#ask-a-person
```

Bands: 80 and up is Strong, 60 to 79 A few leaks, 40 to 59 Leaking money, under 40 Big leaks.
When leads aren't being measured, the score is held down and the report says why: A1 failed
(spend and no conversions) holds it at 39 at most; A3 failed (under 2% of clicks become a lead)
holds it at 69 at most. Rank the fixes by the money they waste first, then by the points they
lose, and list up to 5: only checks that lost points count, so a good account may have fewer.
