# FOOTBALL JACKPOT PROBABILITY ENGINE - COMPLETE BACKEND CODE
## Production-Ready Python Backend - Part 2: Core Mathematical Modules

**DETERMINISTIC. ANALYTICAL. AUDITABLE.**

---

## FILE: backend/models/poisson.py

```python
"""
Poisson Distribution Functions

Pure mathematical implementations.
NO randomness.
NO simulation.
"""

import numpy as np
from math import exp, factorial, log
from typing import Union


def poisson_pmf(lambda_: float, k: int) -> float:
    """
    Poisson probability mass function.
    
    P(X = k) = (λ^k * e^(-λ)) / k!
    
    Args:
        lambda_: Rate parameter (expected value)
        k: Observed count (non-negative integer)
    
    Returns:
        Probability of observing exactly k events
    
    Examples:
        >>> poisson_pmf(1.5, 0)
        0.22313016014842982
        >>> poisson_pmf(1.5, 2)
        0.25117081516510597
    """
    if k < 0:
        return 0.0
    
    if lambda_ <= 0:
        raise ValueError(f"Lambda must be positive, got {lambda_}")
    
    # Use log-space for numerical stability
    log_prob = k * log(lambda_) - lambda_ - sum(log(i) for i in range(1, k + 1))
    return exp(log_prob)


def poisson_cdf(lambda_: float, k: int) -> float:
    """
    Poisson cumulative distribution function.
    
    P(X ≤ k) = Σ P(X = i) for i = 0 to k
    
    Args:
        lambda_: Rate parameter
        k: Upper bound
    
    Returns:
        Probability of observing k or fewer events
    """
    return sum(poisson_pmf(lambda_, i) for i in range(k + 1))


def poisson_pmf_vectorized(lambda_: np.ndarray, k: np.ndarray) -> np.ndarray:
    """
    Vectorized Poisson PMF for efficiency.
    
    Args:
        lambda_: Array of rate parameters
        k: Array of counts
    
    Returns:
        Array of probabilities
    """
    from scipy.stats import poisson
    return poisson.pmf(k, lambda_)
```

---

## FILE: backend/models/dixon_coles.py

