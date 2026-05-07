"""GET /v1/model/info — returns the currently loaded model's identity fields."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/v1/model", tags=["model"])


@router.get("/info")
async def model_info(request: Request) -> dict[str, str]:
    model = request.app.state.loaded_model
    return {
        "model_name": model.model_name,
        "model_version": model.model_version,
        "model_uri": f"models:/{model.model_name}/{model.model_version}",
    }
