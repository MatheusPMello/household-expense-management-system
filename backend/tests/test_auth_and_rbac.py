import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register User
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "Password123!",
            "full_name": "Alice Resident",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["email"] == "alice@example.com"
    assert len(reg_data["households"]) == 1
    assert reg_data["households"][0]["role"] == "ADMIN"
    household_id = reg_data["households"][0]["household_id"]

    # 2. Duplicate registration fails
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "OtherPassword!",
            "full_name": "Alice Duplicate",
        },
    )
    assert dup_resp.status_code == 409

    # 3. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "Password123!",
        },
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 4. Access /auth/me with Bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"

    # 5. Token Refresh
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # 6. Re-using the old rotated refresh token fails (rotation revoked it)
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient):
    # Register Alice
    resp_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice_tenant@example.com", "password": "Password123!", "full_name": "Alice"},
    )
    token_a = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "alice_tenant@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    h_a_id = resp_a.json()["households"][0]["household_id"]

    # Register Bob
    resp_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob_tenant@example.com", "password": "Password123!", "full_name": "Bob"},
    )
    token_b = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "bob_tenant@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    h_b_id = resp_b.json()["households"][0]["household_id"]

    # Bob tries to access Alice's household members -> 403 Forbidden
    unauth_resp = await client.get(
        f"/api/v1/households/{h_a_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauth_resp.status_code == 403

    # Alice accesses her own household members -> 200 OK
    auth_resp = await client.get(
        f"/api/v1/households/{h_a_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert auth_resp.status_code == 200


@pytest.mark.asyncio
async def test_resident_optional_user_linking(client: AsyncClient):
    # 1. Register admin user Charlie
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"email": "charlie_admin@example.com", "password": "Password123!", "full_name": "Charlie Admin"},
    )
    assert reg_admin.status_code == 201
    token_admin = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "charlie_admin@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    household_id = reg_admin.json()["households"][0]["household_id"]

    # 2. Add standalone resident (without email)
    p_resp = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "David Standalone"},
    )
    assert p_resp.status_code == 201
    person_data = p_resp.json()
    assert person_data["name"] == "David Standalone"
    assert person_data["user_id"] is None
    assert person_data["user_email"] is None
    assert person_data["role"] is None
    person_id = person_data["id"]

    # 3. Attempt to link non-registered email -> 404
    link_fail = await client.post(
        f"/api/v1/persons/{person_id}/link-user",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"email": "notregistered@example.com", "role": "MEMBER"},
    )
    assert link_fail.status_code == 404

    # 4. Register David
    reg_david = await client.post(
        "/api/v1/auth/register",
        json={"email": "david_linked@example.com", "password": "Password123!", "full_name": "David Linked"},
    )
    assert reg_david.status_code == 201
    david_user_id = reg_david.json()["id"]

    # 5. Link David to the standalone resident
    link_success = await client.post(
        f"/api/v1/persons/{person_id}/link-user",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"email": "david_linked@example.com", "role": "MEMBER"},
    )
    assert link_success.status_code == 200
    linked_data = link_success.json()
    assert linked_data["user_id"] == david_user_id
    assert linked_data["user_email"] == "david_linked@example.com"
    assert linked_data["role"] == "MEMBER"

    # 6. Verify GET /households/{id}/persons reflects linkage
    list_persons = await client.get(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert list_persons.status_code == 200
    p_matched = next((p for p in list_persons.json() if p["id"] == person_id), None)
    assert p_matched is not None
    assert p_matched["user_email"] == "david_linked@example.com"

    # 7. Non-admin cannot unlink or link -> 403
    token_david = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "david_linked@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    forbidden_unlink = await client.post(
        f"/api/v1/persons/{person_id}/unlink-user",
        headers={"Authorization": f"Bearer {token_david}"},
    )
    assert forbidden_unlink.status_code == 403

    # 8. Admin unlinks user
    unlink_success = await client.post(
        f"/api/v1/persons/{person_id}/unlink-user",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert unlink_success.status_code == 200
    unlinked_data = unlink_success.json()
    assert unlinked_data["user_id"] is None
    assert unlinked_data["user_email"] is None


@pytest.mark.asyncio
async def test_resident_admin_only_creation_and_update(client: AsyncClient):
    # 1. Register admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "Password123!", "full_name": "Owner Admin"},
    )
    token_admin = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    household_id = reg_admin.json()["households"][0]["household_id"]

    # 2. Register member user
    reg_member = await client.post(
        "/api/v1/auth/register",
        json={"email": "tenant@example.com", "password": "Password123!", "full_name": "Tenant Member"},
    )
    token_member = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "tenant@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]

    # Admin adds tenant as MEMBER
    add_mem_resp = await client.post(
        f"/api/v1/households/{household_id}/members",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"email": "tenant@example.com", "role": "MEMBER"},
    )
    assert add_mem_resp.status_code == 201

    # 3. Member attempts to create a resident -> 403 Forbidden
    member_create_resp = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"name": "Unauthorized Resident"},
    )
    assert member_create_resp.status_code == 403
    assert "administrators" in member_create_resp.json()["detail"]

    # Admin creates a resident
    admin_create_resp = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Valid Resident"},
    )
    assert admin_create_resp.status_code == 201
    person_id = admin_create_resp.json()["id"]

    # 4. Member attempts to update resident -> 403 Forbidden
    member_update_resp = await client.put(
        f"/api/v1/persons/{person_id}",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"name": "Hacked Name", "is_active": False},
    )
    assert member_update_resp.status_code == 403

    # Admin successfully updates resident
    admin_update_resp = await client.put(
        f"/api/v1/persons/{person_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Updated Resident", "is_active": True},
    )
    assert admin_update_resp.status_code == 200
    assert admin_update_resp.json()["name"] == "Updated Resident"


@pytest.mark.asyncio
async def test_add_household_member_duplicate_person_names(client: AsyncClient):
    # Register admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"email": "boss@example.com", "password": "Password123!", "full_name": "Boss Admin"},
    )
    token_admin = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "boss@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    household_id = reg_admin.json()["households"][0]["household_id"]

    # Add two persons with the same name "Sam Smith" (e.g. junior/senior or common name)
    await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Sam Smith"},
    )
    await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"name": "Sam Smith"},
    )

    # Register user "Sam Smith"
    await client.post(
        "/api/v1/auth/register",
        json={"email": "sam@example.com", "password": "Password123!", "full_name": "Sam Smith"},
    )

    # Admin adds Sam as member; must not crash with MultipleResultsFound
    add_mem = await client.post(
        f"/api/v1/households/{household_id}/members",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"email": "sam@example.com", "role": "MEMBER"},
    )
    assert add_mem.status_code == 201
    assert add_mem.json()["email"] == "sam@example.com"


