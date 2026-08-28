# Locked export structure

## Weekly client PDF (this is the weekly report)

Source: `samples/Stuart Mitchell Meta Ads Report June 29 (1).pdf`

Google Docs → PDF, **US Letter portrait** (612×792), 3 pages. Punchline Promotions logo top-left. Not a spreadsheet dump and not the monthly slide deck. Body type is Arial 11pt (regular / bold / italic). The weekly template embeds Liberation Sans (Arial-metric, OFL) so production Linux matches; we do not ship Microsoft Arial.

### Page chrome

- Logo (Punchline Promotions) top-left on every page
- Title bar: `STUART MITCHELL | META ADS REPORTING`
- Meta row: Client · Date (`Updated to {updated_until}`) · Account Manager (Abby)
- Thin black frame around the body

### Body order

1. **Overview of all Campaigns** — one table row per campaign:
   platform, campaign name, status, amount spent, clicks, CPC, CTR, tix sold, CPP
2. **One section per campaign**, in overview order. Each section:
   - Yellow heading: `{campaign name} Performance Update ({updated_until})`
   - Optional campaign note (1–2 sentences, e.g. which cities are still live)
   - **If the campaign has cities (OTR):**
     - Wide city table: city + status + spend + clicks + CPC + **tix sold by week date** + total tix + total CPP
     - Overall totals as bullets (spend, clicks, CPC, tix, CPP)
     - One sentence on the campaign as a whole
     - **Per city:** heading `{City} — Live|Now off` (name bold, status italic). Two punch bullets that must stay on one line each: `Ad Spend | Clicks | CPC` then `Tickets Sold | CPP`. Then the city comment paragraph, indented with the bullet text.
     - **Next Steps** (bullets)
   - **If the campaign has no cities (Edinburgh, Blackfriars):**
     - KPI bullets: spend, clicks, CPC, CTR, tix, CPP
     - **Performance Summary** (bullets)
     - **Next Steps** (bullets)

Numbers come from Meta CSV + typed Tix Sold. All prose (note, city comments, performance summary, next steps) is written by Abby.

### What we do not copy from the sample

- Pasting a screenshot of the Google Sheet into the PDF. Recreate the city table in HTML if we have the week history.
- The Bots Lab masthead. Client PDF is Punchline-branded.

## Monthly presentation

Source example: `samples/weekly PDF and monthly presentation.pdf` (10 landscape slides). Separate template. Pages:

1. Cover — CAMPAIGN OVERVIEW
2. Event slide — Edinburgh Shows
3. Event slide — Blackfriars Shows
4. Boost posts list
5. Section — CURRENT CAMPAIGNS — OTR
6. OTR totals + narrative
7. OTR city rows
8. NEXT STEPS
9. QUESTIONS?

Dashboard import: Meta CSV on **Overview** (and again on the week detail page).
