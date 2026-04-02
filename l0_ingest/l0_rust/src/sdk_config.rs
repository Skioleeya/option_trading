use longport::{Config, Language};

pub fn build_sdk_config(
    app_key: String,
    app_secret: String,
    access_token: String,
    http_url: Option<String>,
    quote_ws_url: Option<String>,
    trade_ws_url: Option<String>,
    language: Option<String>,
    enable_overnight: bool,
) -> Result<Config, String> {
    let mut config = Config::new(app_key, app_secret, access_token);
    if let Some(value) = http_url.filter(|value| !value.trim().is_empty()) {
        config = config.http_url(value);
    }
    if let Some(value) = quote_ws_url.filter(|value| !value.trim().is_empty()) {
        config = config.quote_ws_url(value);
    }
    if let Some(value) = trade_ws_url.filter(|value| !value.trim().is_empty()) {
        config = config.trade_ws_url(value);
    }
    if let Some(value) = language.filter(|value| !value.trim().is_empty()) {
        config = config.language(parse_language(&value)?);
    }
    if enable_overnight {
        config = config.enable_overnight();
    }
    Ok(config)
}

fn parse_language(value: &str) -> Result<Language, String> {
    match value.trim().to_ascii_uppercase().as_str() {
        "EN" => Ok(Language::EN),
        "ZH_CN" | "ZH-CN" => Ok(Language::ZH_CN),
        "ZH_HK" | "ZH-HK" => Ok(Language::ZH_HK),
        other => Err(format!("unsupported language '{other}'")),
    }
}
