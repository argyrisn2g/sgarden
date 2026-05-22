from fastapi import APIRouter, HTTPException, status, Depends
from database import products_collection, settings_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

DEFAULT_THRESHOLD = 10
THRESHOLD_KEY = "alert_threshold"


def severity(stock: int, threshold: int) -> str:
    if stock <= threshold * 0.33:
        return "critical"
    elif stock <= threshold * 0.66:
        return "warning"
    return "info"


async def get_threshold() -> int:
    doc = await settings_collection.find_one({"key": THRESHOLD_KEY})
    return doc["value"] if doc else DEFAULT_THRESHOLD


@router.get("")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    threshold = await get_threshold()

    alerts = []
    cursor = products_collection.find({"stock": {"$lt": threshold}})
    async for product in cursor:
        stock = product.get("stock", 0)
        alerts.append({
            "productId": str(product["_id"]),
            "name": product.get("name"),
            "stock": stock,
            "threshold": threshold,
            "severity": severity(stock, threshold),
        })
    return alerts


@router.put("/threshold")
async def set_threshold(body: dict, current_user: dict = Depends(get_current_user)):
    threshold = body.get("threshold")
    if (
        threshold is None
        or isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or threshold < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold must be a non-negative number",
        )

    await settings_collection.update_one(
        {"key": THRESHOLD_KEY},
        {"$set": {"key": THRESHOLD_KEY, "value": threshold}},
        upsert=True,
    )
    return {"threshold": threshold}