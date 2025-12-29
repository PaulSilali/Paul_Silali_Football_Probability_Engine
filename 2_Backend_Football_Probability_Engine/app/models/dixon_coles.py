"""
Dixon-Coles Poisson Model for Football Match Prediction

Reference: "Modelling Association Football Scores and Inefficiencies 
in the Football Betting Market" (Dixon & Coles, 1997)

Key Concepts:
- Attack/Defense strength parameters per team
- Home advantage factor
- Low-score dependency parameter (ρ)
- Exponential time decay (ξ)
"""
import math
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class TeamStrength:
    """Team strength parameters"""
    team_id: int
    attack: float  # α_i
    defense: float  # β_i
    league_id: Optional[int] = None


@dataclass
class DixonColesParams:
    """Dixon-Coles model parameters"""
    rho: float = -0.13  # Dependency parameter
    xi: float = 0.0065  # Time decay (per day)
    home_advantage: float = 0.35  # Global home advantage


@dataclass
class GoalExpectations:
    """Expected goals for a match"""
    lambda_home: float
    lambda_away: float


@dataclass
class MatchProbabilities:
    """Match outcome probabilities"""
    home: float  # P(Home Win)
    draw: float  # P(Draw)
    away: float  # P(Away Win)
    entropy: float
    lambda_home: Optional[float] = None
    lambda_away: Optional[float] = None


def factorial(n: int) -> int:
    """Calculate factorial"""
    if n < 0:
        return 0
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def poisson_probability(lambda_val: float, k: int) -> float:
    """
    Poisson probability: P(X = k) = (λ^k * e^(-λ)) / k!
    """
    if lambda_val <= 0 or k < 0:
        return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / factorial(k)


def tau_adjustment(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float
) -> float:
    """
    Dixon-Coles adjustment factor for low scores
    
    τ(x, y, λ_home, λ_away, ρ) adjusts probabilities for:
    - (0,0), (1,0), (0,1), (1,1)
    """
    # Only adjust for low-score combinations
    if home_goals > 1 or away_goals > 1:
        return 1.0
    
    if home_goals == 0 and away_goals == 0:
        return 1 - lambda_home * lambda_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + lambda_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + lambda_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    
    return 1.0


def calculate_expected_goals(
    home_team: TeamStrength,
    away_team: TeamStrength,
    params: DixonColesParams
) -> GoalExpectations:
    """
    Calculate expected goals for a match
    
    λ_home = exp(α_home - β_away + γ)
    λ_away = exp(α_away - β_home)
    
    where γ is home advantage
    """
    lambda_home = math.exp(
        home_team.attack - away_team.defense + params.home_advantage
    )
    
    lambda_away = math.exp(
        away_team.attack - home_team.defense
    )
    
    return GoalExpectations(lambda_home=lambda_home, lambda_away=lambda_away)


def score_joint_probability(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float
) -> float:
    """
    Calculate joint probability of a score
    
    P(X=x, Y=y) = τ(x,y) * Poisson(x; λ_home) * Poisson(y; λ_away)
    """
    poisson_home = poisson_probability(lambda_home, home_goals)
    poisson_away = poisson_probability(lambda_away, away_goals)
    tau = tau_adjustment(home_goals, away_goals, lambda_home, lambda_away, rho)
    
    return tau * poisson_home * poisson_away


def calculate_match_probabilities(
    home_team: TeamStrength,
    away_team: TeamStrength,
    params: DixonColesParams,
    max_goals: int = 8
) -> MatchProbabilities:
    """
    Calculate match outcome probabilities
    
    P(Home) = Σ P(x, y) for x > y
    P(Draw) = Σ P(x, x) for all x
    P(Away) = Σ P(x, y) for x < y
    """
    expectations = calculate_expected_goals(home_team, away_team, params)
    lambda_home = expectations.lambda_home
    lambda_away = expectations.lambda_away
    
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0
    
    # Sum over all possible scores up to max_goals
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = score_joint_probability(
                h, a, lambda_home, lambda_away, params.rho
            )
            
            if h > a:
                prob_home += prob
            elif h == a:
                prob_draw += prob
            else:
                prob_away += prob
    
    # Normalize (should sum to ~1.0 already)
    total = prob_home + prob_draw + prob_away
    if total > 0:
        prob_home /= total
        prob_draw /= total
        prob_away /= total
    
    # Calculate entropy
    entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [prob_home, prob_draw, prob_away]
    )
    
    return MatchProbabilities(
        home=prob_home,
        draw=prob_draw,
        away=prob_away,
        entropy=entropy,
        lambda_home=lambda_home,
        lambda_away=lambda_away
    )


def max_probability_outcome(probs: MatchProbabilities) -> str:
    """Get the outcome with highest probability"""
    if probs.home >= probs.draw and probs.home >= probs.away:
        return "H"
    elif probs.draw >= probs.away:
        return "D"
    else:
        return "A"

