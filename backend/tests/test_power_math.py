from app.services.power_math import three_phase_metrics

def test_three_phase_power():
    result = three_phase_metrics(480, 100, .9, .92)
    assert 74 < result["real_power_kw"] < 76
    assert result["apparent_power_kva"] > result["real_power_kw"]
