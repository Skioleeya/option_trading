use longport::quote::{CalcIndex, OptionDirection, OptionType};
use num_traits::ToPrimitive;
use pyo3::exceptions::PyRuntimeError;
use pyo3::PyResult;
use std::time::{SystemTime, UNIX_EPOCH};
use time::{format_description::parse as parse_time_format, Date};

pub fn now_unix_nanos() -> u64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_nanos() as u64,
        Err(_) => 0,
    }
}

pub fn non_negative_volume_to_u64(value: i64) -> u64 {
    if value > 0 {
        value as u64
    } else {
        0
    }
}

pub fn parse_calc_index(name: &str) -> Option<CalcIndex> {
    match name.trim() {
        "LastDone" => Some(CalcIndex::LastDone),
        "ChangeValue" => Some(CalcIndex::ChangeValue),
        "ChangeRate" => Some(CalcIndex::ChangeRate),
        "Volume" => Some(CalcIndex::Volume),
        "Turnover" => Some(CalcIndex::Turnover),
        "YtdChangeRate" => Some(CalcIndex::YtdChangeRate),
        "TurnoverRate" => Some(CalcIndex::TurnoverRate),
        "TotalMarketValue" => Some(CalcIndex::TotalMarketValue),
        "CapitalFlow" => Some(CalcIndex::CapitalFlow),
        "Amplitude" => Some(CalcIndex::Amplitude),
        "VolumeRatio" => Some(CalcIndex::VolumeRatio),
        "PeTtmRatio" => Some(CalcIndex::PeTtmRatio),
        "PbRatio" => Some(CalcIndex::PbRatio),
        "DividendRatioTtm" => Some(CalcIndex::DividendRatioTtm),
        "FiveDayChangeRate" => Some(CalcIndex::FiveDayChangeRate),
        "TenDayChangeRate" => Some(CalcIndex::TenDayChangeRate),
        "HalfYearChangeRate" => Some(CalcIndex::HalfYearChangeRate),
        "FiveMinutesChangeRate" => Some(CalcIndex::FiveMinutesChangeRate),
        "ExpiryDate" => Some(CalcIndex::ExpiryDate),
        "StrikePrice" => Some(CalcIndex::StrikePrice),
        "UpperStrikePrice" => Some(CalcIndex::UpperStrikePrice),
        "LowerStrikePrice" => Some(CalcIndex::LowerStrikePrice),
        "OutstandingQty" => Some(CalcIndex::OutstandingQty),
        "OutstandingRatio" => Some(CalcIndex::OutstandingRatio),
        "Premium" => Some(CalcIndex::Premium),
        "ItmOtm" => Some(CalcIndex::ItmOtm),
        "ImpliedVolatility" => Some(CalcIndex::ImpliedVolatility),
        "WarrantDelta" => Some(CalcIndex::WarrantDelta),
        "CallPrice" => Some(CalcIndex::CallPrice),
        "ToCallPrice" => Some(CalcIndex::ToCallPrice),
        "EffectiveLeverage" => Some(CalcIndex::EffectiveLeverage),
        "LeverageRatio" => Some(CalcIndex::LeverageRatio),
        "ConversionRatio" => Some(CalcIndex::ConversionRatio),
        "BalancePoint" => Some(CalcIndex::BalancePoint),
        "OpenInterest" => Some(CalcIndex::OpenInterest),
        "Delta" => Some(CalcIndex::Delta),
        "Gamma" => Some(CalcIndex::Gamma),
        "Theta" => Some(CalcIndex::Theta),
        "Vega" => Some(CalcIndex::Vega),
        "Rho" => Some(CalcIndex::Rho),
        _ => None,
    }
}

pub fn parse_iso_date(value: &str) -> PyResult<Date> {
    let format =
        parse_time_format("[year]-[month]-[day]").map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    Date::parse(value, &format).map_err(|e| PyRuntimeError::new_err(format!("invalid date '{value}': {e}")))
}

pub fn format_iso_date(value: Date) -> String {
    match parse_time_format("[year]-[month]-[day]") {
        Ok(format) => value.format(&format).unwrap_or_else(|_| value.to_string()),
        Err(_) => value.to_string(),
    }
}

pub fn format_compact_date(value: Date) -> String {
    match parse_time_format("[year][month][day]") {
        Ok(format) => value.format(&format).unwrap_or_else(|_| format_iso_date(value)),
        Err(_) => format_iso_date(value),
    }
}

pub fn option_type_code(value: OptionType) -> Option<&'static str> {
    match value {
        OptionType::American => Some("A"),
        OptionType::Europe => Some("U"),
        OptionType::Unknown => None,
    }
}

pub fn option_direction_code(value: OptionDirection) -> Option<&'static str> {
    match value {
        OptionDirection::Put => Some("P"),
        OptionDirection::Call => Some("C"),
        OptionDirection::Unknown => None,
    }
}

pub fn decimal_to_f64<T: ToPrimitive>(value: T) -> f64 {
    value.to_f64().unwrap_or_default()
}

pub fn option_string(value: Option<&str>) -> Option<String> {
    value.map(str::to_owned)
}
