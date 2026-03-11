from fastapi import FastAPI


fastapi_app = FastAPI(
    title="Autism Assessment API",
    version="1.0",
)


@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}


@fastapi_app.get("/version")
async def version():
    return {"api": "autism assessment platform"}
