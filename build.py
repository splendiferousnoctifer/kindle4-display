#!/usr/bin/env python3
"""Bake weather + gist message into a Kindle 4 static page."""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
TEMPLATE_PATH = ROOT / "template.html"
OUT_PATH = ROOT / "docs" / "index.html"
USER_AGENT = "kindle4-display/1.0 (+https://github.com/splendiferousnoctifer/kindle4-display)"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def short_cond(desc: str) -> str:
    d = (desc or "").lower()
    if "thunder" in d:
        return "Storm"
    if "snow" in d or "sleet" in d or "blizzard" in d:
        return "Snow"
    if "drizzle" in d:
        return "Drizzle"
    if "rain" in d or "shower" in d:
        return "Rain"
    if "fog" in d or "mist" in d:
        return "Fog"
    if "overcast" in d:
        return "Overcast"
    if "cloud" in d:
        return "Clouds"
    if "clear" in d or "sunny" in d:
        return "Clear"
    if "wind" in d:
        return "Windy"
    return (desc or "—")[:12]


def forecast_html(days: list[dict], units: str) -> str:
    if not days:
        return '<div class="fc-cond">Forecast unavailable</div>'
    hi_key = "maxtempC" if units.upper() != "F" else "maxtempF"
    lo_key = "mintempC" if units.upper() != "F" else "mintempF"
    cells = []
    for i, day in enumerate(days[:3]):
        date_s = day.get("date") or ""
        try:
            dt = datetime.strptime(date_s, "%Y-%m-%d")
            label = dt.strftime("%a")
        except ValueError:
            label = "—"
        counts: dict[str, int] = {}
        for hour in day.get("hourly") or []:
            try:
                desc_h = hour["weatherDesc"][0]["value"]
            except (KeyError, IndexError, TypeError):
                continue
            counts[desc_h] = counts.get(desc_h, 0) + 1
        desc = max(counts, key=counts.get) if counts else ""
        cls = "first" if i == 0 else ""
        cells.append(
            "<td class='"
            + cls
            + "'>"
            "<div class='fc-day'>"
            + html.escape(label)
            + "</div>"
            "<div class='fc-hi'>"
            + html.escape(str(day.get(hi_key, "—")))
            + "°</div>"
            "<div class='fc-lo'>"
            + html.escape(str(day.get(lo_key, "—")))
            + "°</div>"
            "<div class='fc-cond'>"
            + html.escape(short_cond(desc))
            + "</div></td>"
        )
    return "<table class='fc' cellspacing='0' cellpadding='0'><tr>" + "".join(cells) + "</tr></table>"


def weather(city: str, units: str) -> tuple[str, str, str, str]:
    loc = urllib.parse.quote(city)
    empty_fc = forecast_html([], units)
    try:
        data = json.loads(fetch(f"https://wttr.in/{loc}?format=j1"))
        cur = data["current_condition"][0]
        temp_key = "temp_C" if units.upper() != "F" else "temp_F"
        temp = f"{cur[temp_key]}°"
        cond = (cur["weatherDesc"][0]["value"] or "").strip()
        extra = f"{cur['humidity']}% humidity"
        days = data.get("weather") or []
        if days and days[0].get("maxtempC"):
            hi_key = "maxtempC" if units.upper() != "F" else "maxtempF"
            lo_key = "mintempC" if units.upper() != "F" else "mintempF"
            extra = f"H {days[0][hi_key]}°  /  L {days[0][lo_key]}°   ·   {cur['humidity']}%"
        return temp, cond, extra, forecast_html(days, units)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, IndexError):
        return "--°", "Weather unavailable", city, empty_fc


def gist_message(url: str) -> str:
    if not url.strip():
        return "Add a public gist raw URL in config.json to show a message here."
    raw = url.strip()
    if "gist.github.com" in raw and "/raw" not in raw:
        raw = raw.rstrip("/") + "/raw"
    try:
        text = fetch(raw).strip()
    except (urllib.error.URLError, TimeoutError):
        return "Could not load gist."
    text = re.sub(r"\s+\n", "\n", text)
    if len(text) > 220:
        text = text[:217] + "..."
    return html.escape(text).replace("\n", "<br>")


def render(cfg: dict) -> str:
    tz = ZoneInfo(cfg.get("timezone") or "Europe/Vienna")
    now = datetime.now(tz)
    temp, cond, extra, forecast = weather(cfg.get("city") or "Linz", cfg.get("units") or "C")
    message = gist_message(cfg.get("gist_url") or "")
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{WEEKDAY}}": now.strftime("%A"),
        "{{DATE}}": now.strftime("%B ") + str(now.day) + now.strftime(", %Y"),
        "{{TIME}}": now.strftime("%H:%M"),
        "{{TEMP}}": html.escape(temp),
        "{{CONDITION}}": html.escape(cond),
        "{{CITY}}": html.escape(cfg.get("city") or "Linz"),
        "{{WEATHER_EXTRA}}": html.escape(extra),
        "{{FORECAST}}": forecast,
        "{{MESSAGE}}": message,
    }
    for key, value in replacements.items():
        tpl = tpl.replace(key, value)
    return tpl


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(load_config()), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
