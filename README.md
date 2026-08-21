# Kindle 4 display (D01100)

A 600×800 black-and-white page for the Kindle 4 experimental browser: date, weather, and a message from a gist. The page reloads every minute. Weather and the gist are baked in by GitHub Actions so the Kindle does not have to call HTTPS APIs (its browser cannot).

## Kindle URL (HTTP)

GitHub Pages is HTTPS-only, which the Kindle 4 browser cannot use. After this repo is on GitHub, open **HTTP** (not https) in **Menu → Experimental → Browser**:

```
http://raw.githack.com/splendiferousnoctifer/kindle4-display/main/docs/index.html
```

Add that as a bookmark. Leave the browser open; the page refreshes itself every 60 seconds.

Preview on a computer (HTTPS): `https://splendiferousnoctifer.github.io/kindle4-display/`

## Message gist

1. Create a **public** gist whose body is the message (plain text).
2. Open the gist, click **Raw**, copy that URL.
3. Put it in `config.json` as `gist_url`.
4. Push to `main`. Actions will pick it up within a few minutes.

## Config

Edit `config.json`:

- `city` — passed to [wttr.in](https://wttr.in) (default `Linz`)
- `timezone` — used for the baked clock fallback (`Europe/Vienna`)
- `units` — `C` or `F`
- `gist_url` — public gist raw URL

Weather data updates about every 5 minutes (GitHub’s schedule limit). The clock updates in the browser and on each 60-second reload.

## Local build

```bash
python3 build.py
```

Then open `docs/index.html`.
