from fastapi import APIRouter, HTTPException, status, Depends
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user
from bson import ObjectId
from datetime import datetime
from collections import defaultdict

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sales")
async def get_sales_analytics(
    startDate: str = None,
    endDate: str = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if startDate or endDate:
        date_filter = {}
        if startDate:
            try:
                date_filter["$gte"] = datetime.fromisoformat(startDate)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid startDate format"
                )
        if endDate:
            try:
                end = datetime.fromisoformat(endDate)
                date_filter["$lte"] = datetime(end.year, end.month, end.day, 23, 59, 59)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid endDate format"
                )
        query["createdAt"] = date_filter

    orders = []
    async for order in orders_collection.find(query):
        orders.append(order)

    if not orders:
        return {
            "totalRevenue": 0,
            "totalOrders": 0,
            "topProducts": [],
            "revenueByPeriod": [],
        }

    total_revenue = round(sum(o.get("total", 0) for o in orders), 2)
    total_orders = len(orders)

    # Aggregate total quantity sold per product across all matching orders
    product_qty: dict[str, int] = defaultdict(int)
    for order in orders:
        for item in order.get("items", []):
            product_qty[item["productId"]] += item["quantity"]

    # Resolve product names and current prices, sorted by quantity desc
    top_products = []
    for pid, qty in sorted(product_qty.items(), key=lambda x: -x[1])[:10]:
        product = None
        if ObjectId.is_valid(pid):
            product = await products_collection.find_one({"_id": ObjectId(pid)})
        name = product.get("name") if product else pid
        price = product.get("price", 0) if product else 0
        top_products.append({
            "productId": pid,
            "name": name,
            "totalQuantity": qty,
            "totalRevenue": round(qty * price, 2),
        })

    # Revenue grouped by month (YYYY-MM)
    period_revenue: dict[str, float] = defaultdict(float)
    for order in orders:
        created_at = order.get("createdAt")
        if created_at:
            period = created_at.strftime("%Y-%m")
            period_revenue[period] += order.get("total", 0)

    revenue_by_period = [
        {"period": p, "revenue": round(r, 2)}
        for p, r in sorted(period_revenue.items())
    ]

    return {
        "totalRevenue": total_revenue,
        "totalOrders": total_orders,
        "topProducts": top_products,
        "revenueByPeriod": revenue_by_period,
    }
