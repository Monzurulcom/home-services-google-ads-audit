# How to make the common fixes

Walk the owner through only the fix they ask about. Google renames menus from time to time; if a
name doesn't match, look for the nearest one.

## Add negative keywords (B1, B2, B3)

1. Open **Insights and reports > Search terms**.
2. Tick the searches that will never become a job.
3. Click **Add as negative keyword**, choose **Campaign** level (or a list), and save.
4. For words that should never trigger an ad anywhere (jobs, hiring, salary, diy, how to, youtube,
   home depot, course, training), go to **Tools > Shared library > Negative keyword lists**, create a
   list, add the words as **phrase match**, and apply the list to every campaign.

## Count phone calls as leads (A2)

1. **Goals > Conversions > New conversion action > Phone calls.**
2. Create "Calls from ads" (calls from the call button) and set a minimum call length of 60 seconds.
3. Create "Calls to a phone number on your website", then add Google's forwarding-number snippet
   to the site through Google Tag Manager or the site builder. A call-tracking tool (CallRail and
   others) works too.

## Show ads only in the service area (C3)

1. Open the campaign, then **Settings > Locations > Location options**.
2. Choose **Presence: people in or regularly in your included locations**. Save.
3. Repeat for every campaign.

## Add a call button (D2)

**Ads > Assets > + > Call**, enter the business number, turn on call reporting, and set the asset
schedule to the hours someone answers.

## Set an ad schedule (D3)

Open the campaign, then **Ad schedule > Edit**, add the hours the phone is answered, and save.

## Stop a Performance Max or Display campaign that isn't producing leads (B5)

On the **Campaigns** page, tick the campaign, then **Edit > Pause**. Move its daily budget to the
search campaign that produces the most leads.

## Slow down smart bidding without data (A4)

Open the campaign, then **Settings > Bidding > Change bid strategy > Maximize clicks**, and set a
maximum cost per click near the average you pay now. Switch back to Maximize conversions once the
campaign records about 15 leads a month.
