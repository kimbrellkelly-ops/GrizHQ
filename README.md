# Griz HQ automatic updates

Upload the files in this package to the root of your GitHub Pages repository.

The GitHub Action refreshes `data.json` twice per hour from official/public sources. It updates:
- Montana schedule and completed results
- overall and Big Sky record
- next opponent/date/time
- AFCA Coaches Poll and Stats Perform Top 25
- FCS Top 25 data used by the Scores tab
- official Montana football news
- core cumulative stats from GoGriz

The site also checks `data.json` every 5 minutes while a visitor has the site open, so the updated information can appear without a manual browser refresh.

The workflow can also be run manually from GitHub: Actions -> Refresh Griz HQ data -> Run workflow.

Keep your existing `CNAME` and any other repository files not included here.
