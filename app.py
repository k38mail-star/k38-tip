"""K38 Tip - Football Betting Recommendation Engine (Updated Flow)"""
import os, json, sqlite3, math, itertools, time, subprocess
from collections import OrderedDict
from contextlib import contextmanager
from odds_service import get_odds_for_fixture, calculate_ev
from team_names import TEAM_CN_MAP
from flask import Flask, render_template, jsonify, request
from engine.poisson import PoissonModel
from engine.monte_carlo import MonteCarlo

app = Flask(__name__)
VERSION = "v1.1.0"  # 波波鸡版本号 - 每次更新递增
DB = "/opt/k38-football/football.db"


# ---------------------------------------------------------------------------
# Startup: ensure indexes (gracefully handle missing DB)
# ---------------------------------------------------------------------------
def ensure_indexes():
    try:
        conn = sqlite3.connect(DB, timeout=3)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_matches_status ON football_matches(status);
            CREATE INDEX IF NOT EXISTS idx_matches_date ON football_matches(match_date);
            CREATE INDEX IF NOT EXISTS idx_matches_league ON football_matches(league_id);
            CREATE INDEX IF NOT EXISTS idx_matches_fixture ON football_matches(fixture_id);
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] ensure_indexes skipped: {e}", flush=True)


ensure_indexes()


# ---------------------------------------------------------------------------
# LRU Cache (replaces naive dict + trim approach)
# ---------------------------------------------------------------------------
class LRUCache(OrderedDict):
    """Simple LRU cache backed by OrderedDict."""
    def __init__(self, maxsize=500):
        super().__init__()
        self.maxsize = maxsize

    def get_item(self, key):
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key, value):
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self.maxsize:
            self.popitem(last=False)


# ---------------------------------------------------------------------------
# Engine & Caches
# ---------------------------------------------------------------------------
_poisson = None
_monte = None
_pred_cache = LRUCache(500)
_odds_cache = LRUCache(500)  # P0-2: LRU eviction prevents unbounded growth


# ---------------------------------------------------------------------------
# Circuit Breaker for Odds API
# ---------------------------------------------------------------------------
_odds_fail_count = 0
_odds_fail_time = 0.0
_ODDS_FAIL_THRESHOLD = 3
_ODDS_COOLDOWN_SEC = 300


def odds_circuit_open():
    """Check if odds circuit breaker is open (should skip API calls)."""
    if _odds_fail_count < _ODDS_FAIL_THRESHOLD:
        return False
    if time.time() - _odds_fail_time >= _ODDS_COOLDOWN_SEC:
        return False  # Half-open: allow retry
    return True


def odds_record_failure():
    global _odds_fail_count, _odds_fail_time
    _odds_fail_count += 1
    _odds_fail_time = time.time()


def odds_record_success():
    global _odds_fail_count, _odds_fail_time
    _odds_fail_count = 0
    _odds_fail_time = 0.0


# ---------------------------------------------------------------------------
# League ID -> sport_key mapping (replaces if/elif chain)
# ---------------------------------------------------------------------------
LEAGUE_SPORT_MAP = {
    "39": "soccer_epl",
    "140": "soccer_spain_la_liga",
    "135": "soccer_italy_serie_a",
    "78": "soccer_germany_bundesliga",
    "61": "soccer_france_ligue_one",
    "41": "soccer_china_superleague",
    "98": "soccer_japan_j_league",
    "292": "soccer_korea_kleague1",
}


def get_engine():
    global _poisson, _monte
    if _poisson is None:
        _poisson = PoissonModel(DB)
        _poisson.fit()
        _monte = MonteCarlo(_poisson)
    return _poisson, _monte


