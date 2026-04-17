def _batch_payload(batch_number: int = 101, **overrides) -> dict:
    payload = {
        "СтатусЗакрытия": False,
        "ПредставлениеЗаданияНаСмену": "Сменное задание",
        "РабочийЦентр": "Линия розлива №1",
        "Смена": "Дневная",
        "Бригада": "Бригада А",
        "НомерПартии": batch_number,
        "ДатаПартии": "2026-04-17",
        "Номенклатура": "Молоко 2.5% 1л",
        "КодЕКН": "EKN-001",
        "ИдентификаторРЦ": "WC-01",
        "ДатаВремяНачалаСмены": "2026-04-17T08:00:00",
        "ДатаВремяОкончанияСмены": "2026-04-17T20:00:00",
    }
    payload.update(overrides)
    return payload


async def test_dashboard_returns_summary(client):
    await client.post("/api/v1/batches", json=[_batch_payload(901)])
    await client.post("/api/v1/batches", json=[_batch_payload(902, **{"СтатусЗакрытия": True})])

    response = await client.get("/api/v1/analytics/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_batches"] == 2
    assert body["summary"]["closed_batches"] == 1
    assert "by_shift" in body
    assert "top_work_centers" in body


async def test_batch_statistics(client):
    created = await client.post("/api/v1/batches", json=[_batch_payload(903)])
    batch_id = created.json()[0]["id"]

    response = await client.get(f"/api/v1/batches/{batch_id}/statistics")

    assert response.status_code == 200
    body = response.json()
    assert body["batch_info"]["id"] == batch_id
    assert "production_stats" in body
    assert "timeline" in body


async def test_compare_batches(client):
    c1 = await client.post("/api/v1/batches", json=[_batch_payload(904)])
    c2 = await client.post("/api/v1/batches", json=[_batch_payload(905)])

    response = await client.post(
        "/api/v1/analytics/compare-batches",
        json={"batch_ids": [c1.json()[0]["id"], c2.json()[0]["id"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["comparison"]) == 2
    assert "average" in body
