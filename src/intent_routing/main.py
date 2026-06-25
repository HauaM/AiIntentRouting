from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Intent Routing Service")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
