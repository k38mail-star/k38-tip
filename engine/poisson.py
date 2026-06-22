"""Poisson Distribution Model for Football Goal Prediction."""
import math
import sqlite3
from datetime import datetime
from collections import defaultdict


class PoissonModel:
    """Poisson goal prediction model."""

    def __init__(self, db_path="/opt/k38-football/football.db"):
        self.db_path = db_path
        self._attack = {}
        self._defense = {}
        self._league_avg = {}
        self._fitted = False

    def fit(self, min_matches=5, recency_weight=0.7):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT home_team, away_team, home_goals, away_goals, match_date, league_id
            FROM football_matches
            WHERE status = 'Finished' AND home_goals IS NOT NULL
            ORDER BY match_date ASC
        """).fetchall()
        if not rows:
            conn.close()
            return False

        league_goals = defaultdict(list)
        for r in rows:
            league_goals[r["league_id"]].extend([r["home_goals"], r["away_goals"]])
        # Only use leagues with sufficient data (min 10 matches = 20 goal entries)
        self._league_avg = {
            lid: sum(g) / len(g)
            for lid, g in league_goals.items()
            if len(g) >= 20
        }
        all_goals = [g for goals in league_goals.values() for g in goals]
        overall_avg = sum(all_goals) / len(all_goals) if all_goals else 2.5

        team_scored = defaultdict(list)
        team_conceded = defaultdict(list)
        for r in rows:
            try:
                match_dt = datetime.strptime(r["match_date"][:10], "%Y-%m-%d")
                days_ago = (datetime.now() - match_dt).days
                w = math.exp(-days_ago / (365 * (1 - recency_weight) + 1))
            except (ValueError, TypeError):
                w = 0.5
            team_scored[r["home_team"]].append((r["home_goals"], w))
            team_conceded[r["home_team"]].append((r["away_goals"], w))
            team_scored[r["away_team"]].append((r["away_goals"], w))
            team_conceded[r["away_team"]].append((r["home_goals"], w))

        for team in set(list(team_scored) + list(team_conceded)):
            scored = team_scored.get(team, [])
            conceded = team_conceded.get(team, [])
            if len(scored) < min_matches or len(conceded) < min_matches:
                continue
            w_s = sum(w for _, w in scored)
            w_c = sum(w for _, w in conceded)
            if w_s == 0 or w_c == 0:
                continue
            avg_s = sum(g * w for g, w in scored) / w_s
            avg_c = sum(g * w for g, w in conceded) / w_c
            self._attack[team] = avg_s / overall_avg if overall_avg > 0 else 1.0
            self._defense[team] = avg_c / overall_avg if overall_avg > 0 else 1.0

        conn.close()
        self._fitted = True
        return True

    def predict_score(self, home_team, away_team, league_id=None):
        if not self._fitted:
            return {"error": "Model not fitted"}
        league_avg = self._league_avg.get(league_id, 2.5)
        home_xg = self._attack.get(home_team, 1.0) * self._defense.get(away_team, 1.0) * league_avg * 1.1
        away_xg = self._attack.get(away_team, 1.0) * self._defense.get(home_team, 1.0) * league_avg * 0.9

        max_g = 10
        probs = {}
        hw = dr = aw = 0.0
        for h in range(max_g + 1):
            for a in range(max_g + 1):
                p = self._poisson(h, home_xg) * self._poisson(a, away_xg)
                probs[(h, a)] = p
                if h > a:
                    hw += p
                elif h == a:
                    dr += p
                else:
                    aw += p

        ou = {}
        for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
            over = sum(p for (h, a), p in probs.items() if h + a > line)
            ou[str(line)] = {"over": round(over, 4), "under": round(1 - over, 4)}

        btts = sum(p for (h, a), p in probs.items() if h > 0 and a > 0)
        top5 = sorted(probs.items(), key=lambda x: -x[1])[:5]

        return {
            "home_xg": round(home_xg, 2),
            "away_xg": round(away_xg, 2),
            "win_prob": {"home": round(hw, 4), "draw": round(dr, 4), "away": round(aw, 4)},
            "top_scores": [{"s": f"{h}:{a}", "p": round(p, 4)} for (h, a), p in top5],
            "over_under": ou,
            "btts": round(btts, 4),
            "fair_odds": {
                "home": round(1 / hw, 2) if hw > 0.001 else 999,
                "draw": round(1 / dr, 2) if dr > 0.001 else 999,
                "away": round(1 / aw, 2) if aw > 0.001 else 999,
            }
        }

    @staticmethod
    def _poisson(k, lam):
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return math.exp(-lam) * (lam ** k) / math.factorial(k)


if __name__ == "__main__":
    import json as _json
    m = PoissonModel()
    if m.fit():
        print(_json.dumps(m.predict_score("England", "Brazil", 1), indent=2, ensure_ascii=False))
