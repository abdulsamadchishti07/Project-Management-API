from app import model
from app.rbac import Role


def test_soft_delete_and_audit_log_flow(client, auth_headers, test_user, db_session):
    # 1. Create Workspace
    ws_res = client.post("/workspace/", json={"name": "Audit Test Workspace"}, headers=auth_headers)
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Create Project
    proj_res = client.post(f"/project/workspace/{ws_id}", json={
        "name": "Audit Project",
        "description": "Testing soft deletes",
        "private": False
    }, headers=auth_headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 3. Create Task
    task_res = client.post(f"/tasks/project/{proj_id}", json={
        "title": "Task to Delete",
        "description": "Will be soft deleted",
        "priority": "low"
    }, headers=auth_headers)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 4. Soft Delete Task
    del_task_res = client.delete(f"/tasks/{task_id}", headers=auth_headers)
    assert del_task_res.status_code == 204

    # Verify task is soft deleted in DB
    db_task = db_session.query(model.Tasks).filter(model.Tasks.id == task_id).first()
    assert db_task.is_deleted is True
    assert db_task.deleted_at is not None

    # Verify task does NOT appear in project tasks list
    list_tasks_res = client.get(f"/tasks/project/{proj_id}", headers=auth_headers)
    assert list_tasks_res.status_code == 200
    assert len(list_tasks_res.json()) == 0

    # 5. Soft Delete Project
    del_proj_res = client.delete(f"/project/{proj_id}", headers=auth_headers)
    assert del_proj_res.status_code == 204

    # Verify project is hidden from workspace project list
    list_projs_res = client.get(f"/project/workspace/{ws_id}", headers=auth_headers)
    assert list_projs_res.status_code == 200
    assert len(list_projs_res.json()) == 0

    # 6. Check Audit Logs recorded in PostgreSQL
    audit_res = client.get(f"/workspace/{ws_id}/audit-logs", headers=auth_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 4

    actions = [l["action"] for l in logs]
    assert "WORKSPACE_CREATED" in actions
    assert "PROJECT_CREATED" in actions
    assert "TASK_CREATED" in actions
    assert "TASK_DELETED" in actions
    assert "PROJECT_DELETED" in actions
