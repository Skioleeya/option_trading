"""Active Option model.

Represents a single option contract in the 'ACTIVE OPTIONS' table.
"""

from typing import Literal
from pydantic import BaseModel

class ActiveOption(BaseModel):
    symbol: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    implied_volatility: float
    volume: int
    turnover: float
    flow: float
