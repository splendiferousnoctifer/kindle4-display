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


def weather(city: str, units: str) -> tuple[str, str, str]:
    loc = urllib.parse.quote(city)
    try:
        data = json.loads(fetch(f"https://wttr.in/{loc}?format=j1"))
        cur = data["current_condition"][0]
        temp_key = "temp_C" if units.upper() != "F" else "temp_F"
        feels_key = "FeelsLikeC" if units.upper() != "F" else "FeelsLikeF"
        temp = f"{cur[temp_key]}°"
        cond = cur["weatherDesc"][0]["value"]
        extra = f"feels {cur[feels_key]}° · {cur['humidity']}% humidity"
        day = data.get("weather", [{}])[0]
        if day.get("maxtempC"):
            hi = day["maxtempC"] if units.upper() != "F" else day["maxtempF"]
            lo = day["mintempC"] if units.upper() != "F" else day["mintempF"]
            extra = f"H {hi}° / L {lo}° · {cur['humidity']}%"
        return temp, cond, extra
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, IndexError):
        return "--°", "Weather unavailable", city


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
    if len(text) > 400:
        text = text[:397] + "..."
    return html.escape(text).replace("\n", "<br>")


def render(cfg: dict) -> str:
    tz = ZoneInfo(cfg.get("timezone") or "Europe/Vienna")
    now = datetime.now(tz)
    temp, cond, extra = weather(cfg.get("city") or "Linz", cfg.get("units") or "C")
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
