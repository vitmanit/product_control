async def test_create_webhook(client):
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["batch_created", "batch_closed"],
            "secret_key": "super-secret",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com/hook"
    assert body["events"] == ["batch_created", "batch_closed"]
    assert body["is_active"] is True
    assert "secret_key" not in body  # секрет не должен возвращаться


async def test_list_webhooks(client):
    await client.post(
        "/api/v1/webhooks",
        json={"url": "https://a.com", "events": ["batch_created"], "secret_key": "k1"},
    )
    await client.post(
        "/api/v1/webhooks",
        json={"url": "https://b.com", "events": ["batch_updated"], "secret_key": "k2"},
    )

    response = await client.get("/api/v1/webhooks")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_update_webhook(client):
    created = await client.post(
        "/api/v1/webhooks",
        json={"url": "https://a.com", "events": ["batch_created"], "secret_key": "k"},
    )
    webhook_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/webhooks/{webhook_id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_delete_webhook(client):
    created = await client.post(
        "/api/v1/webhooks",
        json={"url": "https://a.com", "events": ["batch_created"], "secret_key": "k"},
    )
    webhook_id = created.json()["id"]

    delete_resp = await client.delete(f"/api/v1/webhooks/{webhook_id}")
    assert delete_resp.status_code == 204

    list_resp = await client.get("/api/v1/webhooks")
    assert list_resp.json()["total"] == 0


async def test_update_missing_webhook_404(client):
    response = await client.patch("/api/v1/webhooks/99999", json={"is_active": False})

    assert response.status_code == 404
