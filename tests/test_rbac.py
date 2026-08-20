from app import model
from app.rbac import Role


def create_workspace_helper(db_session, owner_id):
    ws = model.Workspace(name="Engineering Corp", owner_id=owner_id)
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    # Add owner membership
    owner_m = model.WorkspaceMember(user_id=owner_id, workspace_id=ws.id, role=Role.OWNER.value)
    db_session.add(owner_m)
    db_session.commit()
    return ws


def test_rbac_workspace_owner_access(client, auth_headers):
    # Owner creates workspace
    res = client.post("/workspace/", json={"name": "Owner Workspace"}, headers=auth_headers)
    assert res.status_code == 201
    ws_id = res.json()["id"]

    # Owner creates project
    proj_res = client.post(f"/project/workspace/{ws_id}", json={
        "name": "Backend Engine",
        "description": "FastAPI",
        "private": False
    }, headers=auth_headers)
    assert proj_res.status_code == 201


def test_rbac_viewer_cannot_create_task(client, db_session, test_user, test_viewer_user, viewer_headers):
    # 1. Setup workspace & project
    ws = create_workspace_helper(db_session, test_user.id)
    proj = model.Project(name="Core Project", workspace_id=ws.id, owner_id=test_user.id, private=False)
    db_session.add(proj)
    db_session.commit()

    # 2. Add Viewer user to workspace with VIEWER role
    viewer_member = model.WorkspaceMember(user_id=test_viewer_user.id, workspace_id=ws.id, role=Role.VIEWER.value)
    db_session.add(viewer_member)
    db_session.commit()

    # 3. Viewer CAN read tasks
    get_res = client.get(f"/tasks/project/{proj.id}", headers=viewer_headers)
    assert get_res.status_code == 200

    # 4. Viewer CANNOT create task -> 403 Forbidden!
    post_res = client.post(f"/tasks/project/{proj.id}", json={
        "title": "Unauthorized Task",
        "description": "Should fail",
        "priority": "high"
    }, headers=viewer_headers)
    assert post_res.status_code == 403
    assert "Insufficient permissions" in post_res.json()["detail"]


def test_rbac_member_can_create_task(client, db_session, test_user, test_member_user, member_headers):
    # 1. Setup workspace & project
    ws = create_workspace_helper(db_session, test_user.id)
    proj = model.Project(name="Core Project", workspace_id=ws.id, owner_id=test_user.id, private=False)
    db_session.add(proj)
    db_session.commit()

    # 2. Add Member user to workspace with MEMBER role
    member_rec = model.WorkspaceMember(user_id=test_member_user.id, workspace_id=ws.id, role=Role.MEMBER.value)
    db_session.add(member_rec)
    db_session.commit()

    # 3. Member CAN create task -> 201 Created!
    post_res = client.post(f"/tasks/project/{proj.id}", json={
        "title": "Member Task",
        "description": "Should succeed",
        "priority": "high"
    }, headers=member_headers)
    assert post_res.status_code == 201
    assert post_res.json()["title"] == "Member Task"


def test_rbac_viewer_cannot_comment(client, db_session, test_user, test_viewer_user, viewer_headers):
    ws = create_workspace_helper(db_session, test_user.id)
    proj = model.Project(name="Core Project", workspace_id=ws.id, owner_id=test_user.id, private=False)
    db_session.add(proj)
    db_session.commit()

    task = model.Tasks(project_id=proj.id, title="Test Task", priority="medium")
    db_session.add(task)
    db_session.commit()

    # Viewer member
    viewer_member = model.WorkspaceMember(user_id=test_viewer_user.id, workspace_id=ws.id, role=Role.VIEWER.value)
    db_session.add(viewer_member)
    db_session.commit()

    # Viewer CANNOT post comment -> 403 Forbidden!
    comm_res = client.post(f"/comments/task/{task.id}", json={
        "content": "Unauthorized comment"
    }, headers=viewer_headers)
    assert comm_res.status_code == 403


def test_rbac_non_member_access_denied(client, db_session, test_user, test_viewer_user, viewer_headers):
    # Workspace created by owner, viewer is NOT a member
    ws = create_workspace_helper(db_session, test_user.id)

    # Non-member tries to get workspace -> 403 Forbidden
    res = client.get(f"/workspace/{ws.id}", headers=viewer_headers)
    assert res.status_code == 403
