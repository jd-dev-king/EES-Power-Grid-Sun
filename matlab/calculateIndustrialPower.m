function metrics = calculateIndustrialPower(voltageV, currentA, powerFactor, phases, efficiency)
arguments
    voltageV (1,1) double {mustBePositive}
    currentA (1,1) double {mustBeNonnegative}
    powerFactor (1,1) double {mustBeGreaterThan(powerFactor,0),mustBeLessThanOrEqual(powerFactor,1)}
    phases (1,1) double {mustBeMember(phases,[1 3])} = 3
    efficiency (1,1) double {mustBeGreaterThan(efficiency,0),mustBeLessThanOrEqual(efficiency,1)} = 1
end
if phases == 3
    apparentKVA = sqrt(3) * voltageV * currentA / 1000;
else
    apparentKVA = voltageV * currentA / 1000;
end
realKW = apparentKVA * powerFactor;
reactiveKVAR = sqrt(max(apparentKVA^2 - realKW^2,0));
metrics = struct("real_power_kw",realKW,"reactive_power_kvar",reactiveKVAR, ...
    "apparent_power_kva",apparentKVA,"mechanical_power_kw",realKW*efficiency);
end
