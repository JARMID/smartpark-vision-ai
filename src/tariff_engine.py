"""
Smart Park - Progressive Tiered Tariff Calculation Engine.
Implements standard Algerian municipal parking schedules, grace periods,
daily maximum caps, reduced mobility discounts, and lost ticket fees.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
from typing import Dict, Any, Optional, List


@dataclass
class TariffSchedule:
    """Configurable tariff rules for parking operations."""
    grace_period_min: int = 15
    first_hour_rate_dzd: float = 100.0
    tier2_hourly_rate_dzd: float = 50.0  # Hours 2 to 4
    tier3_hourly_rate_dzd: float = 30.0  # Hours 5 and beyond
    daily_cap_dzd: float = 800.0         # 24-hour maximum cap per vehicle
    lost_ticket_flat_dzd: float = 1500.0 # Fixed administrative fee for lost ticket
    lost_ticket_penalty_dzd: float = 500.0  # Surcharge added when entry time is verified
    pmr_discount_ratio: float = 0.50     # 50% discount for disabled drivers
    currency: str = "DZD"


class TariffEngine:
    """
    Computes parking fees using progressive tiered rates with 24-hour cycle caps.
    """

    def __init__(self, schedule: Optional[TariffSchedule] = None):
        self.schedule = schedule or TariffSchedule()

    def calculate_fee(
        self,
        entry_time: datetime,
        exit_time: Optional[datetime] = None,
        is_vip: bool = False,
        is_pmr: bool = False,
        is_lost_ticket: bool = False,
        flat_lost_ticket: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate total parking dues based on duration, vehicle class, and ticket status.
        """
        now = exit_time or datetime.now()
        duration_seconds = max(0, int((now - entry_time).total_seconds()))
        duration_minutes = duration_seconds // 60

        # VIP subscribers park without charge
        if is_vip:
            return {
                "duration_minutes": duration_minutes,
                "billable_hours": 0,
                "is_grace_period": False,
                "is_vip": True,
                "is_pmr": False,
                "is_lost_ticket": False,
                "base_amount_dzd": 0.0,
                "discount_dzd": 0.0,
                "total_due_dzd": 0.0,
                "breakdown": "Abonnement VIP / Gratuité Permanente",
                "currency": self.schedule.currency,
                "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Flat lost ticket without verifiable entry record
        if is_lost_ticket and flat_lost_ticket:
            total_due = self.schedule.lost_ticket_flat_dzd
            if is_pmr:
                total_due = round(total_due * self.schedule.pmr_discount_ratio, 2)
            return {
                "duration_minutes": duration_minutes,
                "billable_hours": 0,
                "is_grace_period": False,
                "is_vip": False,
                "is_pmr": is_pmr,
                "is_lost_ticket": True,
                "base_amount_dzd": self.schedule.lost_ticket_flat_dzd,
                "discount_dzd": round(self.schedule.lost_ticket_flat_dzd - total_due, 2),
                "total_due_dzd": total_due,
                "breakdown": f"Forfait Ticket Perdu ({self.schedule.lost_ticket_flat_dzd:.0f} DZD)",
                "currency": self.schedule.currency,
                "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Initial drop-off grace period check
        if duration_minutes <= self.schedule.grace_period_min:
            return {
                "duration_minutes": duration_minutes,
                "billable_hours": 0,
                "is_grace_period": True,
                "is_vip": False,
                "is_pmr": is_pmr,
                "is_lost_ticket": False,
                "base_amount_dzd": 0.0,
                "discount_dzd": 0.0,
                "total_due_dzd": 0.0,
                "breakdown": f"Franchise Gratuite ({self.schedule.grace_period_min} min)",
                "currency": self.schedule.currency,
                "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Progressive tiered billing
        total_hours = math.ceil(duration_minutes / 60.0)
        days = total_hours // 24
        remainder_hours = total_hours % 24

        base_due = 0.0

        # Calculate remainder hours within the current day block
        if remainder_hours > 0:
            day_due = 0.0
            # Hour 1
            day_due += self.schedule.first_hour_rate_dzd
            # Hours 2 to 4
            tier2_hours = max(0, min(remainder_hours - 1, 3))
            day_due += tier2_hours * self.schedule.tier2_hourly_rate_dzd
            # Hours 5+
            tier3_hours = max(0, remainder_hours - 4)
            day_due += tier3_hours * self.schedule.tier3_hourly_rate_dzd

            # Apply daily cap on remainder
            base_due += min(day_due, self.schedule.daily_cap_dzd)

        # Add full 24-hour days capped at daily max
        base_due += days * self.schedule.daily_cap_dzd

        # Add lost ticket penalty if entry time was verified but ticket is physically missing
        lost_surcharge = self.schedule.lost_ticket_penalty_dzd if is_lost_ticket else 0.0
        base_due += lost_surcharge

        # Apply PMR discount if qualified
        discount = 0.0
        if is_pmr:
            discount = round(base_due * (1.0 - self.schedule.pmr_discount_ratio), 2)
            total_due = round(base_due - discount, 2)
        else:
            total_due = round(base_due, 2)

        breakdown_parts: List[str] = []
        if days > 0:
            breakdown_parts.append(f"{days} jour(s) x {self.schedule.daily_cap_dzd:.0f} DZD")
        if remainder_hours > 0:
            breakdown_parts.append(f"{remainder_hours} heure(s) en tarif progressif")
        if lost_surcharge > 0:
            breakdown_parts.append(f"Majoration ticket perdu (+{lost_surcharge:.0f} DZD)")
        if is_pmr:
            breakdown_parts.append("Remise PMR 50%")

        breakdown_text = " + ".join(breakdown_parts) if breakdown_parts else "Tarif standard"

        return {
            "duration_minutes": duration_minutes,
            "billable_hours": total_hours,
            "is_grace_period": False,
            "is_vip": False,
            "is_pmr": is_pmr,
            "is_lost_ticket": is_lost_ticket,
            "base_amount_dzd": round(base_due, 2),
            "discount_dzd": discount,
            "total_due_dzd": total_due,
            "breakdown": breakdown_text,
            "currency": self.schedule.currency,
            "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_schedule_summary(self) -> Dict[str, Any]:
        """Return clean dictionary describing current active tariff schedule."""
        return {
            "grace_period_minutes": self.schedule.grace_period_min,
            "first_hour_rate_dzd": self.schedule.first_hour_rate_dzd,
            "tier2_hourly_rate_dzd": self.schedule.tier2_hourly_rate_dzd,
            "tier3_hourly_rate_dzd": self.schedule.tier3_hourly_rate_dzd,
            "daily_cap_dzd": self.schedule.daily_cap_dzd,
            "lost_ticket_flat_dzd": self.schedule.lost_ticket_flat_dzd,
            "lost_ticket_penalty_dzd": self.schedule.lost_ticket_penalty_dzd,
            "pmr_discount_percent": int(self.schedule.pmr_discount_ratio * 100),
            "currency": self.schedule.currency,
        }