@contextmanager
def get_db():
    conn = sqlite3.connect(DB, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Data Access
# ---------------------------------------------------------------------------
def get_candidate_matches(limit=100, date_from=None, date_to=None, league_ids=None):
    with get_db() as conn:
        where = ["status IN ('Not Started', 'NS')", "match_date >= '2026-01-01'"]
        params = []
        if date_from:
            where.append("DATE(match_date) >= ?")
            params.append(date_from)
        if date_to:
            where.append("DATE(match_date) <= ?")
            params.append(date_to)
        if league_ids:
            placeholders = ",".join("?" for _ in league_ids)
            where.append(f"league_id IN ({placeholders})")
            params.extend(league_ids)
        where_sql = " AND ".join(where)
        rows = conn.execute(f"""
            SELECT DISTINCT fixture_id, home_team, away_team, home_team_cn, away_team_cn,
                   home_flag, away_flag, match_date, league_name, league_id
            FROM football_matches
            WHERE {where_sql}
            ORDER BY match_date ASC LIMIT ?
        """, params + [limit]).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("v84-kimi-a.html")


@app.route("/v84")
@app.route("/v84/")
@app.route("/v84/a")
@app.route("/v84-a")
def v84():
    return render_template("v84-kimi-a.html")


# ---------------------------------------------------------------------------
# Core: build predictions for candidate matches
# ---------------------------------------------------------------------------
def build_candidate_results(limit=100, date_from=None, date_to=None, league_ids=None):
    """生成候选比赛数据（含预测），供 API 和模板共用"""
    poisson, _ = get_engine()
    matches = get_candidate_matches(limit, date_from, date_to, league_ids)
    results = []
    for m in matches:
        fid = m["fixture_id"]
        pred = _pred_cache.get_item(fid)
        if pred is None:
            pred = poisson.predict_score(m["home_team"], m["away_team"], m["league_id"])
            if "error" not in pred:
                _pred_cache.put(fid, pred)
        if "error" in pred:
            continue
        hw = pred["win_prob"]["home"]
        aw = pred["win_prob"]["away"]
        dw = pred["win_prob"]["draw"]
        if hw >= aw and hw >= dw:
            winner = "home"
        elif aw >= hw and aw >= dw:
            winner = "away"
        else:
            winner = "draw"
        confidence = round(max(hw, aw, dw) * 100, 1)

        # Odds fetching with circuit breaker
        odds_data = None
        if not odds_circuit_open():
            try:
                sport_key = LEAGUE_SPORT_MAP.get(str(m["league_id"]), "soccer_fifa_world_cup")
                cache_key = (m["home_team"], m["away_team"], sport_key)
                odds_data = _odds_cache.get_item(cache_key)
                if odds_data is None:
                    odds = get_odds_for_fixture(m["home_team"], m["away_team"], sport_key=sport_key)
                    if odds and odds.get("home_odds"):
                        ev = calculate_ev(
                            max(hw, aw),
                            odds.get("home_odds") if hw >= aw else odds.get("away_odds")
                        )
                        odds_data = {
                            "home_odds": odds.get("home_odds"),
                            "away_odds": odds.get("away_odds"),
                            "edge_pct": ev.get("edge_pct") if ev else None,
                        }
                        _odds_cache.put(cache_key, odds_data)
                        odds_record_success()
                    else:
                        odds_record_failure()
            except Exception:
                odds_record_failure()
                odds_data = None

        results.append({
            "id": m["fixture_id"],
            "home": m["home_team"],
            "away": m["away_team"],
            "home_cn": m.get("home_team_cn") or TEAM_CN_MAP.get(m["home_team"], m["home_team"]),
            "away_cn": m.get("away_team_cn") or TEAM_CN_MAP.get(m["away_team"], m["away_team"]),
            "home_flag": m.get("home_flag", ""),
            "away_flag": m.get("away_flag", ""),
            "date": m["match_date"],
            "league": m.get("league_name", ""),
            "league_id": m["league_id"],
            "winner": winner,
            "prediction": {"home": "主胜", "away": "客胜", "draw": "平局"}.get(winner, ""),
            "confidence": confidence,
            "win_prob": pred["win_prob"],
            "top_scores": pred.get("top_scores", []),
            "over_under": pred.get("over_under", {}),
            "btts": pred.get("btts"),
            "fair_odds": pred.get("fair_odds"),
            "odds": {
                "home_odds": (odds_data or {}).get("home_odds"),
                "away_odds": (odds_data or {}).get("away_odds"),
                "edge_pct": (odds_data or {}).get("edge_pct"),
            } if odds_data else None,
        })
    results = [r for r in results if r["confidence"] >= 5]
    results.sort(key=lambda x: -x["confidence"])
    return results


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.route("/api/candidates")
def api_candidates():
    """返回候选比赛列表（带预测）JSON"""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    leagues = request.args.get("leagues")
    league_ids = [int(x) for x in leagues.split(",") if x.strip().isdigit()] if leagues else None
    results = build_candidate_results(100, date_from, date_to, league_ids)
    return jsonify({"matches": results, "total": len(results)})


@app.route("/api/leagues")
def api_leagues():
    """返回有未开始比赛的联赛列表"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT league_id, league_name
            FROM football_matches
            WHERE status IN ('Not Started','NS') AND match_date >= '2026-01-01'
            ORDER BY league_id
        """).fetchall()
    leagues = [{"id": r["league_id"], "name": r["league_name"], "key": f"l{r['league_id']}"} for r in rows]
    return jsonify(leagues)


