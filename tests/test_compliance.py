from pipeline.compliance import assess_maximum, assess_range, profile_is_applicable


def test_maximum_limit_states_are_forecast_states():
    assert assess_maximum("SS", 18, 30).status == "forecast_below_limit"
    assert assess_maximum("SS", 27, 30).status == "forecast_near_limit"
    result = assess_maximum("SS", 31, 30)
    assert result.status == "forecast_exceeds_limit"
    assert result.margin == -1


def test_missing_limit_is_never_treated_as_compliant():
    assert assess_maximum("COD", 72, None).status == "unassessed"


def test_ph_range_uses_nearest_boundary():
    result = assess_range("pH", 7.2, 6.0, 9.0)
    assert result.status == "forecast_below_limit"
    assert round(result.margin, 1) == 1.2
    assert assess_range("pH", 9.2, 6.0, 9.0).status == "forecast_exceeds_limit"


def test_profile_rejects_stricter_individual_requirement():
    profile = {"industry": "化工業", "dischargeRoute": "surface_water", "jurisdiction": "TW"}
    plant = {**profile, "stricterRequirementExists": True}
    applicable, reasons = profile_is_applicable(profile, plant)
    assert applicable is False
    assert "存在較嚴個案條件" in reasons[0]

