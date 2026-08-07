function forecast = requestForecast(apiBaseUrl, scope, horizonMinutes)
arguments
    apiBaseUrl (1,1) string
    scope (1,1) string = "CAMPUS"
    horizonMinutes (1,1) double = 15
end
payload = struct("scope",scope,"horizon_minutes",horizonMinutes);
opts = weboptions(MediaType="application/json",Timeout=30);
forecast = webwrite(apiBaseUrl + "/api/v1/forecasts",payload,opts);
end
