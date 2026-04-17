from datetime import date, datetime


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


async def test_create_batch_with_russian_fields(client):
    response = await client.post("/api/v1/batches", json=[_batch_payload()])

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["batch_number"] == 101
    assert body[0]["is_closed"] is False
    assert body[0]["nomenclature"] == "Молоко 2.5% 1л"


async def test_create_batch_duplicate_conflicts(client):
    payload = _batch_payload(batch_number=202)

    first = await client.post("/api/v1/batches", json=[payload])
    assert first.status_code == 201

    second = await client.post("/api/v1/batches", json=[payload])
    assert second.status_code == 409


async def test_get_batch_returns_data(client):
    created = await client.post("/api/v1/batches", json=[_batch_payload(batch_number=303)])
    batch_id = created.json()[0]["id"]

    response = await client.get(f"/api/v1/batches/{batch_id}")

    assert response.status_code == 200
    assert response.json()["id"] == batch_id


async def test_get_batch_not_found(client):
    response = await client.get("/api/v1/batches/99999")

    assert response.status_code == 404


async def test_update_batch_sets_closed_at(client):
    created = await client.post("/api/v1/batches", json=[_batch_payload(batch_number=404)])
    batch_id = created.json()[0]["id"]

    response = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"is_closed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_closed"] is True
    assert body["closed_at"] is not None


async def test_update_batch_reopen_clears_closed_at(client):
    created = await client.post(
        "/api/v1/batches",
        json=[_batch_payload(batch_number=505, **{"СтатусЗакрытия": True})],
    )
    batch_id = created.json()[0]["id"]

    response = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"is_closed": False},
    )

    assert response.status_code == 200
    assert response.json()["closed_at"] is None


async def test_list_batches_paginates(client):
    for n in range(3):
        await client.post("/api/v1/batches", json=[_batch_payload(batch_number=600 + n)])

    response = await client.get("/api/v1/batches?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2


async def test_list_batches_filters_by_shift(client):
    await client.post("/api/v1/batches", json=[_batch_payload(batch_number=701, **{"Смена": "Ночная"})])
    await client.post("/api/v1/batches", json=[_batch_payload(batch_number=702, **{"Смена": "Дневная"})])

    response = await client.get("/api/v1/batches?shift=Ночная")

    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["shift"] == "Ночная" for item in items)
    assert any(item["batch_number"] == 701 for item in items)
