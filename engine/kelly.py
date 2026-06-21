"""Kelly Criterion for optimal bet sizing."""
import math


class KellyCriterion:
    """Calculate optimal bet size using Kelly Criterion."""

    @staticmethod
    def calculate(probability: float, decimal_odds: float, bankroll: float = 10000,
                  fraction: float = 0.25) -> dict:
        """Full Kelly: f* = (bp - q) / b where b = decimal_odds - 1.
        
        Args:
            probability: Estimated win probability (0-1)
            decimal_odds: Bookmaker odds in decimal format
            bankroll: Current bankroll
            fraction: Kelly fraction (0.25 = quarter Kelly, safer)
        """
        b = decimal_odds - 1  # net odds
        q = 1 - probability
        
        if b <= 0:
            return {"error": "Odds must be > 1.0", "bet": 0, "ev": 0}
        
        # Full Kelly
        f_star = (b * probability - q) / b
        f_star = max(0, f_star)  # No negative bets
        
        # Fractional Kelly
        bet_size = f_star * fraction * bankroll
        
        # Expected value
        ev = (probability * decimal_odds) - 1
        
        return {
            "kelly_pct": round(f_star * 100, 2),
            "bet_amount": round(bet_size, 2),
            "bet_pct_of_bankroll": round(f_star * fraction * 100, 2),
            "expected_value": round(ev * 100, 2),
            "recommendation": "BET" if f_star > 0.01 else "SKIP" if f_star > 0 else "NO_BET",
            "edge": round((probability * decimal_odds - 1) * 100, 2),
        }

    @staticmethod
    def kelly_for_parlay(parlay_prob: float, parlay_odds: float, bankroll: float = 10000) -> dict:
        """Kelly for a parlay bet."""
        return KellyCriterion.calculate(parlay_prob, parlay_odds, bankroll, fraction=0.1)
