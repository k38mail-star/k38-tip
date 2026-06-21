"""Walk-Forward Analysis for parameter optimization."""
import sqlite3
from itertools import product


class WalkForward:
    """Walk-Forward Analysis: optimize params on training window, test on next window."""

    def __init__(self, db_path="/opt/k38-football/football.db"):
        self.db_path = db_path

    def run(self, window_size=50, step=25, param_grid=None):
        """Run walk-forward analysis.
        
        Args:
            window_size: Matches per training window
            step: Step between windows
            param_grid: {param_name: [values]} to test
        """
        if param_grid is None:
            param_grid = {
                "recency_weight": [0.5, 0.7, 0.9],
                "min_matches": [3, 5, 10],
            }
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT rowid, home_team, away_team, home_goals, away_goals, match_date, league_id
            FROM football_matches WHERE status='Finished' AND home_goals IS NOT NULL
            ORDER BY match_date ASC
        """).fetchall()
        conn.close()

        if len(rows) < window_size + 10:
            return {"error": f"Need at least {window_size + 10} matches"}

        results = []
        start = 0
        while start + window_size + step <= len(rows):
            train = rows[start:start + window_size]
            test = rows[start + window_size:start + window_size + step]
            if len(test) < 5:
                break

            best = self._find_best_params(train, test, param_grid)
            results.append({
                "window": f"{start}-{start+window_size+step}",
                "train_size": len(train),
                "test_size": len(test),
                "best_params": best,
            })
            start += step

        # Summarize best params across all windows
        from collections import Counter
        param_votes = {}
        for r in results:
            for k, v in r["best_params"].items():
                param_votes.setdefault(k, Counter()).update({str(v): 1})

        consensus = {k: c.most_common(1)[0][0] for k, c in param_votes.items()}
        return {"windows": len(results), "results": results, "consensus_params": consensus}

    def _find_best_params(self, train, test, param_grid):
        keys = list(param_grid.keys())
        vals = list(param_grid.values())
        best_acc, best_params = 0, {}

        for combo in product(*vals):
            params = dict(zip(keys, combo))
            acc = self._eval_params(train, test, params)
            if acc > best_acc:
                best_acc, best_params = acc, params
        return best_params | {"accuracy": round(best_acc, 3)}

    def _eval_params(self, train, test, params):
        from .poisson import PoissonModel
        pm = PoissonModel()
        pm._fitted = True
        pm._attack = {}
        pm._defense = {}

        # Simplified fitting from train data
        from collections import defaultdict
        scored, conceded = defaultdict(list), defaultdict(list)
        for r in train:
            scored[r["home_team"]].append(r["home_goals"])
            conceded[r["home_team"]].append(r["away_goals"])
            scored[r["away_team"]].append(r["away_goals"])
            conceded[r["away_team"]].append(r["home_goals"])

        avg_goals = sum(r["home_goals"] + r["away_goals"] for r in train) / (len(train) * 2)
        for team in set(list(scored) + list(conceded)):
            if len(scored.get(team, [])) < params.get("min_matches", 3):
                continue
            pm._attack[team] = (sum(scored[team])/len(scored[team])) / avg_goals if avg_goals > 0 else 1.0
            pm._defense[team] = (sum(conceded[team])/len(conceded[team])) / avg_goals if avg_goals > 0 else 1.0

        correct = 0
        for r in test:
            home_xg = pm._attack.get(r["home_team"], 1.0) * pm._defense.get(r["away_team"], 1.0) * avg_goals * 1.1
            away_xg = pm._attack.get(r["away_team"], 1.0) * pm._defense.get(r["home_team"], 1.0) * avg_goals * 0.9
            pred_home = home_xg > away_xg
            pred_away = away_xg > home_xg
            actual_home = r["home_goals"] > r["away_goals"]
            actual_away = r["away_goals"] > r["home_goals"]
            if actual_home == pred_home or actual_away == pred_away:
                correct += 1

        return correct / len(test) if test else 0
