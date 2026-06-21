"""Monte Carlo Simulation for Match Outcomes & Parlay Analysis."""
import random, math


class MonteCarlo:
    def __init__(self, poisson_model=None):
        self.poisson = poisson_model

    def simulate_match(self, home_xg, away_xg, n=50000):
        results = {"home_wins": 0, "draws": 0, "away_wins": 0,
                   "btts": 0, "over_2.5": 0, "over_3.5": 0, "over_4.5": 0}
        for _ in range(n):
            h, a = self._rpoisson(home_xg), self._rpoisson(away_xg)
            if h > a: results["home_wins"] += 1
            elif a > h: results["away_wins"] += 1
            else: results["draws"] += 1
            if h > 0 and a > 0: results["btts"] += 1
            if h + a > 2.5: results["over_2.5"] += 1
            if h + a > 3.5: results["over_3.5"] += 1
            if h + a > 4.5: results["over_4.5"] += 1
        return {k: round(v/n, 4) if isinstance(v, int) else v for k, v in results.items()}

    def simulate_parlay(self, matches, n=20000):
        """Simulate a parlay. matches: [{home_xg, away_xg, bet_type, line}]"""
        hits = 0
        for _ in range(n):
            ok = all(self._check(m, self._rpoisson(m["home_xg"]), self._rpoisson(m["away_xg"])) for m in matches)
            if ok: hits += 1
        hr = hits / n
        return {"matches": len(matches), "hit_rate": hr, "hit_pct": round(hr*100, 1)}

    def _check(self, bet, h, a):
        t = bet["bet_type"]
        if t == "home_win": return h > a
        if t == "away_win": return a > h
        if t == "draw": return h == a
        if t == "over": return h + a > bet.get("line", 2.5)
        if t == "under": return h + a < bet.get("line", 2.5)
        if t == "btts": return h > 0 and a > 0
        return True

    @staticmethod
    def _rpoisson(lam):
        if lam <= 0: return 0
        L, k, p = math.exp(-lam), 0, 1.0
        while p > L: k += 1; p *= random.random()
        return k - 1
