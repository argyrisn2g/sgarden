from fastapi import APIRouter, HTTPException, status, Depends
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user
from models.order import OrderRequest
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/orders", tags=["orders"])

VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending":   ["confirmed", "cancelled"],
    "confirmed": ["shipped"],
    "shipped":   ["delivered"],
    "delivered": [],
    "cancelled": [],
}


def order_to_response(order: dict) -> dict:
    return {
        "id": str(order["_id"]),
        "status": order.get("status", "pending"),
        "items": order.get("items", []),
        "total": order.get("total", 0),
        "createdAt": order["createdAt"].isoformat() if order.get("createdAt") else None,
        "updatedAt": order["updatedAt"].isoformat() if order.get("updatedAt") else None,
    }


async def calculate_total(items: list) -> float:
    total = 0.0
    for item in items:
        if not ObjectId.is_valid(item["productId"]):
            continue
        product = await products_collection.find_one({"_id": ObjectId(item["productId"])})
        if product and product.get("price") is not None:
            total += product["price"] * item["quantity"]
    return round(total, 2)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderRequest, current_user: dict = Depends(get_current_user)):
    items = [{"productId": item.productId, "quantity": item.quantity} for item in request.items]

    # Phase 1: validate stock for every item before touching anything
    fetched = {}
    for item in items:
        if not ObjectId.is_valid(item["productId"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID"
            )
        product = await products_collection.find_one({"_id": ObjectId(item["productId"])})
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found"
            )
        if (product.get("stock") or 0) < item["quantity"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.get('name', item['productId'])}'",
            )
        fetched[item["productId"]] = product

    # Phase 2: all checks passed — reduce stock and create order
    total = round(
        sum(fetched[item["productId"]].get("price", 0) * item["quantity"] for item in items), 2
    )

    for item in items:
        await products_collection.update_one(
            {"_id": ObjectId(item["productId"])},
            {"$inc": {"stock": -item["quantity"]}, "$set": {"updatedAt": datetime.utcnow()}},
        )

    order_doc = {
        "status": "pending",
        "items": items,
        "total": total,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }
    result = await orders_collection.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id
    return order_to_response(order_doc)


@router.get("")
async def get_all_orders(
    status: str = None,
    current_user: dict = Depends(get_current_user),
):
    query = {"status": status} if status else {}
    orders = []
    cursor = orders_collection.find(query)
    async for order in cursor:
        orders.append(order_to_response(order))
    return orders


@router.get("/{order_id}")
async def get_order_by_id(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return order_to_response(order)


@router.put("/{order_id}")
async def update_order(order_id: str, request: OrderRequest, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    items = [{"productId": item.productId, "quantity": item.quantity} for item in request.items]
    total = await calculate_total(items)

    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"items": items, "total": total, "updatedAt": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    return order_to_response(order)


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    new_status = body.get("status")
    current_status = order.get("status", "pending")
    allowed = VALID_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'",
        )

    await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": new_status, "updatedAt": datetime.utcnow()}},
    )

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    return order_to_response(order)


@router.delete("/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {"message": "Order deleted"}