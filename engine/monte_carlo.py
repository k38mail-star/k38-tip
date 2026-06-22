"""Monte Carlo Simulation for Match Outcomes & Parlay Analysis."""
import numpy as np


class MonteCarlo:
    def __init__(self, poisson_model=None):
        self.poisson = poisson_model

    def simulate_match(self, home_xg, away_xg, n=50000):
        """Simulate n matches using vectorized numpy Poisson."""
        home_goals = np.random.poisson(max(home_xg, 0.01), n)
        away_goals = np.random.poisson(max(away_xg, 0.01), n)
        total = home_goals + away_goals

        return {
            "home_wins": round(float(np.mean(home_goals > away_goals)), 4),
            "draws": round(float(np.mean(home_goals == away_goals)), 4),
            "away_wins": round(float(np.mean(home_goals < away_goals)), 4),
            "btts": round(float(np.mean((home_goals > 0) & (away_goals > 0))), 4),
            "over_2.5": round(float(np.mean(total > 2.5)), 4),
            "over_3.5": round(float(np.mean(total > 3.5)), 4),
            "over_4.5": round(float(np.mean(total > 4.5)), 4),
        }

    def simulate_parlay(self, matches, n=20000):
        """Simulate a parlay. matches: [{home_xg, away_xg, bet_type, line}]"""
        hits = np.ones(n, dtype=bool)
        for m in matches:
            hg = np.random.poisson(max(m["home_xg"], 0.01), n)
            ag = np.random.poisson(max(m["away_xg"], 0.01), n)
            hits &= self._check_vec(m, hg, ag)
        hr = float(np.mean(hits))
        return {"matches": len(matches), "hit_rate": hr, "hit_pct": round(hr * 100, 1)}

    def _check_vec(self, bet, h, a):
        """Vectorized bet check."""
        t = bet["bet_type"]
        if t == "home_win":
            return h > a
        if t == "away_win":
            return a > h
        if t == "draw":
            return h == a
        if t == "over":
            return (h + a) > bet.get("line", 2.5)
        if t == "under":
            return (h + a) < bet.get("line", 2.5)
        if t == "btts":
            return (h > 0) & (a > 0)
        return np.ones(len(h), dtype=bool)
