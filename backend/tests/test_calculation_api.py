import pytest
from test_vessels_api import Base, client, engine, vessel_payload


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def calculation_payload(vessel_id: str) -> dict:
    return {
        "vessel_id": vessel_id,
        "name": "КП: оптимальный план",
        "vessel_data_revision": "course-project-reference",
        "coordinate_convention": "Начало в AP на ОП; X в нос, Y на ЛБ, Z вверх.",
        "lbp_m": 283.1,
        "seawater_density_t_m3": 1.018,
        "lightship": {
            "mass_t": 47087.2,
            "lcg_m": 119.245,
            "tcg_m": -0.106,
            "vcg_m": 16.538,
            "source_reference": "КП, таблица 1.3, стр. 6",
        },
        "items": [{
            "name": "Сводная переменная нагрузка",
            "mass_t": 90717.2,
            "lcg_m": 152.59,
            "tcg_m": 0.12,
            "vcg_m": 16.77,
            "free_surface_moment_tm": 141922.4,
            "source_reference": "КП, таблица оптимального плана, стр. 17",
        }],
        "hydrostatic_table": [
            {
                "displacement_volume_m3": 134919,
                "draft_extreme_m": 12.65,
                "lcf_from_ap_m": 129.61,
                "lcb_from_ap_m": 141.39,
                "transverse_metacentre_z_m": 25.44,
                "mct_t_m_per_cm": 2780.6,
                "source_reference": "Информация об остойчивости, PDF стр. 82, строка 12.65 м",
            },
            {
                "displacement_volume_m3": 135573,
                "draft_extreme_m": 12.70,
                "lcf_from_ap_m": 129.49,
                "lcb_from_ap_m": 141.33,
                "transverse_metacentre_z_m": 25.41,
                "mct_t_m_per_cm": 2792.7,
                "source_reference": "Информация об остойчивости, PDF стр. 82, строка 12.70 м",
            },
        ],
        "kn_curve": [
            {"heel_angle_deg": angle, "kn_m": kn,
             "source_reference": f"Информация об остойчивости, кривая KN, угол {angle}°"}
            for angle, kn in [(0, 0), (10, 4.429), (20, 8.785), (30, 13.061), (40, 15.975)]
        ],
    }


def test_calculation_endpoint_persists_an_immutable_estimate():
    vessel = client.post("/api/v1/vessels", json=vessel_payload()).json()
    response = client.post(
        "/api/v1/calculations/loading-condition",
        json=calculation_payload(vessel["id"]),
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "ESTIMATE_ONLY"
    outputs = result["calculation_result"]["outputs"]
    assert outputs["displacement_t"] == 137804.4
    assert outputs["corrected_initial_gm_m"] == pytest.approx(7.70, abs=0.02)
    assert outputs["mean_draft_m"] == pytest.approx(12.72, abs=0.02)
    stability = result["calculation_result"]["stability_curve"]
    assert stability["status"] == "ESTIMATE_ONLY"
    assert stability["area_to_30_deg_m_rad"] > 1.0

    history = client.get(f"/api/v1/vessels/{vessel['id']}/calculation-runs")
    assert history.status_code == 200
    assert history.json()[0]["id"] == result["id"]

    details = client.get(f"/api/v1/calculation-runs/{result['id']}")
    assert details.status_code == 200
    assert details.json()["calculation_input"]["lightship"]["source_reference"] == (
        "КП, таблица 1.3, стр. 6"
    )
    assert len(details.json()["calculation_input"]["kn_curve"]) == 5
    assert details.json()["calculation_result"] == result["calculation_result"]


def test_calculation_endpoint_rejects_hydrostatic_extrapolation():
    vessel = client.post("/api/v1/vessels", json=vessel_payload()).json()
    payload = calculation_payload(vessel["id"])
    payload["items"][0]["mass_t"] = 150000
    response = client.post("/api/v1/calculations/loading-condition", json=payload)
    assert response.status_code == 422
    assert "extrapolation is prohibited" in response.json()["detail"]
