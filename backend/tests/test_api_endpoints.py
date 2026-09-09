import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, name: str = "Test User"):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": name},
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    household_id = data["households"][0]["household_id"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    return tokens["access_token"], tokens["refresh_token"], household_id


@pytest.mark.asyncio
async def test_auth_logout_and_invalid_tokens(client: AsyncClient):
    access_token, refresh_token, _ = await _register_and_login(client, "logout_test@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    # Successful logout with refresh token
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200

    # Invalid login credentials
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout_test@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # Invalid refresh token
    bad_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_refresh_token_string"},
    )
    assert bad_refresh.status_code == 401


@pytest.mark.asyncio
async def test_households_endpoints(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "household_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Get single household
    get_resp = await client.get(f"/api/v1/households/{household_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == household_id

    # Create another household
    create_resp = await client.post(
        "/api/v1/households",
        headers=headers,
        json={"name": "Summer House"},
    )
    assert create_resp.status_code == 201
    new_h = create_resp.json()
    assert new_h["name"] == "Summer House"

    # List household members
    members_resp = await client.get(
        f"/api/v1/households/{new_h['id']}/members", headers=headers
    )
    assert members_resp.status_code == 200
    assert len(members_resp.json()) == 1


@pytest.mark.asyncio
async def test_fixed_templates_endpoints(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "template_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create fixed template
    create_resp = await client.post(
        f"/api/v1/fixed-templates?household_id={household_id}",
        headers=headers,
        json={
            "title": "High Speed Internet",
            "estimated_amount_cents": 7999,
            "due_day": 15,
            "category": "Utilities",
            "recurrence_type": "FIXED",
            "is_active": True,
            "split_type": "EQUAL",
        },
    )
    assert create_resp.status_code == 201
    template = create_resp.json()
    assert template["title"] == "High Speed Internet"
    template_id = template["id"]

    # List templates for household
    list_resp = await client.get(
        f"/api/v1/fixed-templates?household_id={household_id}", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update template
    put_resp = await client.put(
        f"/api/v1/fixed-templates/{template_id}",
        headers=headers,
        json={"estimated_amount_cents": 8999, "is_active": False},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["estimated_amount_cents"] == 8999

    # Delete template
    del_resp = await client.delete(
        f"/api/v1/fixed-templates/{template_id}", headers=headers
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_expenses_and_settlements_crud(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "expense_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create cycle
    cycle_resp = await client.post(
        "/api/v1/cycles",
        headers=headers,
        json={"household_id": household_id, "year": 2026, "month": 11},
    )
    assert cycle_resp.status_code == 201
    cycle_id = cycle_resp.json()["id"]

    # List persons to get resident ID
    persons_resp = await client.get(
        f"/api/v1/households/{household_id}/persons", headers=headers
    )
    assert persons_resp.status_code == 200
    person_id = persons_resp.json()[0]["id"]

    # Create expense with split
    exp_resp = await client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Groceries",
            "total_amount_cents": 10000,
            "due_date": "2026-11-15",
            "category": "Food",
            "split_type": "EQUAL",
            "participant_ids": [person_id],
        },
    )
    assert exp_resp.status_code == 201
    expense_id = exp_resp.json()["id"]

    # Update expense
    put_exp = await client.put(
        f"/api/v1/expenses/{expense_id}",
        headers=headers,
        json={"title": "Supermarket Groceries", "total_amount_cents": 12000},
    )
    assert put_exp.status_code == 200
    assert put_exp.json()["title"] == "Supermarket Groceries"

    # Record Payment
    pay_resp = await client.post(
        "/api/v1/settlements/payments",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "person_id": person_id,
            "amount_cents": 5000,
            "notes": "Half payment",
        },
    )
    assert pay_resp.status_code == 201
    payment_id = pay_resp.json()["id"]

    # Update Payment
    patch_pay = await client.patch(
        f"/api/v1/settlements/payments/{payment_id}",
        headers=headers,
        json={"amount_cents": 6000, "notes": "Updated payment"},
    )
    assert patch_pay.status_code == 200
    assert patch_pay.json()["amount_cents"] == 6000

    # List payments
    list_pay = await client.get(
        f"/api/v1/settlements/payments?billing_cycle_id={cycle_id}", headers=headers
    )
    assert list_pay.status_code == 200
    assert len(list_pay.json()) == 1

    # Record Waiver
    waiver_resp = await client.post(
        "/api/v1/settlements/waivers",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "person_id": person_id,
            "amount_cents": 2000,
            "reason": "Chore credit",
        },
    )
    assert waiver_resp.status_code == 201
    waiver_id = waiver_resp.json()["id"]

    # Update Waiver
    patch_waiver = await client.patch(
        f"/api/v1/settlements/waivers/{waiver_id}",
        headers=headers,
        json={"amount_cents": 2500},
    )
    assert patch_waiver.status_code == 200
    assert patch_waiver.json()["amount_cents"] == 2500

    # List waivers
    list_waiver = await client.get(
        f"/api/v1/settlements/waivers?billing_cycle_id={cycle_id}", headers=headers
    )
    assert list_waiver.status_code == 200
    assert len(list_waiver.json()) == 1

    # Fetch Cycle Report
    rep_resp = await client.get(f"/api/v1/reports/current-cycle?cycle_id={cycle_id}", headers=headers)
    assert rep_resp.status_code == 200

    # Fetch General Balance Report
    gen_rep = await client.get(
        f"/api/v1/reports/general-balance?household_id={household_id}", headers=headers
    )
    assert gen_rep.status_code == 200

    # Delete Waiver
    del_waiver = await client.delete(
        f"/api/v1/settlements/waivers/{waiver_id}", headers=headers
    )
    assert del_waiver.status_code == 204

    # Delete Payment
    del_pay = await client.delete(
        f"/api/v1/settlements/payments/{payment_id}", headers=headers
    )
    assert del_pay.status_code == 204

    # Delete Expense
    del_exp = await client.delete(
        f"/api/v1/expenses/{expense_id}", headers=headers
    )
    assert del_exp.status_code == 204


@pytest.mark.asyncio
async def test_cycle_close_and_reopen_flow(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "cycle_flow@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create cycle
    c_resp = await client.post(
        "/api/v1/cycles",
        headers=headers,
        json={"household_id": household_id, "year": 2026, "month": 12},
    )
    assert c_resp.status_code == 201
    cycle_id = c_resp.json()["id"]

    # List cycles
    list_c = await client.get(
        f"/api/v1/cycles?household_id={household_id}", headers=headers
    )
    assert list_c.status_code == 200
    assert len(list_c.json()) >= 1

    # Close cycle
    close_resp = await client.post(f"/api/v1/cycles/{cycle_id}/close", headers=headers)
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # Reopen cycle
    reopen_resp = await client.post(f"/api/v1/cycles/{cycle_id}/reopen", headers=headers)
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "OPEN"


@pytest.mark.asyncio
async def test_household_members_and_persons_flow(client: AsyncClient):
    admin_token, _, household_id = await _register_and_login(client, "admin_user@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register member user
    member_token, _, _ = await _register_and_login(client, "invited_member@example.com")

    # Add member to household
    add_mem = await client.post(
        f"/api/v1/households/{household_id}/members",
        headers=admin_headers,
        json={"email": "invited_member@example.com", "role": "MEMBER"},
    )
    assert add_mem.status_code == 201
    mem_id = add_mem.json()["id"]

    # Add standalone person to household
    add_person = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers=admin_headers,
        json={"name": "Bob Roommate", "is_active": True},
    )
    assert add_person.status_code == 201
    person_id = add_person.json()["id"]

    # Delete standalone person
    del_person = await client.delete(
        f"/api/v1/persons/{person_id}",
        headers=admin_headers,
    )
    assert del_person.status_code == 200


@pytest.mark.asyncio
async def test_expense_percentage_and_weighted_splits(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "splits_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create cycle
    c_resp = await client.post(
        "/api/v1/cycles",
        headers=headers,
        json={"household_id": household_id, "year": 2027, "month": 1},
    )
    cycle_id = c_resp.json()["id"]

    # Add second resident
    p2 = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers=headers,
        json={"name": "Participant 2", "is_active": True},
    )
    p2_id = p2.json()["id"]

    # Get persons
    persons_resp = await client.get(
        f"/api/v1/households/{household_id}/persons", headers=headers
    )
    persons_list = persons_resp.json()
    p1_id = [p["id"] for p in persons_list if p["id"] != p2_id][0]

    # Percentage expense
    pct_exp = await client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Electricity",
            "total_amount_cents": 10000,
            "due_date": "2027-01-20",
            "category": "Utilities",
            "split_type": "PERCENTAGE",
            "percentages": {str(p1_id): 60.0, str(p2_id): 40.0},
        },
    )
    assert pct_exp.status_code == 201

    # Weighted expense
    wgt_exp = await client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Internet",
            "total_amount_cents": 9000,
            "due_date": "2027-01-25",
            "category": "Utilities",
            "split_type": "WEIGHTED",
            "weights": {str(p1_id): 2.0, str(p2_id): 1.0},
        },
    )
    assert wgt_exp.status_code == 201

    exp_id = wgt_exp.json()["id"]

    # Update payment status of expense
    patch_status = await client.patch(
        f"/api/v1/expenses/{exp_id}/payment-status",
        headers=headers,
        json={"is_paid": True},
    )
    assert patch_status.status_code == 200
    assert patch_status.json()["is_paid"] is True

    # Check cycle expenses via cycle list endpoint
    cycle_check = await client.get(f"/api/v1/cycles?household_id={household_id}", headers=headers)
    assert cycle_check.status_code == 200
    assert cycle_check.json()[0]["total_expenses_cents"] == 19000


@pytest.mark.asyncio
async def test_auth_me_and_refresh_flow(client: AsyncClient):
    token, refresh_tok, household_id = await _register_and_login(client, "me_refresh@example.com", "Me User")
    headers = {"Authorization": f"Bearer {token}"}

    # /auth/me
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "me_refresh@example.com"
    assert len(me_data["households"]) >= 1

    # Duplicate registration
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "me_refresh@example.com", "password": "Password123!", "full_name": "Me Duplicate"},
    )
    assert dup_resp.status_code == 409

    # Successful token refresh
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok, "device_info": "pytest-runner"},
    )
    assert ref_resp.status_code == 200
    new_tokens = ref_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # Verify old refresh token is now rotated/revoked
    old_ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    assert old_ref_resp.status_code == 401


