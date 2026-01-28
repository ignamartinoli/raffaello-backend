from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ContractActivityPolicy:
    """Defines what it means for a contract to be active "as of" a given date.

    Semantics (intentionally centralized):
    - A contract is active if start_date <= as_of
    - AND (end_date is None OR end_date >= as_of)

    Note: end_date is inclusive. A contract ending "today" is still active today.
    """

    as_of: date

    def is_active(self, *, start_date: date, end_date: date | None) -> bool:
        return (start_date <= self.as_of) and (end_date is None or end_date >= self.as_of)

    def is_inactive(self, *, start_date: date, end_date: date | None) -> bool:
        # Negation of the active rule, expressed in a query-friendly way.
        return (start_date > self.as_of) or (end_date is not None and end_date < self.as_of)

    def sqlalchemy_active_predicate(self, *, start_col, end_col):
        """Build a SQLAlchemy predicate implementing the active rule.

        Kept here so repositories can translate the policy into SQL without
        redefining the boundary conditions.
        """
        from sqlalchemy import and_, or_

        return and_(
            start_col <= self.as_of,
            or_(
                end_col.is_(None),
                end_col >= self.as_of,
            ),
        )

    def sqlalchemy_inactive_predicate(self, *, start_col, end_col):
        """Build a SQLAlchemy predicate implementing the inactive rule."""
        from sqlalchemy import and_, or_

        return or_(
            start_col > self.as_of,
            and_(
                end_col.isnot(None),
                end_col < self.as_of,
            ),
        )

