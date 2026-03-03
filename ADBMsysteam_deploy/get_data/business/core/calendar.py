"""
美股广度数据生成者系统 - 交易日历模块
提供交易日和节假日判断功能（长期有效）
"""

from datetime import datetime, date, timedelta

import holidays
from zoneinfo import ZoneInfo


class TradingCalendar:
    """
    统一处理美国股市交易日历、节假日、提前收盘
    使用 holidays.US，并补充复活节相关节假日
    """

    def __init__(self) -> None:
        self.tz_ny = ZoneInfo("America/New_York")
        self.us_holidays = holidays.US(years=range(2020, 2040))

    def _ensure_holidays_loaded(self, year: int) -> None:
        if year not in self.us_holidays.years:
            self.us_holidays.years.add(year)

    def is_holiday(self, date_obj: date) -> bool:
        self._ensure_holidays_loaded(date_obj.year)

        if date_obj in self.us_holidays:
            return True

        easter = self._calculate_easter(date_obj.year)
        good_friday = easter - timedelta(days=2)
        return date_obj == good_friday

    def is_trading_day(self, dt: datetime) -> bool:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.tz_ny)
        else:
            dt = dt.astimezone(self.tz_ny)

        if dt.weekday() >= 5:
            return False

        return not self.is_holiday(dt.date())

    def is_early_close_day(self, date_obj: date) -> bool:
        self._ensure_holidays_loaded(date_obj.year)

        thanksgiving = self._get_thanksgiving(date_obj.year)
        if thanksgiving:
            day_after = thanksgiving + timedelta(days=1)
            if day_after.weekday() < 5 and not self.is_holiday(day_after):
                if date_obj == day_after:
                    return True

        christmas = date(date_obj.year, 12, 25)
        christmas_eve = christmas - timedelta(days=1)
        if christmas_eve.weekday() < 5 and not self.is_holiday(christmas_eve):
            return date_obj == christmas_eve

        return False

    def _calculate_easter(self, year: int) -> date:
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    def _get_thanksgiving(self, year: int) -> date | None:
        first_day = date(year, 11, 1)
        first_weekday = first_day.weekday()
        days_to_first_thursday = (3 - first_weekday) % 7
        first_thursday = first_day + timedelta(days=days_to_first_thursday)
        return first_thursday + timedelta(weeks=3)


trading_calendar = TradingCalendar()
