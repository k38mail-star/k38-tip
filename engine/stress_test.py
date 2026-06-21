"""Stress Testing & Monte Carlo simulation for bankroll risk analysis."""
import random, math


class StressTest:
    """Run stress tests on betting strategies."""

    @staticmethod
    def simulate(probabilities: list, bankroll: float = 10000, bet_size: float = 100,
                 n_simulations: int = 10000) -> dict:
        """Monte Carlo simulation of a betting session.
        
        Args:
            probabilities: List of (win_prob, decimal_odds) tuples
            bankroll: Starting bankroll
            bet_size: Fixed bet amount per play
            n_simulations: Number of full session simulations
        """
        final_bankrolls = []
        max_drawdowns = []
        losing_streaks = []
        win_counts = []

        for _ in range(n_simulations):
            br = bankroll
            peak = br
            dd = 0
            streak = 0
            wins = 0
            max_streak = 0

            for prob, odds in probabilities:
                if br < bet_size:
                    break
                br -= bet_size
                if random.random() < prob:
                    br += bet_size * odds
                    wins += 1
                    streak = 0
                else:
                    streak += 1
                    max_streak = max(max_streak, streak)
                peak = max(peak, br)
                dd = max(dd, peak - br)

            final_bankrolls.append(br)
            max_drawdowns.append(dd)
            losing_streaks.append(max_streak)
            win_counts.append(wins)

        final_bankrolls.sort()
        max_drawdowns.sort()

        return {
            "n_simulations": n_simulations,
            "starting_bankroll": bankroll,
            "avg_final_bankroll": round(sum(final_bankrolls) / n_simulations, 2),
            "median_final_bankroll": final_bankrolls[n_simulations // 2],
            "worst_case_5pct": final_bankrolls[int(n_simulations * 0.05)],
            "best_case_5pct": final_bankrolls[int(n_simulations * 0.95)],
            "avg_max_drawdown": round(sum(max_drawdowns) / n_simulations, 2),
            "worst_drawdown_5pct": max_drawdowns[int(n_simulations * 0.95)],
            "avg_losing_streak": round(sum(losing_streaks) / n_simulations, 1),
            "worst_losing_streak": max(losing_streaks),
            "ruin_probability": round(
                sum(1 for br in final_bankrolls if br <= 0) / n_simulations, 4
            ),
            "profit_probability": round(
                sum(1 for br in final_bankrolls if br > bankroll) / n_simulations, 4
            ),
        }

    @staticmethod
    def simulate_parlay_strategy(parlay_hit_rate: float, parlay_odds: float,
                                  bankroll: float = 10000, bet_pct: float = 0.02,
                                  n_bets: int = 100, n_sim: int = 5000) -> dict:
        """Stress test a parlay betting strategy."""
        bets = [(parlay_hit_rate, parlay_odds)] * n_bets
        return StressTest.simulate(bets, bankroll, bankroll * bet_pct, n_sim)
