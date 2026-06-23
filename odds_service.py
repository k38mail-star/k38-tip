"""K38 Odds Service — The Odds API integration.

获取实时赔率并计算期望价值（EV）。
如果 API Key 未配置，函数优雅降级返回 None。
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"


def get_odds_for_fixture(home_team: str, away_team: str, sport_key: str = "soccer_epl", region: str = "eu") -> dict | None:
    """获取一场比赛的实时赔率。

    Returns:
        dict with home_odds, away_odds, draw_odds, bookmaker, updated_at
        or None if API key missing / network error / no data.
    """
    if not ODDS_API_KEY:
        return None

    try:
        url = (
            f"{ODDS_API_BASE}/sports/{sport_key}/odds"
            f"?apiKey={ODDS_API_KEY}&regions={region}"
            f"&markets=h2h&oddsFormat=decimal"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())

        if not isinstance(data, list):
            return None

        for event in data:
            ev_home = (event.get("home_team") or "").lower().strip()
            ev_away = (event.get("away_team") or "").lower().strip()
            q_home = home_team.lower().strip()
            q_away = away_team.lower().strip()
            if ev_home == q_home and ev_away == q_away:
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("key") != "h2h":
                            continue
                        outcomes = {o["name"].lower(): o["price"] for o in market.get("outcomes", [])}
                        return {
                            "home_odds": outcomes.get(q_home),
                            "away_odds": outcomes.get(q_away),
                            "draw_odds": outcomes.get("draw") or outcomes.get("平"),
                            "bookmaker": bookmaker.get("title", ""),
                            "updated_at": event.get("commence_time", ""),
                        }
        return None
    except Exception:
        return None


def calculate_ev(pred_win_prob: float, win_odds: float) -> dict | None:
    """计算期望价值 (EV) 和 Kelly 分数。

    Args:
        pred_win_prob: 模型预测的获胜概率 (0-1)
        win_odds: 获胜的赔率 (decimal)

    Returns:
        dict with edge_pct, ev_pct, kelly_fraction, or None
    """
    if not all([pred_win_prob, win_odds]):
        return None

    fair_odds = 1 / pred_win_prob if pred_win_prob > 0 else 999
    edge_pct = round((win_odds - fair_odds) / fair_odds * 100, 2)
    ev_pct = round((pred_win_prob * win_odds - 1) * 100, 2)

    # Kelly: f* = (bp - q) / b
    # b = decimal odds - 1, p = win prob, q = 1-p
    b = win_odds - 1
    q = 1 - pred_win_prob
    kelly_fraction = round((b * pred_win_prob - q) / b, 4) if b > 0 else 0

    return {
        "edge_pct": edge_pct,
        "ev_pct": ev_pct,
        "kelly_fraction": max(0, kelly_fraction),
    }
