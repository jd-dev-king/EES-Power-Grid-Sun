from math import sqrt

def three_phase_metrics(voltage_v: float, current_a: float, power_factor: float, efficiency: float = 1.0) -> dict:
    apparent_kva = sqrt(3) * voltage_v * current_a / 1000
    real_kw = apparent_kva * power_factor
    reactive_kvar = sqrt(max(apparent_kva**2 - real_kw**2, 0))
    mechanical_kw = real_kw * efficiency
    return {"apparent_power_kva": apparent_kva, "real_power_kw": real_kw,
            "reactive_power_kvar": reactive_kvar, "mechanical_power_kw": mechanical_kw}

def single_phase_metrics(voltage_v: float, current_a: float, power_factor: float) -> dict:
    apparent_kva = voltage_v * current_a / 1000
    real_kw = apparent_kva * power_factor
    reactive_kvar = sqrt(max(apparent_kva**2 - real_kw**2, 0))
    return {"apparent_power_kva": apparent_kva, "real_power_kw": real_kw,
            "reactive_power_kvar": reactive_kvar}