@pytest.mark.asyncio
async def test_expenses_exact_split_and_save_template(client: AsyncClient):
    token, _, household_id = await _register_and_login(client, "exact_exp@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create cycle
    c_resp = await client.post(
        "/api/v1/cycles",
        headers=headers,
        json={"household_id": household_id, "year": 2027, "month": 2},
    )
    cycle_id = c_resp.json()["id"]

    # Add second resident
    p2 = await client.post(
        f"/api/v1/households/{household_id}/persons",
        headers=headers,
        json={"name": "Exact Roommate", "is_active": True},
    )
    p2_id = p2.json()["id"]

    # Get persons
    persons_resp = await client.get(f"/api/v1/households/{household_id}/persons", headers=headers)
    p1_id = [p["id"] for p in persons_resp.json() if p["id"] != p2_id][0]

    # Create expense with EXACT split and save_as_template=True
    exp_resp = await client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Water Utility",
            "total_amount_cents": 5000,
            "due_date": "2027-02-18",
            "category": "Utilities",
            "split_type": "EXACT",
            "exact_amounts": {str(p1_id): 3000, str(p2_id): 2000},
            "save_as_template": True,
            "recurrence_type": "FIXED",
        },
    )
    assert exp_resp.status_code == 201
    exp_data = exp_resp.json()
    assert exp_data["split_type"] == "EXACT"
    assert exp_data["template_id"] is not None

    # Update EXACT expense via PUT
    put_amt = await client.put(
        f"/api/v1/expenses/{exp_data['id']}",
        headers=headers,
        json={
            "total_amount_cents": 6000,
            "split_type": "EXACT",
            "exact_amounts": {str(p1_id): 3500, str(p2_id): 2500},
        },
    )
    assert put_amt.status_code == 200
    assert put_amt.json()["total_amount_cents"] == 6000

    # Create variable/equal expense and test PATCH /amount
    var_exp = await client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Gas Bill",
            "total_amount_cents": 0,
            "due_date": "2027-02-20",
            "category": "Utilities",
            "split_type": "EQUAL",
            "participant_ids": [p1_id, p2_id],
            "recurrence_type": "VARIABLE",
            "status": "PENDING_VALUE",
            "save_as_template": True,
        },
    )
    assert var_exp.status_code == 201
    var_exp_id = var_exp.json()["id"]

    patch_amt = await client.patch(
        f"/api/v1/expenses/{var_exp_id}/amount",
        headers=headers,
        json={"actual_amount_cents": 4200, "update_template_default": True},
    )
    assert patch_amt.status_code == 200
    assert patch_amt.json()["total_amount_cents"] == 4200
    assert patch_amt.json()["status"] == "READY"

    # Verify expense in cycle report
    rep = await client.get(f"/api/v1/reports/current-cycle?cycle_id={cycle_id}", headers=headers)
    assert rep.status_code == 200
    rep_expenses = rep.json()["expenses"]
    assert any(e["id"] == var_exp_id for e in rep_expenses)


