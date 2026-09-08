import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_cycle_and_ledger_workflow(client: AsyncClient):
    # 1. Register Admin User
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "landlord@example.com",
            "password": "Password123!",
            "full_name": "Landlord Admin",
        },
    )
    auth_data = reg.json()
    household_id = auth_data["households"][0]["household_id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "landlord@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add two more residents: "Bob" and "Charlie"
    bob_resp = await client.post(
        f"/api/v1/households/{household_id}/persons",
        json={"name": "Bob Resident"},
        headers=headers,
    )
    bob_id = bob_resp.json()["id"]

    charlie_resp = await client.post(
        f"/api/v1/households/{household_id}/persons",
        json={"name": "Charlie Resident"},
        headers=headers,
    )
    charlie_id = charlie_resp.json()["id"]

    # Retrieve all persons (Admin, Bob, Charlie)
    persons_resp = await client.get(
        f"/api/v1/households/{household_id}/persons",
        headers=headers,
    )
    all_persons = persons_resp.json()
    assert len(all_persons) == 3
    admin_person = next(p for p in all_persons if p["name"] == "Landlord Admin")
    admin_id = admin_person["id"]

    # 3. Create a Fixed Expense Template: "Internet Fiber" $90.00 (9000 cents)
    tpl_resp = await client.post(
        f"/api/v1/fixed-templates?household_id={household_id}",
        json={
            "title": "Internet Fiber",
            "estimated_amount_cents": 9000,
            "due_day": 15,
            "category": "Utilities",
            "is_active": True,
        },
        headers=headers,
    )
    assert tpl_resp.status_code == 201

    # 4. Create Billing Cycle for 2026-09
    cycle_resp = await client.post(
        "/api/v1/cycles",
        json={
            "household_id": household_id,
            "year": 2026,
            "month": 9,
        },
        headers=headers,
    )
    assert cycle_resp.status_code == 201
    cycle = cycle_resp.json()
    cycle_id = cycle["id"]
    # Template was automatically instantiated: 9000 cents split 3 ways = 3000 each!
    assert cycle["total_expenses_cents"] == 9000

    # 5. Create an ad-hoc Variable Expense: "Front Gate Repair" for $120.00 (12000 cents)
    exp_resp = await client.post(
        "/api/v1/expenses",
        json={
            "billing_cycle_id": cycle_id,
            "title": "Front Gate Repair",
            "total_amount_cents": 12000,
            "is_fixed": False,
            "category": "Maintenance",
            "due_date": "2026-09-20",
            "split_type": "EQUAL",
            "participant_ids": [admin_id, bob_id, charlie_id],
        },
        headers=headers,
    )
    assert exp_resp.status_code == 201
    expense_data = exp_resp.json()
    assert len(expense_data["splits"]) == 3
    for s in expense_data["splits"]:
        assert s["assigned_amount_cents"] == 4000  # 12000 / 3 = 4000 cents

    # Toggle paid to vendor
    toggle_resp = await client.patch(
        f"/api/v1/expenses/{expense_data['id']}/vendor-status",
        json={"paid_to_vendor": True},
        headers=headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["paid_to_vendor"] is True

    # At this point:
    # Admin assigned: 3000 + 4000 = 7000 cents
    # Bob assigned: 3000 + 4000 = 7000 cents
    # Charlie assigned: 3000 + 4000 = 7000 cents

    # 6. Record Payment for Admin: full 7000 cents
    pay_resp = await client.post(
        "/api/v1/settlements/payments",
        json={
            "billing_cycle_id": cycle_id,
            "person_id": admin_id,
            "amount_cents": 7000,
            "notes": "Bank transfer",
        },
        headers=headers,
    )
    assert pay_resp.status_code == 201

    # 7. Record Partial Payment for Bob: 5000 cents
    await client.post(
        "/api/v1/settlements/payments",
        json={
            "billing_cycle_id": cycle_id,
            "person_id": bob_id,
            "amount_cents": 5000,
        },
        headers=headers,
    )

    # 8. Record Debt Waiver for Bob: remaining 2000 cents forgiven with reason
    waiver_resp = await client.post(
        "/api/v1/settlements/waivers",
        json={
            "billing_cycle_id": cycle_id,
            "person_id": bob_id,
            "amount_cents": 2000,
            "reason": "Mutual agreement for gate painting labor offset",
        },
        headers=headers,
    )
    assert waiver_resp.status_code == 201

    # 9. Verify Current Cycle Report
    report_resp = await client.get(
        f"/api/v1/reports/current-cycle?cycle_id={cycle_id}",
        headers=headers,
    )
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert report["total_budget_cents"] == 21000  # 9000 + 12000
    assert report["total_collected_cents"] == 12000  # 7000 + 5000
    assert report["total_waived_cents"] == 2000

    residents_map = {r["person_id"]: r for r in report["residents"]}
    # Admin: assigned 7000, paid 7000, waived 0, remaining 0 (SETTLED)
    assert residents_map[admin_id]["remaining_balance_cents"] == 0
    assert residents_map[admin_id]["status"] == "SETTLED"

    # Bob: assigned 7000, paid 5000, waived 2000, remaining 0 (SETTLED because 7000 - 5000 - 2000 = 0)
    assert residents_map[bob_id]["remaining_balance_cents"] == 0
    assert residents_map[bob_id]["waived_cents"] == 2000
    assert residents_map[bob_id]["status"] == "SETTLED"

    # Charlie: assigned 7000, paid 0, waived 0, remaining 7000 (OWES)
    assert residents_map[charlie_id]["remaining_balance_cents"] == 7000
    assert residents_map[charlie_id]["status"] == "OWES"

    # 10. Verify General Balance Report
    gen_resp = await client.get(
        f"/api/v1/reports/general-balance?household_id={household_id}",
        headers=headers,
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    # Debt waiver ledger contains Bob's waiver
    assert len(gen_data["debt_waiver_ledger"]) == 1
    assert gen_data["debt_waiver_ledger"][0]["amount_cents"] == 2000
    assert gen_data["debt_waiver_ledger"][0]["person_name"] == "Bob Resident"
    assert "labor offset" in gen_data["debt_waiver_ledger"][0]["reason"]

    # Trajectory points
    assert len(gen_data["trajectory"]) == 1
    assert gen_data["trajectory"][0]["fixed_cents"] == 9000
    assert gen_data["trajectory"][0]["variable_cents"] == 12000
    assert gen_data["trajectory"][0]["total_cents"] == 21000

    # 11. Close Cycle and verify modification lock and preserved metrics
    close_resp = await client.post(
        f"/api/v1/cycles/{cycle_id}/close",
        headers=headers,
    )
    assert close_resp.status_code == 200
    close_data = close_resp.json()
    assert close_data["status"] == "CLOSED"
    assert close_data["total_expenses_cents"] == 21000
    assert close_data["total_collected_cents"] == 12000
    assert close_data["total_waived_cents"] == 2000

    # Reopen cycle and verify preserved metrics
    reopen_resp = await client.post(
        f"/api/v1/cycles/{cycle_id}/reopen",
        headers=headers,
    )
    assert reopen_resp.status_code == 200
    reopen_data = reopen_resp.json()
    assert reopen_data["status"] == "OPEN"
    assert reopen_data["total_expenses_cents"] == 21000

    # Close again to verify locked expense creation
    await client.post(f"/api/v1/cycles/{cycle_id}/close", headers=headers)

    # Attempting to add an expense to a CLOSED cycle fails
    locked_exp = await client.post(
        "/api/v1/expenses",
        json={
            "billing_cycle_id": cycle_id,
            "title": "Post Close Expense",
            "total_amount_cents": 5000,
            "is_fixed": False,
            "category": "Food",
            "due_date": "2026-09-25",
            "split_type": "EQUAL",
            "participant_ids": [admin_id],
        },
        headers=headers,
    )
    assert locked_exp.status_code == 400
    assert "CLOSED" in locked_exp.json()["detail"]


@pytest.mark.asyncio
async def test_expense_update_and_tenant_validation(client: AsyncClient):
    # 1. Register User A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "usera@example.com", "password": "Password123!", "full_name": "User A"},
    )
    token_a = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "usera@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    h_a_id = reg_a.json()["households"][0]["household_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B in separate household
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "Password123!", "full_name": "User B"},
    )
    p_b_id = (
        await client.get(
            f"/api/v1/households/{reg_b.json()['households'][0]['household_id']}/persons",
            headers={"Authorization": f"Bearer {(await client.post('/api/v1/auth/login', json={'email': 'userb@example.com', 'password': 'Password123!'})).json()['access_token']}"},
        )
    ).json()[0]["id"]

    # Person in household A
    p_a_id = (
        await client.get(
            f"/api/v1/households/{h_a_id}/persons",
            headers=headers_a,
        )
    ).json()[0]["id"]

    # Add second resident in A
    p_a2_resp = await client.post(
        f"/api/v1/households/{h_a_id}/persons",
        headers=headers_a,
        json={"name": "Resident A2"},
    )
    p_a2_id = p_a2_resp.json()["id"]

    # Create cycle in household A
    cycle_a = (
        await client.post(
            "/api/v1/cycles",
            headers=headers_a,
            json={"household_id": h_a_id, "year": 2026, "month": 12},
        )
    ).json()

    # Create percentage expense
    exp_resp = await client.post(
        "/api/v1/expenses",
        headers=headers_a,
        json={
            "billing_cycle_id": cycle_a["id"],
            "title": "Initial Electric",
            "total_amount_cents": 10000,
            "category": "Utilities",
            "due_date": "2026-12-10",
            "split_type": "PERCENTAGE",
            "percentages": {p_a_id: 60.0, p_a2_id: 40.0},
        },
    )
    assert exp_resp.status_code == 201
    exp_id = exp_resp.json()["id"]

    # Partial metadata update without re-sending split data (MUST NOT crash)
    update_meta = await client.put(
        f"/api/v1/expenses/{exp_id}",
        headers=headers_a,
        json={"title": "Updated Electric Utility", "category": "Bills"},
    )
    assert update_meta.status_code == 200
    assert update_meta.json()["title"] == "Updated Electric Utility"
    assert len(update_meta.json()["splits"]) == 2

    # Attempt cross-tenant participant update using p_b_id (from another household) -> 400 Bad Request
    cross_tenant_update = await client.put(
        f"/api/v1/expenses/{exp_id}",
        headers=headers_a,
        json={
            "split_type": "EQUAL",
            "participant_ids": [p_a_id, p_b_id],
        },
    )
    assert cross_tenant_update.status_code == 400
    assert "do not belong to this household" in cross_tenant_update.json()["detail"]


