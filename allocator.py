"""DAFB — Demand-Adaptive Floors with Buffer.

Reference implementation of the allocation algorithm specified in DESIGN.md.
Allocates a flat per-period token budget B across users with heterogeneous,
heavy-tailed demand:

  Stage A: per-user EWMA demand forecast with deviation headroom
  Stage B: max-min entitlement floors  f_i = min(d_i, B/n)
  Stage C: utilization-earned-weight water-filling on residual demand
  Buffer:  unassigned residual stays liquid for mid-period overage draws

Stdlib only. See test_allocator.py for the property suite (P1-P6).
"""

from __future__ import annotations

from dataclasses import dataclass, field


def water_fill(residuals: list[float], weights: list[float], target: float) -> list[float]:
    """Exact weighted water-filling.

    Returns grants g_i = min(r_i, w_i * lam) with lam chosen so that
    sum(g) == min(target, sum(residuals)), computed exactly by sorting the
    saturation breakpoints r_i / w_i (no numerical tolerance loop).

    residuals must be >= 0 and weights strictly > 0.
    """
    if len(residuals) != len(weights):
        raise ValueError("residuals and weights must have equal length")
    if any(r < 0 for r in residuals):
        raise ValueError("residuals must be non-negative")
    if any(w <= 0 for w in weights):
        raise ValueError("weights must be strictly positive")

    total_demand = sum(residuals)
    target = max(0.0, min(target, total_demand))
    if target == 0.0:
        return [0.0] * len(residuals)
    if target == total_demand:
        return list(residuals)

    # Sort users by the water level at which they saturate.
    order = sorted(range(len(residuals)), key=lambda i: residuals[i] / weights[i])
    sat_sum = 0.0                      # demand already fully granted
    w_rest = sum(weights)              # total weight of unsaturated users
    lam = 0.0
    k = 0
    for k, i in enumerate(order):
        b = residuals[i] / weights[i]
        # If everyone still unsaturated were filled to level b, would we
        # overshoot the target?  Then lam lies below b: solve and stop.
        if sat_sum + b * w_rest >= target:
            lam = (target - sat_sum) / w_rest
            break
        sat_sum += residuals[i]
        w_rest -= weights[i]
    else:  # pragma: no cover - target < total_demand guarantees a break
        lam = (target - sat_sum) / w_rest if w_rest > 0 else 0.0

    return [min(r, w * lam) for r, w in zip(residuals, weights)]


@dataclass
class UserState:
    """Per-user EWMA state tracked across periods."""

    mean: float = 0.0        # EWMA of realized usage (m_i)
    deviation: float = 0.0   # EWMA of |usage - mean| (v_i)
    utilization: float = 1.0  # EWMA of min(1, used/granted); optimistic start
    probe: float = 0.0       # saturation probe: gamma * usage while capped
    has_history: bool = False


@dataclass
class Allocation:
    """Result of one period's allocation."""

    quotas: dict[str, float]
    buffer: float
    forecasts: dict[str, float]
    floors: dict[str, float]
    weights: dict[str, float]

    @property
    def total(self) -> float:
        return sum(self.quotas.values()) + self.buffer


