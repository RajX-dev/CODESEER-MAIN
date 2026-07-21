# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

"""
Central pricing constants and tier definitions for N3MO SaaS.

All pricing, limits, and feature lists are defined here as the single
source of truth.  Every other module (API server, webhook handler,
frontend data endpoints) must import from this module instead of
hardcoding values.
"""

from __future__ import annotations

import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

TRIAL_DAYS = 15
UNLIMITED = -1

PRICING_TIERS: dict[str, dict] = {
    "standard": {
        "id": "standard",
        "name": "Standard Plan",
        "price_usd": 19,
        "price_in_cents": 1900,
        "repos_limit": 1,
        "loc_per_repo": 30_000,
        "max_total_loc": 30_000,
        "billing_cycle_days": 30,
        "features": [
            "1 repository",
            "Up to 30K lines of code",
            "Real-time PR Impact Analysis",
            "Interactive Dependency Graph",
            "Built-in MCP Server for AI Agents",
            "Community support",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro Plan",
        "price_usd": 69,
        "price_in_cents": 6900,
        "repos_limit": 3,
        "loc_per_repo": 100_000,
        "max_total_loc": 300_000,
        "billing_cycle_days": 30,
        "features": [
            "Up to 3 repositories",
            "Up to 100K lines of code per repo",
            "Everything in Standard",
            "Priority indexing queue",
            "Email notifications",
            "Multi-repo dashboard",
            "Email & community support",
        ],
    },
    "team_basic": {
        "id": "team_basic",
        "name": "Team Basic",
        "price_usd": 1,
        "price_in_cents": 100,
        "repos_limit": 5,
        "loc_per_repo": 200_000,
        "max_total_loc": 1_000_000,
        "billing_cycle_days": 30,
        "features": [
            "Up to 5 repositories",
            "Up to 200K lines of code per repo",
            "Everything in Pro",
            "Monorepo support",
            "Team workspaces & RBAC",
            "Slack integration",
            "Org-level dashboard",
            "Priority SLA support",
        ],
    },
    "team_pro": {
        "id": "team_pro",
        "name": "Team Pro",
        "price_usd": 399,
        "price_in_cents": 39900,
        "repos_limit": 7,
        "loc_per_repo": 500_000,
        "max_total_loc": 3_500_000,
        "billing_cycle_days": 30,
        "features": [
            "Up to 7 repositories",
            "Up to 500K lines of code per repo",
            "Everything in Team Basic",
            "Advanced Org RBAC",
            "Custom webhooks",
            "Priority SLA support",
        ],
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise Plan",
        "price_usd": None,
        "price_in_cents": None,
        "repos_limit": UNLIMITED,
        "loc_per_repo": UNLIMITED,
        "max_total_loc": UNLIMITED,
        "billing_cycle_days": 30,
        "features": [
            "Unlimited repos",
            "Unlimited lines of code",
            "Everything in Team Pro",
            "SSO / SAML authentication",
            "Audit logs",
            "Self-hosted deployment option",
            "Dedicated Support Engineer",
            "Custom SLA",
        ],
    },
}

# Ordered list of tier IDs from lowest to highest for upgrade suggestions.
TIER_ORDER: list[str] = ["standard", "pro", "team_basic", "team_pro", "enterprise"]

# ---------------------------------------------------------------------------
# Razorpay configuration
# ---------------------------------------------------------------------------

RAZORPAY_CONFIG: dict[str, object] = {
    "currency": "INR",
    "timeout": 900,  # 15 minutes to complete payment
    "tier_descriptions": {
        "standard": "N3MO Standard Plan - 1 Month",
        "pro": "N3MO Pro Plan - 1 Month",
        "team_basic": "N3MO Team Basic Plan - 1 Month",
        "team_pro": "N3MO Team Pro Plan - 1 Month",
    },
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_tier(tier_id: str) -> Optional[dict]:
    """Return the tier definition for *tier_id*, or ``None``."""
    return PRICING_TIERS.get(tier_id)


def get_tier_for_upgrade(total_loc: int, repo_count: int) -> Optional[str]:
    """Return the cheapest tier that supports *total_loc* and *repo_count*.

    Returns ``None`` if no tier can accommodate the requirements (should
    not happen with the current tiers, but guards against future changes).
    """
    for tier_id in TIER_ORDER:
        tier = PRICING_TIERS[tier_id]
        if (tier["repos_limit"] == UNLIMITED or repo_count <= tier["repos_limit"]) and \
           (tier["max_total_loc"] == UNLIMITED or total_loc <= tier["max_total_loc"]):
            return tier_id
    return None


def calculate_upgrade_bonus_days(current_expires_at: Optional[datetime.datetime]) -> int:
    """Return the number of remaining days on an existing plan.

    If the subscription is already expired or *current_expires_at* is
    ``None``, returns ``0``.
    """
    if current_expires_at is None:
        return 0

    now = datetime.datetime.now(datetime.timezone.utc)

    # Ensure timezone awareness by defaulting to UTC if naive
    if current_expires_at.tzinfo is None:
        current_expires_at = current_expires_at.replace(tzinfo=datetime.timezone.utc)

    exp_utc = current_expires_at.astimezone(datetime.timezone.utc)
    remaining = (exp_utc - now).days
    return max(remaining, 0)


def validate_eligibility(
    tier_id: str,
    repo_count: int,
    per_repo_locs: list[int],
) -> tuple[bool, str]:
    """Check whether a user's codebase fits within *tier_id* limits.

    Parameters
    ----------
    tier_id:
        The tier the user wants to purchase.
    repo_count:
        Number of repositories the user has connected.
    per_repo_locs:
        LOC count for each connected repository.

    Returns
    -------
    (is_eligible, error_message)
        ``(True, "")`` when the user qualifies, otherwise
        ``(False, "<human-readable reason>")`` with a suggestion.
    """
    if repo_count < 0 or not isinstance(per_repo_locs, list):
        return False, "Invalid input"

    if len(per_repo_locs) != repo_count:
        return False, "LOC list size mismatch"

    if any(loc < 0 for loc in per_repo_locs):
        return False, "Negative LOC not allowed"

    tier = get_tier(tier_id)
    if tier is None:
        return False, f"Unknown tier: '{tier_id}'."

    # Check repo limit
    if tier["repos_limit"] != UNLIMITED and repo_count > tier["repos_limit"]:
        suggested = get_tier_for_upgrade(sum(per_repo_locs), repo_count)
        suggestion = f" Consider the {PRICING_TIERS[suggested]['name']}." if suggested else ""
        return (
            False,
            f"The {tier['name']} supports up to {tier['repos_limit']} "
            f"repositories, but you have {repo_count}.{suggestion}",
        )

    # Check per-repo LOC limit
    if tier["loc_per_repo"] != UNLIMITED:
        for loc in per_repo_locs:
            if loc > tier["loc_per_repo"]:
                suggested = get_tier_for_upgrade(sum(per_repo_locs), repo_count)
                suggestion = f" Consider the {PRICING_TIERS[suggested]['name']}." if suggested else ""
                return (
                    False,
                    f"One of your repositories has {loc:,} lines of code, "
                    f"which exceeds the {tier['name']} limit of "
                    f"{tier['loc_per_repo']:,} per repo.{suggestion}",
                )

    # Check total LOC cap
    total_loc = sum(per_repo_locs)
    if tier["max_total_loc"] != UNLIMITED and total_loc > tier["max_total_loc"]:
        suggested = get_tier_for_upgrade(total_loc, repo_count)
        suggestion = f" Consider the {PRICING_TIERS[suggested]['name']}." if suggested else ""
        return (
            False,
            f"Your total codebase is {total_loc:,} lines, which exceeds "
            f"the {tier['name']} cap of {tier['max_total_loc']:,}.{suggestion}",
        )

    return True, ""
