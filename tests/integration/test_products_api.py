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


async def _create_batch(client, batch_number: int = 101) -> int:
    response = await client.post("/api/v1/batches", json=[_batch_payload(batch_number)])
    return response.json()[0]["id"]


async def test_add_product(client):
    batch_id = await _create_batch(client, 801)

    response = await client.post(
        "/api/v1/products",
        json={"unique_code": "UC-001", "batch_id": batch_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["unique_code"] == "UC-001"
    assert body["batch_id"] == batch_id
    assert body["is_aggregated"] is False


async def test_add_product_duplicate_conflicts(client):
    batch_id = await _create_batch(client, 802)

    first = await client.post(
        "/api/v1/products",
        json={"unique_code": "UC-DUP", "batch_id": batch_id},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/products",
        json={"unique_code": "UC-DUP", "batch_id": batch_id},
    )
    assert second.status_code == 409


async def test_add_product_to_missing_batch(client):
    response = await client.post(
        "/api/v1/products",
        json={"unique_code": "UC-X", "batch_id": 99999},
    )

    assert response.status_code == 404


async def test_aggregate_products(client):
    batch_id = await _create_batch(client, 803)
    for code in ["A1", "A2", "A3"]:
        await client.post(
            "/api/v1/products",
            json={"unique_code": code, "batch_id": batch_id},
        )

    response = await client.post(
        f"/api/v1/products/batches/{batch_id}/aggregate",
        json={"unique_codes": ["A1", "A2"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["aggregated"] == 2
    assert body["total"] == 2
    assert body["failed"] == 0


async def test_aggregate_unknown_codes_report_failed(client):
    batch_id = await _create_batch(client, 804)

    response = await client.post(
        f"/api/v1/products/batches/{batch_id}/aggregate",
        json={"unique_codes": ["MISSING-1", "MISSING-2"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["failed"] == 2
    assert body["aggregated"] == 0