@dataclass
class DAFBAllocator:
    """Demand-Adaptive Floors with Buffer allocator.

    Parameters (defaults per DESIGN.md):
      budget   flat per-period token budget B
      alpha    EWMA smoothing for demand mean/deviation
      kappa    deviation headroom multiplier in the forecast
      w_min    weight floor so every user remains fillable in Stage C
      gamma    saturation-probe multiplier (slow-start style demand uncensoring)
      sat_threshold  fraction of grant consumed that counts as saturated
    """

    budget: float
    alpha: float = 0.3
    kappa: float = 1.0
    w_min: float = 0.25
    gamma: float = 1.5
    sat_threshold: float = 0.95
    users: dict[str, UserState] = field(default_factory=dict)
    _buffer_remaining: float = 0.0

    def add_user(self, user_id: str) -> None:
        if user_id not in self.users:
            self.users[user_id] = UserState()

    def forecast(self, user_id: str) -> float:
        """Stage A: d_i = max(m_i + kappa * v_i, probe); cold start = equal share.

        The probe term uncensors demand: a user who consumed >= sat_threshold
        of their grant was likely capped, so their forecast is bumped to
        gamma * usage until they stop saturating (TCP-slow-start style).
        """
        s = self.users[user_id]
        if not s.has_history:
            return self.budget / len(self.users)
        return max(s.mean + self.kappa * s.deviation, s.probe)

    def weight(self, user_id: str) -> float:
        """Earned weight from demonstrated utilization (w_min..1]."""
        return self.w_min + (1.0 - self.w_min) * self.users[user_id].utilization

    def allocate(self) -> Allocation:
        """Run Stages A-C for the coming period and arm the burst buffer."""
        if not self.users:
            raise ValueError("no users registered")
        ids = list(self.users)
        n = len(ids)
        d = {i: self.forecast(i) for i in ids}
        w = {i: self.weight(i) for i in ids}

        equal_share = self.budget / n
        floors = {i: min(d[i], equal_share) for i in ids}

        residual_budget = self.budget - sum(floors.values())
        residual_demand = [d[i] - floors[i] for i in ids]
        grants = water_fill(residual_demand, [w[i] for i in ids], residual_budget)

        quotas = {i: floors[i] + g for i, g in zip(ids, grants)}
        buffer = self.budget - sum(quotas.values())
        self._buffer_remaining = buffer
        return Allocation(quotas=quotas, buffer=buffer, forecasts=d,
                          floors=floors, weights=w)

    def draw_buffer(self, amount: float) -> float:
        """Mid-period overage draw; grants up to the remaining buffer."""
        if amount < 0:
            raise ValueError("draw must be non-negative")
        granted = min(amount, self._buffer_remaining)
        self._buffer_remaining -= granted
        return granted

    @property
    def buffer_remaining(self) -> float:
        return self._buffer_remaining

    def observe(self, usage: dict[str, float], allocation: Allocation) -> None:
        """End of period: fold realized usage into per-user EWMA state."""
        for i, state in self.users.items():
            u = usage.get(i, 0.0)
            if u < 0:
                raise ValueError(f"negative usage for {i}")
            granted = allocation.quotas.get(i, 0.0)
            util = min(1.0, u / granted) if granted > 0 else state.utilization
            saturated = granted > 0 and u >= self.sat_threshold * granted
            state.probe = self.gamma * u if saturated else 0.0
            if state.has_history:
                state.deviation = (self.alpha * abs(u - state.mean)
                                   + (1 - self.alpha) * state.deviation)
                state.mean = self.alpha * u + (1 - self.alpha) * state.mean
                state.utilization = (self.alpha * util
                                     + (1 - self.alpha) * state.utilization)
            else:
                state.mean = u
                state.deviation = 0.0
                state.utilization = util
                state.has_history = True


@dataclass
class DAFBv2Allocator:
    """Buffer-first redesign (Phase 3 falsified v1's forecast-heavy quotas).

    Architecture inversion, motivated by the ablation result that the liquid
    pool's demand-revealing draws beat forecast-based pre-assignment:

      Floors: f_i = min(EWMA(u_i), floor_frac * B/n) — small, conservative,
              demand-capped; they exist for predictability and no-starvation,
              not to serve peak demand. No headroom, no probing.
      Pool:   B - sum(floors) — maximal by construction (>= (1-floor_frac)B).
      Draws:  the pool is distributed per period against realized excess
              demand; this allocator contributes earned draw WEIGHTS
              (w_min + (1-w_min)*EWMA(utilization)) so experienced heavy
              users win contention without shrinking the pool.

    The draw itself happens in the serving layer (benchmark adapter /
    production gateway), which calls draw_weights() and runs a weighted
    water-fill (or a frictional discipline) over the pool.
    """

    budget: float
    alpha: float = 0.3
    floor_frac: float = 0.5
    w_min: float = 0.25
    users: dict[str, UserState] = field(default_factory=dict)

    def add_user(self, user_id: str) -> None:
        if user_id not in self.users:
            self.users[user_id] = UserState()

    def forecast(self, user_id: str) -> float:
        """Plain EWMA mean; cold start = equal share."""
        s = self.users[user_id]
        if not s.has_history:
            return self.budget / len(self.users)
        return s.mean

    def draw_weights(self) -> dict[str, float]:
        """Earned pool-draw weights in (w_min..1]."""
        return {i: self.w_min + (1.0 - self.w_min) * s.utilization
                for i, s in self.users.items()}

    def allocate(self) -> Allocation:
        if not self.users:
            raise ValueError("no users registered")
        ids = list(self.users)
        n = len(ids)
        cap = self.floor_frac * self.budget / n
        d = {i: self.forecast(i) for i in ids}
        floors = {i: min(d[i], cap) for i in ids}
        buffer = self.budget - sum(floors.values())
        return Allocation(quotas=floors, buffer=buffer, forecasts=d,
                          floors=floors, weights=self.draw_weights())

    def observe(self, usage: dict[str, float], allocation: Allocation) -> None:
        """Fold realized usage (incl. pool draws) into EWMA state.

        Utilization is measured against floor + what the user actually
        received above it (their realized usage is exactly that when they
        consumed everything), capped at 1.
        """
        for i, state in self.users.items():
            u = usage.get(i, 0.0)
            if u < 0:
                raise ValueError(f"negative usage for {i}")
            granted = allocation.quotas.get(i, 0.0)
            util = min(1.0, u / granted) if granted > 0 else state.utilization
            if state.has_history:
                state.mean = self.alpha * u + (1 - self.alpha) * state.mean
                state.utilization = (self.alpha * util
                                     + (1 - self.alpha) * state.utilization)
            else:
                state.mean = u
                state.utilization = util
                state.has_history = True
