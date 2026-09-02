import pytest

from services.energia_service import (
    get_plant_status,
    get_region_consumption,
    get_simulation_step,
    list_plants,
    list_regions,
)


def test_list_regions_returns_expected_structure():
    result = list_regions()

    assert isinstance(result, dict)
    assert "count" in result
    assert "regions" in result
    assert isinstance(result["regions"], list)
    assert result["count"] == len(
        result["regions"]
    )
    assert result["count"] > 0


def test_list_plants_returns_expected_structure():
    result = list_plants()

    assert isinstance(result, dict)
    assert "count" in result
    assert "plants" in result
    assert isinstance(result["plants"], list)
    assert result["count"] == len(
        result["plants"]
    )
    assert result["count"] > 0


def test_get_existing_plant():
    result = get_plant_status("golfech")

    assert result["plant_id"] == "golfech"
    assert "maximum_power_mw" in result
    assert "available" in result


def test_plant_identifier_is_normalized():
    result = get_plant_status(
        "  GOLFECH  "
    )

    assert result["plant_id"] == "golfech"


def test_unknown_plant_returns_controlled_error():
    with pytest.raises(
        ValueError,
        match="Centrale inconnue",
    ):
        get_plant_status(
            "centrale-inconnue"
        )


def test_get_region_consumption():
    result = get_region_consumption(
        "occitanie",
        "18:00",
    )

    assert result["region_id"] == "occitanie"
    assert result["timestamp"] == "18:00"
    assert "consumption_mw" in result
    assert result["consumption_mw"] >= 0


def test_unknown_region_returns_controlled_error():
    with pytest.raises(
        ValueError,
        match="Région inconnue",
    ):
        get_region_consumption(
            "region-inconnue",
            "18:00",
        )


def test_unknown_timestamp_returns_controlled_error():
    with pytest.raises(
        ValueError,
        match="Horaire inconnu",
    ):
        get_region_consumption(
            "occitanie",
            "99:00",
        )


def test_get_simulation_step():
    result = get_simulation_step("18:00")

    assert result["timestamp"] == "18:00"
    assert "total_consumption_mw" in result
    assert "production_mw" in result
    assert "plants" in result
    assert "situation" in result