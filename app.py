"""K38 Tip - Football Betting Recommendation Engine (Updated Flow)"""
import json, sqlite3, math, itertools, random
from odds_service import get_odds_for_fixture, calculate_ev
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from engine.poisson import PoissonModel
from engine.monte_carlo import MonteCarlo
from engine.kelly import KellyCriterion
from engine.walk_forward import WalkForward
from engine.stress_test import StressTest

app = Flask(__name__)
DB = "/opt/k38-football/football.db"

_poisson = None
_monte = None

def get_engine():
    global _poisson, _monte
    if _poisson is None:
        _poisson = PoissonModel(DB)
        _poisson.fit()
        _monte = MonteCarlo(_poisson)
    return _poisson, _monte

def get_db():
    conn = sqlite3.connect(DB, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def get_candidate_matches(limit=30, date_from=None, date_to=None):
    conn = get_db()
    where = ["status IN ('Not Started', 'NS')"]
    params = []
    if date_from:
        where.append("match_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("match_date <= ?")
        params.append(date_to)
    where_sql = " AND ".join(where)
    params.append(limit)
    rows = conn.execute(f"""
        SELECT fixture_id, home_team, away_team, home_team_cn, away_team_cn,
               home_flag, away_flag, match_date, league_name, league_id,
               match_date as match_time
        FROM football_matches
        WHERE {where_sql}
        ORDER BY match_date ASC LIMIT ?
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats_for_team(team, stat_type, limit=5):
    import json as j
    conn = get_db()
    rows = conn.execute("""
        SELECT events, home_team, away_team
        FROM football_matches
        WHERE (home_team=? OR away_team=?) AND events IS NOT NULL AND events!='[]'
        ORDER BY match_date DESC LIMIT ?
    """, (team, team, limit)).fetchall()
    conn.close()
    results = []
    for r in rows:
        try: evs = j.loads(r["events"])
        except: continue
        count = 0; is_home = r["home_team"] == team
        for ev in evs:
            if not isinstance(ev, dict): continue
            if stat_type == "goals" and ev.get("type") == "Goal":
                if (is_home and ev.get("team") in ["home", team]) or (not is_home and ev.get("team") in ["away", team]): count += 1
            elif stat_type == "corners" and ev.get("type") == "Corner":
                if (is_home and ev.get("team") in ["home", team]) or (not is_home and ev.get("team") in ["away", team]): count += 1
        results.append(count)
    return results

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/v<int:vid>")
@app.route("/v<int:vid>/")
def version(vid):
    name = {2:"v2", 3:"v3", 4:"v4", 5:"v5", 81:"v81-home"}
    tmpl = name.get(vid)
    if tmpl:
        return render_template(tmpl+".html")
    return "版本不存在", 404

def build_candidate_results(limit=30, date_from=None, date_to=None):
    """生成候选比赛数据（含预测），供 API 和模板共用"""
    poisson, _ = get_engine()
    matches = get_candidate_matches(limit, date_from, date_to)
    results = []
    for m in matches:
        pred = poisson.predict_score(m["home_team"], m["away_team"], m["league_id"])
        if "error" in pred: continue
        hw = pred["win_prob"]["home"]
        aw = pred["win_prob"]["away"]
        winner = "home" if hw >= aw else "away"
        confidence = round(max(hw, aw) * 100, 1)
        home_corners = get_stats_for_team(m["home_team"], "corners")
        away_corners = get_stats_for_team(m["away_team"], "corners")
        avg_corners = round(
            (sum(home_corners)/len(home_corners) if home_corners else 5) +
            (sum(away_corners)/len(away_corners) if away_corners else 3.5), 1
        )
        odds_data = None
        try:
            sport_key = "soccer_fifa_world_cup"
            lid = str(m["league_id"])
            if lid == "39": sport_key = "soccer_epl"
            elif lid == "140": sport_key = "soccer_spain_la_liga"
            elif lid == "135": sport_key = "soccer_italy_serie_a"
            elif lid == "78": sport_key = "soccer_germany_bundesliga"
            elif lid == "61": sport_key = "soccer_france_ligue_one"
            elif lid == "41": sport_key = "soccer_china_superleague"
            elif lid == "98": sport_key = "soccer_japan_j_league"
            elif lid == "292": sport_key = "soccer_korea_kleague1"
            odds = get_odds_for_fixture(m["home_team"], m["away_team"], sport_key=sport_key)
            if odds and odds.get("home_odds"):
                ev = calculate_ev(
                    max(hw, aw), min(hw, aw),
                    odds.get("home_odds") if hw >= aw else odds.get("away_odds"),
                    odds.get("away_odds") if hw >= aw else odds.get("home_odds")
                )
                odds_data = {
                    "home_odds": odds.get("home_odds"),
                    "away_odds": odds.get("away_odds"),
                    "draw_odds": odds.get("draw_odds"),
                    "bookmaker": odds.get("bookmaker", ""),
                    "edge_pct": ev["edge_pct"] if ev else None,
                    "ev_pct": ev["ev_pct"] if ev else None,
                    "kelly": ev["kelly_fraction"] if ev else None,
                }
        except:
            pass
        results.append({
            "id": m["fixture_id"],
            "date": m["match_date"],
            "match_time": m["match_time"],
            "home": m["home_team"],
            "away": m["away_team"],
            "home_cn": m.get("home_team_cn", ""),
            "away_cn": m.get("away_team_cn", ""),
            "home_flag": m.get("home_flag", ""),
            "away_flag": m.get("away_flag", ""),
            "league": m["league_name"],
            "prediction": "主胜" if winner == "home" else "客胜",
            "confidence": confidence,
            "home_xg": pred["home_xg"],
            "away_xg": pred["away_xg"],
            "btts": round(pred["btts"], 2) if isinstance(pred.get("btts"), float) else 0,
            "over_2_5": pred["over_under"]["2.5"]["over"],
            "avg_corners": avg_corners,
            "odds": odds_data,
        })
    results = [r for r in results if r["confidence"] >= 5]
    results.sort(key=lambda x: -x["confidence"])
    return results

@app.route("/api/candidates")
def api_candidates():
    """返回候选比赛列表（带预测）JSON"""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    results = build_candidate_results(30, date_from, date_to)
    return jsonify({"matches": results, "total": len(results)})

@app.route("/v83")
@app.route("/v83/")
def v83():
    matches = build_candidate_results(30)
    return render_template("v83.html", matches=matches)

@app.route("/api/generate-combos")
def api_generate_combos():
    """生成所有串关组合，Monte Carlo 模拟排序"""
    _, mc = get_engine()

    try:
        parlay_type = int(request.args.get("type", 3))
        if parlay_type < 2 or parlay_type > 6:
            return jsonify({"error": "parlay_type must be 2-6"}), 400
        match_ids = request.args.getlist("ids")
        if not match_ids:
            return jsonify({"error": "No matches selected"}), 400
        if len(match_ids) > 20:
            return jsonify({"error": "Maximum 20 matches allowed"}), 400
        if len(match_ids) < parlay_type:
            return jsonify({"error": f"Need at least {parlay_type} matches"}), 400
    except:
        return jsonify({"error": "Invalid parameters"})

    # Get match predictions
    conn = get_db()
    placeholders = ",".join("?" for _ in match_ids)
    rows = conn.execute(f"""
        SELECT fixture_id, home_team, away_team, match_date, league_name, league_id
        FROM football_matches WHERE fixture_id IN ({placeholders})
    """, match_ids).fetchall()
    conn.close()

    match_map = {r["fixture_id"]: dict(r) for r in rows}
    poisson, _ = get_engine()

    # Build all combinations
    match_list = [(int(mid), match_map.get(int(mid))) for mid in match_ids if int(mid) in match_map]
    if len(match_list) < parlay_type:
        return jsonify({"error": "Not enough valid matches"})

    all_combos = list(itertools.combinations(match_list, parlay_type))
    results = []

    for combo in all_combos:
        mc_input = []
        combo_hit_prob = 1.0
        combo_details = []
        
        for fid, m in combo:
            pred = poisson.predict_score(m["home_team"], m["away_team"], m["league_id"])
            if "error" in pred: continue
            hw = pred["win_prob"]["home"]
            aw = pred["win_prob"]["away"]
            win_prob = max(hw, aw)
            combo_hit_prob *= win_prob

            mc_input.append({
                "home_xg": pred["home_xg"],
                "away_xg": pred["away_xg"],
                "bet_type": "home_win" if hw >= aw else "away_win"
            })
            combo_details.append({
                "fixture_id": fid,
                "home": m["home_team"], "away": m["away_team"],
                "date": m["match_date"], "league": m["league_name"],
                "prediction": "主胜" if hw >= aw else "客胜",
                "confidence": round(max(hw, aw) * 100, 1),
            })

        if len(combo_details) < parlay_type: continue

        # Monte Carlo simulation
        sim = mc.simulate_parlay(mc_input, n=10000)

        results.append({
            "matches": combo_details,
            "hit_rate": sim["hit_rate"],
            "hit_pct": sim["hit_pct"],
            "combined_prob": round(combo_hit_prob * 100, 1),
        })

    # Sort by hit rate descending
    results.sort(key=lambda x: -x["hit_rate"])
    
    # Calculate fair odds for top combos
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
    conn = get_db()
    row = conn.execute("SELECT * FROM football_matches WHERE fixture_id = ?", (fixture_id,)).fetchone()
    conn.close()
    if not row: return jsonify({"error": "Match not found"})
    m = dict(row)
    pred = poisson.predict_score(m["home_team"], m["away_team"], m["league_id"])
    sim = monte.simulate_match(pred["home_xg"], pred["away_xg"])
    pred["monte_carlo"] = sim
    return jsonify(pred)

if __name__ == "__main__":
    print("Warming up prediction engine...")
    get_engine()
    print("Engine ready!")
    app.run(host="0.0.0.0", port=7890, debug=False)
