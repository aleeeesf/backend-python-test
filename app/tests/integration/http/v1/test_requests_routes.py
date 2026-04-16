"""Integration tests for request routes."""

from domain.entities.request import NotificationStatus


class TestRequestRoutes:
    """Test suite for request HTTP routes."""

    def test_creates_request_when_payload_is_valid(self, client):
        """POST /v1/requests returns 201 and a generated request ID."""
        # Arrange
        payload = {
            "to": "user@example.com",
            "message": "Test notification",
            "type": "email",
        }

        # Act
        response = client.post("/v1/requests", json=payload)
        body = response.json()

        # Assert
        assert response.status_code == 201
        assert isinstance(body["id"], str)
        assert body["id"]

    def test_returns_not_found_when_processing_unknown_request(self, client):
        """POST /v1/requests/{id}/process returns 404 for unknown request IDs."""
        # Act
        response = client.post("/v1/requests/missing-request/process")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Request not found"

    def test_returns_accepted_and_dispatches_when_processing_queued_request(
        self,
        client,
        stub_process_dispatcher,
    ):
        """POST /process returns 202 and dispatches queued requests."""
        # Arrange
        create_response = client.post(
            "/v1/requests",
            json={
                "to": "user@example.com",
                "message": "Test notification",
                "type": "email",
            },
        )
        request_id = create_response.json()["id"]

        # Act
        response = client.post(f"/v1/requests/{request_id}/process")
        status_response = client.get(f"/v1/requests/{request_id}")

        # Assert
        assert response.status_code == 202
        assert stub_process_dispatcher.dispatched_request_ids == [request_id]
        assert status_response.status_code == 200
        assert status_response.json() == {
            "id": request_id,
            "status": NotificationStatus.PROCESSING.value,
        }

    def test_returns_not_found_when_getting_status_of_unknown_request(self, client):
        """GET /v1/requests/{id} returns 404 for unknown request IDs."""
        # Act
        response = client.get("/v1/requests/missing-request")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Request not found"
