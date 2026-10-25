"""Typed contracts between layers. A row that fails its contract is blocked and logged in
silver.rejects with the reason; it never reaches gold."""
from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CashFlowRow(BaseModel):
    ref: str
    position_id: str
    kind: Literal["call", "dist", "purchase"]
    amount: float = Field(gt=0)
    recallable: float = Field(ge=0, default=0.0)
    notice_date: dt.date
    value_date: dt.date
    doc_id: str

    @field_validator("recallable")
    @classmethod
    def _rec(cls, v, info):
        amt = info.data.get("amount")
        if amt is not None and v > amt + 1e-9:
            raise ValueError("recallable exceeds amount")
        return v


class ReportRow(BaseModel):
    fund_id: str
    as_of: dt.date
    learnt: dt.date
    fund_nav: float = Field(ge=0)
    lp_share: float = Field(gt=0, le=1)
    lp_nav: float = Field(ge=0)
    reported_irr: float | None
    reported_tvpi: float | None
    doc_id: str

    @field_validator("learnt")
    @classmethod
    def _after(cls, v, info):
        if "as_of" in info.data and v < info.data["as_of"]:
            raise ValueError("report learnt before its as-of date")
        return v


class HoldingRow(BaseModel):
    fund_id: str
    as_of: dt.date
    learnt: dt.date
    name_reported: str = Field(min_length=2)
    value: float = Field(ge=0)
    doc_id: str
    via: Literal["own", "fof_copy"]


class EventRow(BaseModel):
    event_id: str
    doc_id: str
    manager_id: str
    kind: Literal["write_down", "exit", "team_change", "restatement", "extension", "incident", "concern"]
    company_name: str | None = None
    person_name: str | None = None
    fund_id: str | None = None
    coinvest_id: str | None = None
    factor: float | None = None
    effective: dt.date
    learnt: dt.date
    confidence: float = Field(ge=0, le=1)
    status: Literal["accepted", "waiting_for_review"]
    quote: str
