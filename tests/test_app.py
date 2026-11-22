import pytest
from app import create_app, grade
from common import db


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING":True,"DATABASE":str(tmp_path/"test.db"),"SECRET_KEY":"test-secret-for-tests-only-123456789"})


@pytest.fixture
def client(app):
    return app.test_client()


def register_login(client, username="alice"):
    csrf = client.get("/api/session").json["csrf"]
    headers = {"X-CSRF-Token":csrf}
    payload = {"username":username,"password":"test-password-123"}
    assert client.post("/api/register",json=payload,headers=headers).status_code == 201
    response = client.post("/api/login",json=payload,headers=headers)
    assert response.status_code == 200
    return {"X-CSRF-Token":response.json["csrf"]}


def test_auth_csrf_and_password(client):
    assert client.post("/api/register",json={"username":"a","password":"password-long"}).status_code == 403
    token = client.get("/api/session").json["csrf"]
    assert client.post("/api/register",json={"username":"a","password":"short"},headers={"X-CSRF-Token":token}).status_code == 400
    h = register_login(client)
    assert client.get("/api/session").json["user"]["username"] == "alice"
    assert client.post("/api/logout",headers=h).status_code == 200
    assert client.get("/api/session").json["user"] is None



@pytest.mark.parametrize("score,expected",[(0,"F"),(49,"F"),(50,"D"),(60,"C"),(70,"B"),(80,"A"),(90,"A+"),(100,"A+")])
def test_grade_boundaries(score,expected):
    assert grade(score) == expected


def test_admin_student_permissions_and_results(app,client):
    h = register_login(client)
    assert client.post("/api/students",json={"roll":"X","name":"A"},headers=h).status_code == 403
    with app.app_context():
        db().execute("UPDATE users SET role='admin' WHERE username='alice'")
        db().commit()
    student = app.test_client()
    sh = register_login(student,"student")
    sid = student.get("/api/session").json["user"]["id"]
    assert client.post("/api/students",json={"roll":"23IOT001","name":"Ravi","user_id":sid},headers=h).status_code == 201
    assert client.post("/api/students",json={"roll":"23IOT002","name":"Other"},headers=h).status_code == 201
    assert client.post("/api/exams",json={"name":"Semester 1","subject":"Python"},headers=h).status_code == 201
    records = client.get("/api/records").json
    student_id = records["students"][0]["id"]
    exam_id = records["exams"][0]["id"]
    payload = {"student_id":student_id,"exam_id":exam_id,"score":95}
    assert client.put("/api/results",json=payload,headers=h).json["grade"] == "A+"
    assert client.put("/api/results",json={**payload,"score":101},headers=h).status_code == 400
    assert student.put("/api/results",json=payload,headers=sh).status_code == 403
    visible = student.get("/api/records").json
    assert len(visible["students"]) == 1 and len(visible["results"]) == 1
    outsider = app.test_client()
    register_login(outsider,"outsider")
    assert outsider.get("/api/records").json["results"] == []
    assert client.put(f"/api/students/{student_id}",json={"roll":"23IOT001","name":"Ravi Kumar","user_id":sid},headers=h).status_code == 200
    assert client.put(f"/api/exams/{exam_id}",json={"name":"Semester 1","subject":"Programming"},headers=h).status_code == 200
    assert client.delete(f"/api/exams/{exam_id}",headers=h).status_code == 200
    assert client.get("/api/records").json["results"] == []
    assert client.delete(f"/api/students/{student_id}",headers=h).status_code == 200


def test_admin_cli_and_no_registration_escalation(app,client):
    result = app.test_cli_runner().invoke(args=["create-admin","operator"],input="test-admin-password\ntest-admin-password\n")
    assert result.exit_code == 0
    csrf = client.get("/api/session").json["csrf"]
    client.post("/api/register",json={"username":"hacker","password":"test-password-123","role":"admin"},headers={"X-CSRF-Token":csrf})
    with app.app_context():
        assert db().execute("SELECT role FROM users WHERE username='hacker'").fetchone()[0] == "student"