@app.route("/api/generate-combos")
def api_generate_combos():
    """生成所有串关组合，Monte Carlo 模拟排序"""
    _, mc = get_engine()

    type_param = request.args.get("type", "3")

    # P2-11: Auto mode - enumerate 2-6 fold parlays and return the best
    if type_param == "auto":
        fixture_ids = request.args.getlist("ids", type=int)
        fixture_ids = list(dict.fromkeys(fixture_ids))
        if len(fixture_ids) < 2:
            return jsonify({"error": "Need at least 2 matches for auto mode"}), 400

        poisson, _ = get_engine()
        match_list = []
        with get_db() as conn:
            for fid in fixture_ids:
                pred = _pred_cache.get_item(fid)
                if pred is None:
                    row = conn.execute(
                        "SELECT home_team, away_team, league_id FROM football_matches WHERE fixture_id = ?",
                        (fid,)
                    ).fetchone()
                    if not row:
                        continue
                    pred = poisson.predict_score(row["home_team"], row["away_team"], row["league_id"])
                    if "error" in pred:
                        continue
                    _pred_cache.put(fid, pred)
                    home, away = row["home_team"], row["away_team"]
                else:
                    row = conn.execute(
                        "SELECT home_team, away_team FROM football_matches WHERE fixture_id = ?",
                        (fid,)
                    ).fetchone()
                    if not row:
                        continue
                    home, away = row["home_team"], row["away_team"]

                hw = pred["win_prob"]["home"]
                aw = pred["win_prob"]["away"]
                dw = pred["win_prob"]["draw"]
                if hw >= aw and hw >= dw:
                    bet_type, prob, prediction = "home_win", hw, "主胜"
                elif aw >= hw and aw >= dw:
                    bet_type, prob, prediction = "away_win", aw, "客胜"
                else:
                    bet_type, prob, prediction = "draw", dw, "平局"
                match_list.append({
                    "fixture_id": fid,
                    "home": home,
                    "away": away,
                    "home_xg": pred["home_xg"],
                    "away_xg": pred["away_xg"],
                    "bet_type": bet_type,
                    "prob": prob,
                    "prediction": prediction,
                })

        if len(match_list) < 2:
            return jsonify({"error": "Not enough valid matches"}), 400

        # Enumerate all parlay types and find the best
        best_combo = None
        best_hit_rate = 0
        best_type = 2
        for pt in range(2, min(7, len(match_list) + 1)):
            for combo in itertools.combinations(match_list, pt):
                sim = mc.simulate_parlay(list(combo))
                if sim["hit_rate"] > best_hit_rate:
                    best_hit_rate = sim["hit_rate"]
                    best_combo = combo
                    best_type = pt

        if best_combo:
            combo_hit_prob = 1.0
            for leg in best_combo:
                combo_hit_prob *= leg["prob"]
            result = {
                "matches": [{"home": c["home"], "away": c["away"], "prediction": c["prediction"]} for c in best_combo],
                "hit_rate": best_hit_rate,
                "hit_pct": round(best_hit_rate * 100, 1),
                "combined_prob": round(combo_hit_prob * 100, 1),
                "fair_odds": round(1 / best_hit_rate, 2) if best_hit_rate > 0 else 999,
            }
            return jsonify({
                "type": f"{best_type}x1",
                "auto_selected": True,
                "total_combos": 1,
                "candidate_matches": len(match_list),
                "top_combos": [result],
            })
        else:
            return jsonify({"error": "No valid combinations found"}), 400

    try:
        parlay_type = int(type_param)
    except (ValueError, TypeError):
        parlay_type = 3
    parlay_type = max(2, min(6, parlay_type))

    fixture_ids = request.args.getlist("ids", type=int)
    # Deduplicate fixture IDs to prevent same match being calculated twice
    fixture_ids = list(dict.fromkeys(fixture_ids))
    if len(fixture_ids) < parlay_type:
        return jsonify({"error": f"Need at least {parlay_type} matches, got {len(fixture_ids)}"}), 400

    # Gather predictions for selected matches
    poisson, _ = get_engine()
    match_list = []
    with get_db() as conn:
        for fid in fixture_ids:
            pred = _pred_cache.get_item(fid)
            if pred is None:
                row = conn.execute(
                    "SELECT home_team, away_team, league_id FROM football_matches WHERE fixture_id = ?",
                    (fid,)
                ).fetchone()
                if not row:
                    continue
                pred = poisson.predict_score(row["home_team"], row["away_team"], row["league_id"])
                if "error" in pred:
                    continue
                _pred_cache.put(fid, pred)
                home, away = row["home_team"], row["away_team"]
            else:
                row = conn.execute(
                    "SELECT home_team, away_team FROM football_matches WHERE fixture_id = ?",
                    (fid,)
                ).fetchone()
                if not row:
                    continue
                home, away = row["home_team"], row["away_team"]

            hw = pred["win_prob"]["home"]
            aw = pred["win_prob"]["away"]
            dw = pred["win_prob"]["draw"]
            if hw >= aw and hw >= dw:
                bet_type, prob, prediction = "home_win", hw, "主胜"
            elif aw >= hw and aw >= dw:
                bet_type, prob, prediction = "away_win", aw, "客胜"
            else:
                bet_type, prob, prediction = "draw", dw, "平局"
            match_list.append({
                "fixture_id": fid,
                "home": home,
                "away": away,
                "home_xg": pred["home_xg"],
                "away_xg": pred["away_xg"],
                "bet_type": bet_type,
                "prob": prob,
                "prediction": prediction,
            })

    if len(match_list) < parlay_type:
        return jsonify({"error": "Not enough valid matches"}), 400

    # Generate all combos and simulate
    results = []
    for combo in itertools.combinations(match_list, parlay_type):
        sim = mc.simulate_parlay(list(combo))
        combo_hit_prob = 1.0
        for leg in combo:
            combo_hit_prob *= leg["prob"]
        results.append({
            "matches": [{"home": c["home"], "away": c["away"], "prediction": c["prediction"]} for c in combo],
            "hit_rate": sim["hit_rate"],
            "hit_pct": sim["hit_pct"],
            "combined_prob": round(combo_hit_prob * 100, 1),
        })

    results.sort(key=lambda x: -x["hit_rate"])

    for r in results[:10]:
        if r["hit_rate"] > 0:
            r["fair_odds"] = round(1 / r["hit_rate"], 2)
        else:
            r["fair_odds"] = 999

    return jsonify({
        "type": f"{parlay_type}x1",
        "total_combos": len(results),
        "candidate_matches": len(match_list),
        "top_combos": results[:10],
    })


@app.route("/api/predict/<int:fixture_id>")
def predict_match(fixture_id):
    poisson, monte = get_engine()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM football_matches WHERE fixture_id = ?", (fixture_id,)).fetchone()
    if not row:
        return jsonify({"error": "Match not found"}), 404
    m = dict(row)
    pred = poisson.predict_score(m["home_team"], m["away_team"], m["league_id"])
    if "error" in pred:
        return jsonify(pred), 500
    sim = monte.simulate_match(pred["home_xg"], pred["away_xg"])
    pred["monte_carlo"] = sim
    return jsonify(pred)


@app.route("/api/version")
def api_version():
    commit = ""
    try:
        import subprocess
        commit = subprocess.run(["git","log","--oneline","-1"], capture_output=True, text=True, cwd="/opt/k38-tip").stdout.strip()
    except: pass
    return jsonify({"version": VERSION, "commit": commit, "server": "新加坡"})


# ---------------------------------------------------------------------------
# Warm up engine on import
# ---------------------------------------------------------------------------
print("Warming up prediction engine...", flush=True)
get_engine()
print("Engine ready!", flush=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7890, debug=False)