@pytest.mark.asyncio
async def test_api_edge_cases_and_error_handling(client: AsyncClient):
    token1, _, h1_id = await _register_and_login(client, "user_alpha@example.com")
    token2, _, h2_id = await _register_and_login(client, "user_beta@example.com")
    h1_headers = {"Authorization": f"Bearer {token1}"}
    h2_headers = {"Authorization": f"Bearer {token2}"}

    fake_id = "00000000-0000-0000-0000-000000000000"

    # User beta cannot access household alpha
    forbidden_get = await client.get(f"/api/v1/households/{h1_id}", headers=h2_headers)
    assert forbidden_get.status_code == 403

    # Adding member with unknown email gives 404
    missing_email_resp = await client.post(
        f"/api/v1/households/{h1_id}/members",
        headers=h1_headers,
        json={"email": "nonexistent_person_12345@example.com", "role": "MEMBER"},
    )
    assert missing_email_resp.status_code == 404

    # Adding resident person with unknown email gives 404
    missing_res_resp = await client.post(
        f"/api/v1/households/{h1_id}/persons",
        headers=h1_headers,
        json={"name": "Ghost", "email": "nonexistent_ghost@example.com"},
    )
    assert missing_res_resp.status_code == 404

    # Fixed template 404 on update and delete
    fake_put = await client.put(f"/api/v1/fixed-templates/{fake_id}", headers=h1_headers, json={"title": "None"})
    assert fake_put.status_code == 404

    fake_del = await client.delete(f"/api/v1/fixed-templates/{fake_id}", headers=h1_headers)
    assert fake_del.status_code == 404

    # Expense 404 on update and delete
    fake_exp_put = await client.put(f"/api/v1/expenses/{fake_id}", headers=h1_headers, json={"title": "None"})
    assert fake_exp_put.status_code == 404

    fake_exp_del = await client.delete(f"/api/v1/expenses/{fake_id}", headers=h1_headers)
    assert fake_exp_del.status_code == 404

    # Settlement payment and waiver 404
    fake_pay_patch = await client.patch(f"/api/v1/settlements/payments/{fake_id}", headers=h1_headers, json={"amount_cents": 100})
    assert fake_pay_patch.status_code == 404

    fake_pay_del = await client.delete(f"/api/v1/settlements/payments/{fake_id}", headers=h1_headers)
    assert fake_pay_del.status_code == 404

    fake_waiver_patch = await client.patch(f"/api/v1/settlements/waivers/{fake_id}", headers=h1_headers, json={"amount_cents": 100})
    assert fake_waiver_patch.status_code == 404

    fake_waiver_del = await client.delete(f"/api/v1/settlements/waivers/{fake_id}", headers=h1_headers)
    assert fake_waiver_del.status_code == 404

    # Reports 404 on fake cycle
    rep_404 = await client.get(f"/api/v1/reports/current-cycle?cycle_id={fake_id}", headers=h1_headers)
    assert rep_404.status_code == 404

    # Reports 403 on other user's household
    rep_403 = await client.get(f"/api/v1/reports/general-balance?household_id={h1_id}", headers=h2_headers)
    assert rep_403.status_code == 403