@pytest.mark.asyncio
async def test_settlement_deletion_and_rbac(client: AsyncClient):
    # 1. Register Admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"email": "settle_admin@example.com", "password": "Password123!", "full_name": "Settle Admin"},
    )
    token_admin = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "settle_admin@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    household_id = reg_admin.json()["households"][0]["household_id"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # 2. Register Member
    await client.post(
        "/api/v1/auth/register",
        json={"email": "settle_member@example.com", "password": "Password123!", "full_name": "Settle Member"},
    )
    token_member = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "settle_member@example.com", "password": "Password123!"},
        )
    ).json()["access_token"]
    headers_member = {"Authorization": f"Bearer {token_member}"}

    await client.post(
        f"/api/v1/households/{household_id}/members",
        headers=headers_admin,
        json={"email": "settle_member@example.com", "role": "MEMBER"},
    )

    # 3. Create cycle
    cycle = (
        await client.post(
            "/api/v1/cycles",
            headers=headers_admin,
            json={"household_id": household_id, "year": 2027, "month": 1},
        )
    ).json()

    # Get admin person
    persons = (
        await client.get(f"/api/v1/households/{household_id}/persons", headers=headers_admin)
    ).json()
    admin_pid = persons[0]["id"]

    # 4. Record Payment
    pay_resp = await client.post(
        "/api/v1/settlements/payments",
        headers=headers_admin,
        json={"billing_cycle_id": cycle["id"], "person_id": admin_pid, "amount_cents": 5000},
    )
    pay_id = pay_resp.json()["id"]

    # 5. Record Debt Waiver
    waiver_resp = await client.post(
        "/api/v1/settlements/waivers",
        headers=headers_admin,
        json={"billing_cycle_id": cycle["id"], "person_id": admin_pid, "amount_cents": 1000, "reason": "Test waiver"},
    )
    waiver_id = waiver_resp.json()["id"]

    # Member attempts to delete payment -> 403 Forbidden
    member_del_pay = await client.delete(
        f"/api/v1/settlements/payments/{pay_id}",
        headers=headers_member,
    )
    assert member_del_pay.status_code == 403

    # Member attempts to delete debt waiver -> 403 Forbidden
    member_del_waiver = await client.delete(
        f"/api/v1/settlements/waivers/{waiver_id}",
        headers=headers_member,
    )
    assert member_del_waiver.status_code == 403

    # Admin deletes payment -> 204 No Content
    admin_del_pay = await client.delete(
        f"/api/v1/settlements/payments/{pay_id}",
        headers=headers_admin,
    )
    assert admin_del_pay.status_code == 204

    # Admin deletes debt waiver -> 204 No Content
    admin_del_waiver = await client.delete(
        f"/api/v1/settlements/waivers/{waiver_id}",
        headers=headers_admin,
    )
    assert admin_del_waiver.status_code == 204

