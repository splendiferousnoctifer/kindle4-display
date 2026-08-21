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
    if "overcast" in d or "cloud" in d:
        return "Clouds"
    if "clear" in d or "sunny" in d:
        return "Clear"
    if "wind" in d:
        return "Windy"
    return (desc or "—")[:12]


def hour_from_wttr(value: object) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n < 24:
        return n
    return n // 100


def forecast_html(today: dict | None, units: str, now: datetime) -> str:
    hours = list((today or {}).get("hourly") or [])
    parsed = []
    for slot in hours:
        h = hour_from_wttr(slot.get("time"))
        if h is None:
            continue
        parsed.append((h, slot))
    upcoming = [(h, slot) for h, slot in parsed if h >= now.hour]
    if not upcoming:
        upcoming = parsed[-4:]
    upcoming = upcoming[:4]
    if not upcoming:
        return "<div class='h-cond'>No hourly forecast today</div>"
    temp_key = "tempC" if units.upper() != "F" else "tempF"
    rows = []
    for i, (h, slot) in enumerate(upcoming):
        try:
            desc = slot["weatherDesc"][0]["value"]
        except (KeyError, IndexError, TypeError):
            desc = ""
        temp = slot.get(temp_key, "—")
        cls = " class='first'" if i == 0 else ""
        rows.append(
            "<tr"
            + cls
            + "><td class='h-time'>"
            + html.escape(f"{h:02d}:00")
            + "</td><td class='h-temp'>"
            + html.escape(str(temp))
            + "°</td><td class='h-cond'>"
            + html.escape(short_cond(desc))
            + "</td></tr>"
        )
    return "<table class='hours' cellspacing='0' cellpadding='0'>" + "".join(rows) + "</table>"


def weather(city: str, units: str, now: datetime) -> tuple[str, str, str, str]:
    loc = urllib.parse.quote(city)
    empty_fc = forecast_html(None, units, now)
    try:
        data = json.loads(fetch(f"https://wttr.in/{loc}?format=j1"))
        cur = data["current_condition"][0]
        temp_key = "temp_C" if units.upper() != "F" else "temp_F"
        temp = f"{cur[temp_key]}°"
        cond = (cur["weatherDesc"][0]["value"] or "").strip()
        extra = f"{cur['humidity']}% humidity"
        days = data.get("weather") or []
        today = days[0] if days else None
        if today and today.get("maxtempC"):
            hi_key = "maxtempC" if units.upper() != "F" else "maxtempF"
            lo_key = "mintempC" if units.upper() != "F" else "mintempF"
            extra = f"H {today[hi_key]}°  /  L {today[lo_key]}°   ·   {cur['humidity']}%"
        return temp, cond, extra, forecast_html(today, units, now)
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
    temp, cond, extra, forecast = weather(cfg.get("city") or "Linz", cfg.get("units") or "C", now)
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
