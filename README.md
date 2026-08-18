# Aeronca

Daily aggregator of Aeronca aircraft classified listings from [Controller.com](https://www.controller.com)
and [Barnstormers.com](https://www.barnstormers.com), published as a static page
(`docs/index.html`) meant to be embedded via `<iframe>` on taildraggers.com.

## How it works

- `scraper/barnstormers.py` and `scraper/controller.py` each search their site for
  Aeronca listings, follow pagination, then visit each listing's detail page to pull
  out the title, price, location, and posted date (using structured data/JSON-LD when
  the site provides it, falling back to regex heuristics over the visible text).
- `main.py` runs both scrapers, de-duplicates results, and renders them into
  `docs/index.html` titled **"Other Aeronca Ads on the Web"**, with one row per
  listing: Title (linked to the original ad), Price, Location, Date Posted, and Site
  Posted On.
- `.github/workflows/daily-scrape.yml` runs the whole thing once a day (13:00 UTC),
  commits the regenerated `docs/index.html` if it changed, and can also be triggered
  manually from the Actions tab (`workflow_dispatch`).

## One-time setup: enable GitHub Pages

This repo publishes `docs/index.html` as a plain static file — GitHub Pages just needs
to be pointed at it once:

1. Go to **Settings → Pages** in this repository.
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Branch: `main`, folder: `/docs`. Save.
4. GitHub will publish the page at `https://taildraggers.github.io/aeronca/`
   (may take a minute or two the first time).

## Embedding on taildraggers.com

```html
<iframe
  src="https://taildraggers.github.io/aeronca/"
  title="Other Aeronca Ads on the Web"
  style="width: 100%; height: 800px; border: 0;"
  loading="lazy">
</iframe>
```

## Running locally

```bash
pip install -r requirements.txt
python main.py
```

This writes/overwrites `docs/index.html`.

## Notes

- Each scraper fails independently — if one site changes its markup or is briefly
  unreachable, the other site's listings still get published, and the run logs will
  show a `[warn]`/`[error]` line pointing at what broke.
- The scrapers identify themselves with a descriptive `User-Agent` and add a short
  delay between requests to be polite to both sites.
