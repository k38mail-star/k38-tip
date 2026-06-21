"""Odds collection from API-Football."""
import json, time, sqlite3, os
from datetime import datetime
from urllib.request import Request, urlopen


class OddsCollector:
    """Fetch and store betting odds from API-Football."""

    API_BASE = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key=None, db_path="/opt/k38-football/football.db"):
        self.api_key = api_key or os.getenv("K38_FOOTBALL_API_KEY")
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS football_odds (
                fixture_id INTEGER,
                bookmaker TEXT,
                bet_type TEXT,
                odd_value REAL,
                market TEXT,
                updated_at TEXT,
                PRIMARY KEY (fixture_id, bookmaker, bet_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS football_stats_detail (
                fixture_id INTEGER,
                team TEXT,
                stat_type TEXT,
                stat_value TEXT,
                PRIMARY KEY (fixture_id, team, stat_type)
            )
        """)
        conn.commit()
        conn.close()

    def fetch_odds_for_fixture(self, fixture_id):
        """Fetch odds for a specific fixture."""
        req = Request(f"{self.API_BASE}/odds?fixture={fixture_id}",
                      headers={"x-apisports-key": self.api_key})
        try:
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

        odds_data = []
        for bookmaker in data.get("response", []):
            bm_name = bookmaker.get("name", "unknown")
            for bet in bookmaker.get("bets", []):
                btype = bet.get("name", "")
                for val in bet.get("values", []):
                    odds_data.append({
                        "fixture_id": fixture_id,
                        "bookmaker": bm_name,
                        "bet_type": btype,
                        "odd_value": float(val.get("odd", 0)),
                        "market": val.get("value", ""),
                        "updated_at": datetime.now().isoformat(),
                    })

        if odds_data:
            conn = sqlite3.connect(self.db_path)
            conn.executemany("""
                INSERT OR REPLACE INTO football_odds
                (fixture_id, bookmaker, bet_type, odd_value, market, updated_at)
                VALUES (:fixture_id, :bookmaker, :bet_type, :odd_value, :market, :updated_at)
            """, odds_data)
            conn.commit()
            conn.close()

        return {"fixture_id": fixture_id, "odds_found": len(odds_data)}

    def fetch_stats_for_fixture(self, fixture_id):
        """Fetch detailed statistics for a fixture."""
        req = Request(f"{self.API_BASE}/fixtures/statistics?fixture={fixture_id}",
                      headers={"x-apisports-key": self.api_key})
        try:
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

        stats_records = []
        for team_stats in data.get("response", []):
            team = team_stats.get("team", {}).get("name", "")
            for stat in team_stats.get("statistics", []):
                stype = stat.get("type", "")
                sval = stat.get("value")
                stats_records.append({
                    "fixture_id": fixture_id,
                    "team": team,
                    "stat_type": stype,
                    "stat_value": str(sval) if sval is not None else "0",
                })

        if stats_records:
            conn = sqlite3.connect(self.db_path)
            conn.executemany("""
                INSERT OR REPLACE INTO football_stats_detail
                (fixture_id, team, stat_type, stat_value)
                VALUES (:fixture_id, :team, :stat_type, :stat_value)
            """, stats_records)
            conn.commit()
            conn.close()

        return {"fixture_id": fixture_id, "stats_found": len(stats_records)}

    def backfill_finished(self, limit=30):
        """Backfill odds and stats for recent finished matches."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("""
            SELECT fixture_id FROM football_matches
            WHERE status = 'Finished'
            ORDER BY match_date DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        results = []
        for (fid,) in rows:
            o = self.fetch_odds_for_fixture(fid)
            s = self.fetch_stats_for_fixture(fid)
            results.append({"fixture_id": fid, "odds": o, "stats": s})
            time.sleep(1.2)  # Rate limit

        return {"backfilled": len(results), "results": results}