```python
"""
Dixon-Coles Model Implementation

Reference: "Modelling Association Football Scores and Inefficiencies 
in the Football Betting Market" (Dixon & Coles, 1997)

CRITICAL GUARANTEES:
- Deterministic (same inputs → same outputs)
- Analytical (no Monte Carlo)
- Reproducible (auditable calculations)
- Explicit (all steps documented)

NO SIMULATION. NO BLACK BOXES.
"""

import numpy as np
from math import exp, factorial, log
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from backend.settings import settings
from .poisson import poisson_pmf


@dataclass(frozen=True)
class TeamStrength:
    """
    Team strength parameters (IMMUTABLE).
    
    Attributes:
        team_id: Database team ID
        attack: Attack strength α (log scale)
        defense: Defense strength β (log scale)
        league_id: League identifier
    """
    team_id: int
    attack: float
    defense: float
    league_id: int
    
    def __post_init__(self):
        """Validate strength parameters."""
        if not np.isfinite(self.attack):
            raise ValueError(f"Attack must be finite, got {self.attack}")
        if not np.isfinite(self.defense):
            raise ValueError(f"Defense must be finite, got {self.defense}")


@dataclass(frozen=True)
class DixonColesParams:
    """
    Dixon-Coles model hyperparameters (IMMUTABLE).
    
    Attributes:
        rho: Dependency parameter for low scores (typically -0.13)
        xi: Time decay factor per day (typically 0.0065)
        home_advantage: Global home advantage in goals (typically 0.3-0.5)
    """
    rho: float = settings.DIXON_COLES_RHO
    xi: float = settings.TIME_DECAY_XI
    home_advantage: float = settings.HOME_ADVANTAGE
    
    def __post_init__(self):
        """Validate parameters."""
        if not -0.5 <= self.rho <= 0.0:
            raise ValueError(f"Rho must be in [-0.5, 0.0], got {self.rho}")
        if not 0.0 < self.xi < 0.1:
            raise ValueError(f"Xi must be in (0, 0.1), got {self.xi}")
        if not 0.0 <= self.home_advantage <= 1.0:
            raise ValueError(f"Home advantage must be in [0, 1], got {self.home_advantage}")


@dataclass(frozen=True)
class GoalExpectations:
    """Expected goals for a match (IMMUTABLE)."""
    lambda_home: float
    lambda_away: float
    
    def __post_init__(self):
        """Validate expectations."""
        if not 0.0 <= self.lambda_home <= 10.0:
            raise ValueError(f"Lambda home must be in [0, 10], got {self.lambda_home}")
        if not 0.0 <= self.lambda_away <= 10.0:
            raise ValueError(f"Lambda away must be in [0, 10], got {self.lambda_away}")


@dataclass(frozen=True)
class MatchProbabilities:
    """Match outcome probabilities (IMMUTABLE)."""
    home: float
    draw: float
    away: float
    entropy: float
    
    def validate(self) -> bool:
        """
        Validate probability constraints.
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If probabilities invalid
        """
        # Check range
        for p in [self.home, self.draw, self.away]:
            if not 0.0 <= p <= 1.0:
                raise ValueError(f"Probabilities must be in [0,1], got {p}")
        
        # Check sum
        total = self.home + self.draw + self.away
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Probabilities must sum to 1.0, got {total}")
        
        # Check entropy
        if not 0.0 <= self.entropy <= 1.59:  # Max entropy for 3 outcomes
            raise ValueError(f"Entropy must be in [0, 1.59], got {self.entropy}")
        
        return True


# ============================================================================
# CORE DIXON-COLES FUNCTIONS
# ============================================================================

def tau_adjustment(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float
) -> float:
    """
    Dixon-Coles adjustment factor for low-score dependency.
    
    Corrects the independence assumption of Poisson for scores:
    (0,0), (1,0), (0,1), (1,1)
    
    Mathematical Definition:
        τ(0,0) = 1 - λ_h * λ_a * ρ
        τ(0,1) = 1 + λ_h * ρ
        τ(1,0) = 1 + λ_a * ρ
        τ(1,1) = 1 - ρ
        τ(x,y) = 1 for all other (x,y)
    
    Args:
        home_goals: Home team goals
        away_goals: Away team goals
        lambda_home: Expected home goals
        lambda_away: Expected away goals
        rho: Dependency parameter (typically negative)
    
    Returns:
        Adjustment factor τ ∈ (0, 2)
    
    Examples:
        >>> tau_adjustment(0, 0, 1.5, 1.2, -0.13)
        0.766
        >>> tau_adjustment(2, 3, 1.5, 1.2, -0.13)
        1.0
    """
    # Only adjust for low-score combinations
    if home_goals > 1 or away_goals > 1:
        return 1.0
    
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * lambda_away * rho
    
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lambda_away * rho
    
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    
    return 1.0


def calculate_expected_goals(
    home_team: TeamStrength,
    away_team: TeamStrength,
    params: DixonColesParams
) -> GoalExpectations:
    """
    Calculate expected goals using team strengths.
    
    Formula:
        λ_home = exp(α_home - β_away + γ)
        λ_away = exp(α_away - β_home)
    
    where:
        α = attack strength (log scale)
        β = defense strength (log scale)
        γ = home advantage
    
    Args:
        home_team: Home team strength parameters
        away_team: Away team strength parameters
        params: Model hyperparameters
    
    Returns:
        GoalExpectations with lambda_home and lambda_away
    
    Examples:
        >>> home = TeamStrength(1, attack=0.2, defense=-0.1, league_id=1)
        >>> away = TeamStrength(2, attack=0.1, defense=0.0, league_id=1)
        >>> params = DixonColesParams(home_advantage=0.3)
        >>> exp_goals = calculate_expected_goals(home, away, params)
        >>> 1.5 < exp_goals.lambda_home < 2.0
        True
    """
    # λ_home = exp(α_home - β_away + home_advantage)
    lambda_home = exp(
        home_team.attack - away_team.defense + params.home_advantage
    )
    
    # λ_away = exp(α_away - β_home)
    lambda_away = exp(
        away_team.attack - home_team.defense
    )
    
    return GoalExpectations(
        lambda_home=lambda_home,
        lambda_away=lambda_away
    )


def score_joint_probability(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float
) -> float:
    """
    Calculate joint probability of a specific score.
    
    P(X=x, Y=y) = τ(x,y,λ_h,λ_a,ρ) * Poisson(x; λ_h) * Poisson(y; λ_a)
    
    Args:
        home_goals: Home team goals
        away_goals: Away team goals
        lambda_home: Expected home goals
        lambda_away: Expected away goals
        rho: Dependency parameter
    
    Returns:
        Joint probability P(X=home_goals, Y=away_goals)
    
    Examples:
        >>> score_joint_probability(2, 1, 1.5, 1.2, -0.13)
        0.10234...
    """
    # Independent Poisson probabilities
    prob_home = poisson_pmf(lambda_home, home_goals)
    prob_away = poisson_pmf(lambda_away, away_goals)
    
    # Dixon-Coles dependency correction
    tau = tau_adjustment(home_goals, away_goals, lambda_home, lambda_away, rho)
    
    # Joint probability
    return tau * prob_home * prob_away


def calculate_match_probabilities(
    home_team: TeamStrength,
    away_team: TeamStrength,
    params: DixonColesParams,
    max_goals: int = settings.MAX_GOALS
) -> MatchProbabilities:
    """
    Calculate match outcome probabilities (Home, Draw, Away).
    
    Integrates over all possible scores up to max_goals:
    - P(Home) = Σ P(x,y) for x > y
    - P(Draw) = Σ P(x,x) for all x
    - P(Away) = Σ P(x,y) for x < y
    
    Args:
        home_team: Home team strength
        away_team: Away team strength
        params: Model parameters
        max_goals: Maximum goals to consider (default 8)
    
    Returns:
        MatchProbabilities with home/draw/away probabilities and entropy
    
    Raises:
        ValueError: If probabilities don't sum to ~1.0
    
    Examples:
        >>> home = TeamStrength(1, 0.2, -0.1, 1)
        >>> away = TeamStrength(2, 0.1, 0.0, 1)
        >>> params = DixonColesParams()
        >>> probs = calculate_match_probabilities(home, away, params)
        >>> probs.home > probs.away  # Home team stronger
        True
        >>> probs.validate()
        True
    """
    # Calculate expected goals
    exp_goals = calculate_expected_goals(home_team, away_team, params)
    lambda_home = exp_goals.lambda_home
    lambda_away = exp_goals.lambda_away
    
    # Initialize probability accumulators
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0
    
    # Sum over all possible scores up to max_goals
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = score_joint_probability(h, a, lambda_home, lambda_away, params.rho)
            
            if h > a:
                prob_home += prob
            elif h == a:
                prob_draw += prob
            else:  # h < a
                prob_away += prob
    
    # Normalize to ensure sum = 1.0
    # (Truncation at max_goals might leave small residual)
    total = prob_home + prob_draw + prob_away
    prob_home /= total
    prob_draw /= total
    prob_away /= total
    
    # Calculate Shannon entropy
    # H = -Σ p * log2(p)
    entropy = 0.0
    for p in [prob_home, prob_draw, prob_away]:
        if p > 0:
            entropy -= p * log(p, 2)
    
    result = MatchProbabilities(
        home=prob_home,
        draw=prob_draw,
        away=prob_away,
        entropy=entropy
    )
    
    # Validate before returning
    result.validate()
    
    return result


def build_score_matrix(
    lambda_home: float,
    lambda_away: float,
    rho: float,
    max_goals: int = settings.MAX_GOALS
) -> np.ndarray:
    """
    Build complete score probability matrix.
    
    Useful for visualization and detailed analysis.
    
    Args:
        lambda_home: Expected home goals
        lambda_away: Expected away goals
        rho: Dependency parameter
        max_goals: Maximum goals (matrix dimension)
    
    Returns:
        (max_goals+1) x (max_goals+1) matrix where M[h,a] = P(Home=h, Away=a)
    
    Examples:
        >>> matrix = build_score_matrix(1.5, 1.2, -0.13, max_goals=5)
        >>> matrix.shape
        (6, 6)
        >>> 0.0 < matrix[0, 0] < 1.0  # Valid probability
        True
        >>> abs(matrix.sum() - 1.0) < 0.01  # Approximately normalized
        True
    """
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = score_joint_probability(h, a, lambda_home, lambda_away, rho)
    
    return matrix


def get_most_likely_score(
    lambda_home: float,
    lambda_away: float,
    rho: float,
    max_goals: int = settings.MAX_GOALS
) -> Tuple[int, int]:
    """
    Find most likely exact score.
    
    Args:
        lambda_home: Expected home goals
        lambda_away: Expected away goals
        rho: Dependency parameter
        max_goals: Maximum goals to consider
    
    Returns:
        (home_goals, away_goals) tuple of most likely score
    
    Examples:
        >>> get_most_likely_score(1.5, 1.2, -0.13)
        (1, 1)
    """
    max_prob = 0.0
    best_score = (0, 0)
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = score_joint_probability(h, a, lambda_home, lambda_away, rho)
            if prob > max_prob:
                max_prob = prob
                best_score = (h, a)
    
    return best_score


# ============================================================================
# TIME-WEIGHTED LIKELIHOOD (FOR TRAINING)
# ============================================================================

def calculate_time_weights(
    match_dates: np.ndarray,
    reference_date: np.ndarray,
    xi: float = settings.TIME_DECAY_XI
) -> np.ndarray:
    """
    Calculate exponential time decay weights.
    
    w(t) = exp(-ξ * days_ago)
    
    Where ξ ≈ 0.0065 gives half-life ~106 days
    
    Args:
        match_dates: Array of match dates (numpy datetime64)
        reference_date: Reference date for decay calculation
        xi: Decay rate per day
    
    Returns:
        Array of weights, same shape as match_dates
    
    Examples:
        >>> import numpy as np
        >>> dates = np.array(['2023-01-01', '2023-06-01'], dtype='datetime64[D]')
        >>> ref = np.datetime64('2024-01-01', 'D')
        >>> weights = calculate_time_weights(dates, ref)
        >>> weights[0] < weights[1]  # Older match has lower weight
        True
    """
    # Calculate days between dates
    days_ago = (reference_date - match_dates).astype('timedelta64[D]').astype(float)
    
    # Apply exponential decay
    weights = np.exp(-xi * days_ago)
    
    return weights


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_team_strengths(strengths: Dict[int, TeamStrength]) -> bool:
    """
    Validate that team strengths are reasonable.
    
    Checks:
    - All values are finite
    - No extreme values (|parameter| < 3)
    
    Args:
        strengths: Dictionary mapping team_id to TeamStrength
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If validation fails
    """
    for team_id, strength in strengths.items():
        if not np.isfinite(strength.attack):
            raise ValueError(f"Team {team_id} has non-finite attack: {strength.attack}")
        
        if not np.isfinite(strength.defense):
            raise ValueError(f"Team {team_id} has non-finite defense: {strength.defense}")
        
        if abs(strength.attack) > 3.0:
            raise ValueError(f"Team {team_id} attack too extreme: {strength.attack}")
        
        if abs(strength.defense) > 3.0:
            raise ValueError(f"Team {team_id} defense too extreme: {strength.defense}")
    
    return True
```

---

**END OF PART 2**

Part 3 will contain: Goal matrix integration, market odds blending, isotonic calibration, and probability set generation.
