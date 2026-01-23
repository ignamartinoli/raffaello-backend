def test_get_roles_returns_three_roles(client):
    """Test that GET /api/v1/roles returns exactly 3 roles created by migrations."""
    response = client.get("/api/v1/roles")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    role_names = {role["name"] for role in data}
    assert role_names == {"admin", "tenant", "accountant"}

    for role in data:
        assert "id" in role
        assert "name" in role
        assert isinstance(role["id"], int)
        assert isinstance(role["name"], str)