@pytest.mark.asyncio
async def test_settlements_and_waivers_permissions_and_cycle_closure(client: AsyncClient):
    admin_tok, _, household_id = await _register_and_login(client, "admin_settle@example.com")
    admin_hdr = {"Authorization": f"Bearer {admin_tok}"}

    member_tok, _, _ = await _register_and_login(client, "member_settle@example.com")
    mem_hdr = {"Authorization": f"Bearer {member_tok}"}

    # Add member to household
    add_m = await client.post(
        f"/api/v1/households/{household_id}/members",
        headers=admin_hdr,
        json={"email": "member_settle@example.com", "role": "MEMBER"},
    )
    assert add_m.status_code == 201

    # Create cycle
    c_resp = await client.post(
        "/api/v1/cycles",
        headers=admin_hdr,
        json={"household_id": household_id, "year": 2027, "month": 3},
    )
    cycle_id = c_resp.json()["id"]

    # Get persons
    p_resp = await client.get(f"/api/v1/households/{household_id}/persons", headers=admin_hdr)
    persons = p_resp.json()
    admin_person = next(p for p in persons if p["user_email"] == "admin_settle@example.com")
    member_person = next(p for p in persons if p["user_email"] == "member_settle@example.com")

    # Member attempting to record debt waiver (forbidden - admin only)
    bad_waiver = await client.post(
        "/api/v1/settlements/waivers",
        headers=mem_hdr,
        json={"billing_cycle_id": cycle_id, "person_id": member_person["id"], "amount_cents": 500, "reason": "Test"},
    )
    assert bad_waiver.status_code == 403

    # Member attempting to record payment for admin (forbidden - only self)
    bad_pay = await client.post(
        "/api/v1/settlements/payments",
        headers=mem_hdr,
        json={"billing_cycle_id": cycle_id, "person_id": admin_person["id"], "amount_cents": 500},
    )
    assert bad_pay.status_code == 403

    # Admin records waiver and payment
    ok_waiver = await client.post(
        "/api/v1/settlements/waivers",
        headers=admin_hdr,
        json={"billing_cycle_id": cycle_id, "person_id": member_person["id"], "amount_cents": 500, "reason": "Test"},
    )
    assert ok_waiver.status_code == 201
    waiver_id = ok_waiver.json()["id"]

    ok_pay = await client.post(
        "/api/v1/settlements/payments",
        headers=admin_hdr,
        json={"billing_cycle_id": cycle_id, "person_id": member_person["id"], "amount_cents": 1000},
    )
    assert ok_pay.status_code == 201
    pay_id = ok_pay.json()["id"]

    # Member attempting to delete payment (forbidden - admin only)
    bad_del_pay = await client.delete(f"/api/v1/settlements/payments/{pay_id}", headers=mem_hdr)
    assert bad_del_pay.status_code == 403

    # Close cycle
    await client.post(f"/api/v1/cycles/{cycle_id}/close", headers=admin_hdr)

    # Operations in closed cycle return 400
    closed_pay = await client.post(
        "/api/v1/settlements/payments",
        headers=admin_hdr,
        json={"billing_cycle_id": cycle_id, "person_id": member_person["id"], "amount_cents": 500},
    )
    assert closed_pay.status_code == 400

    closed_exp = await client.post(
        "/api/v1/expenses",
        headers=admin_hdr,
        json={
            "billing_cycle_id": cycle_id,
            "title": "Late Bill",
            "total_amount_cents": 1000,
            "due_date": "2027-03-25",
            "category": "Utilities",
            "split_type": "EQUAL",
            "participant_ids": [admin_person["id"]],
        },
    )
    assert closed_exp.status_code == 400

