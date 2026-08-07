function response = sendTelemetry(apiBaseUrl, apiKey, telemetry)
arguments
    apiBaseUrl (1,1) string
    apiKey (1,1) string
    telemetry (1,1) struct
end
opts = weboptions(MediaType="application/json", Timeout=20, ...
    HeaderFields=["X-API-Key",apiKey]);
response = webwrite(apiBaseUrl + "/api/v1/power/telemetry", telemetry, opts);
end
