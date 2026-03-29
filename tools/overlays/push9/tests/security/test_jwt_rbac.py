import os, jwt, time
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.testclient import TestClient
from src.api.security_middleware import SecurityMiddleware


def app_factory(required_role=None):
    app = Starlette()

    @app.route("/hello")
    async def hello(request: Request):
        return JSONResponse({"ok": True})

    app.add_middleware(SecurityMiddleware, required_role=required_role)
    return app


def _token(role="viewer"):
    payload = {"sub": "user-1", "role": role, "iat": int(time.time())}
    return jwt.encode(payload, "testsecret", algorithm="HS256")


def test_jwt_access_with_role():
    os.environ["GMNAP_JWT_SECRET"] = "testsecret"
    app = app_factory(required_role="operator")
    client = TestClient(app)
    tok = _token(role="operator")
    r = client.get("/hello", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_jwt_forbidden_without_role():
    os.environ["GMNAP_JWT_SECRET"] = "testsecret"
    app = app_factory(required_role="admin")
    client = TestClient(app)
    tok = _token(role="viewer")
    r = client.get("/hello", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
