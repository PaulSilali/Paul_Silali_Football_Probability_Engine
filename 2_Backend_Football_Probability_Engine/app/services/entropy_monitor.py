"""
Entropy Drift Monitoring Service

Tracks entropy drift over time to detect when models become
dangerously overconfident.

Entropy collapse = model becoming dangerously confident.
"""
from typing import List, Optional
from statistics import mean, quantiles
import logging

logger = logging.getLogger(__name__)


class EntropyMonitor:
    """
    Tracks entropy drift over time.
    
    Monitors average entropy and percentiles to detect:
    - Sudden entropy drops (overconfidence)
    - Sustained low entropy (model degradation)
    - Entropy collapse (critical issue)
    """
    
    def __init__(
        self,
        warning_threshold: float = 0.45,
        critical_threshold: float = 0.35
    ):
        """
        Args:
            warning_threshold: Average entropy below this triggers warning
            critical_threshold: Average entropy below this triggers critical alert
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def evaluate(self, entropies: List[float]) -> dict:
        """
        Evaluate entropy distribution and return status.
        
        Args:
            entropies: List of entropy values (normalized to [0,1])
        
        Returns:
            Dictionary with:
                - avg_entropy: Average entropy
                - p10_entropy: 10th percentile
                - p90_entropy: 90th percentile
                - status: "ok", "warning", or "critical"
        """
        if not entropies:
            return {
                "avg_entropy": None,
                "p10_entropy": None,
                "p90_entropy": None,
                "status": "unknown"
            }
        
        avg_entropy = mean(entropies)
        
        # Calculate percentiles
        try:
            q = quantiles(entropies, n=10)
            p10 = q[0]
            p90 = q[-1]
        except:
            # Fallback if quantiles fails
            sorted_ents = sorted(entropies)
            p10 = sorted_ents[int(len(sorted_ents) * 0.1)] if len(sorted_ents) > 0 else 0.0
            p90 = sorted_ents[int(len(sorted_ents) * 0.9)] if len(sorted_ents) > 0 else 1.0
        
        # Determine status
        status = "ok"
        if avg_entropy < self.critical_threshold:
            status = "critical"
        elif avg_entropy < self.warning_threshold:
            status = "warning"
        
        return {
            "avg_entropy": round(avg_entropy, 4),
            "p10_entropy": round(p10, 4),
            "p90_entropy": round(p90, 4),
            "status": status
        }


def summarize_entropy(entropies: List[float]) -> dict:
    """
    Convenience function to summarize entropy distribution.
    
    Args:
        entropies: List of entropy values (normalized to [0,1])
    
    Returns:
        Dictionary with entropy statistics and status
    """
    monitor = EntropyMonitor()
    return monitor.evaluate(entropies)

