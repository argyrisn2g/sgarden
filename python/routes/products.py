from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from models.product import ProductRequest, ProductResponse
from database import products_collection
from security.jwt_handler import get_current_user
from bson import ObjectId
from datetime import datetime

VALID_CATEGORIES = {"Electronics", "Accessories", "Storage", "Networking"}


def validate_product(request: ProductRequest, is_create: bool = False) -> dict:
    errors = {}
    if is_create and (request.name is None or not request.name.strip()):
        errors["name"] = "name is required"
    elif request.name is not None and not request.name.strip():
        errors["name"] = "name cannot be empty"
    if request.price is not None and request.price <= 0:
        errors["price"] = "price must be a positive number"
    if request.category is not None and request.category not in VALID_CATEGORIES:
        errors["category"] = f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
    return errors

router = APIRouter(prefix="/api/products", tags=["products"])

# CODE QUALITY ISSUE: unused variable
service_name = "ProductService"


def product_to_response(product: dict) -> dict:
    """Convert MongoDB document to API response format."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


def format_product(product: dict) -> dict:
    """CODE QUALITY ISSUE: duplicate of product_to_response above."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


@router.get("")
async def get_all_products(
    page: int = 1,
    limit: int = 10,
    sort: str = None,
    order: str = "asc",
):
    total = await products_collection.count_documents({})
    skip = (page - 1) * limit
    sort_field = sort if sort else "createdAt"
    sort_direction = 1 if order == "asc" else -1

    cursor = products_collection.find().sort(sort_field, sort_direction).skip(skip).limit(limit)
    data = []
    async for product in cursor:
        data.append(product_to_response(product))

    return {"data": data, "page": page, "limit": limit, "total": total}


@router.get("/search")
async def search_products(
    q: str = None,
    category: str = None,
    minPrice: float = None,
    maxPrice: float = None,
):
    filters = []

    if q:
        filters.append({
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]
        })
    if category:
        filters.append({"category": category})
    if minPrice is not None:
        filters.append({"price": {"$gte": minPrice}})
    if maxPrice is not None:
        filters.append({"price": {"$lte": maxPrice}})

    query = {"$and": filters} if filters else {}

    products = []
    cursor = products_collection.find(query)
    async for product in cursor:
        products.append(product_to_response(product))
    return products


@router.get("/stats")
async def get_product_stats():
    total_count = await products_collection.count_documents({})

    price_pipeline = [
        {"$match": {"price": {"$ne": None}}},
        {"$group": {
            "_id": None,
            "averagePrice": {"$avg": "$price"},
            "minPrice": {"$min": "$price"},
            "maxPrice": {"$max": "$price"},
        }},
    ]
    price_result = await products_collection.aggregate(price_pipeline).to_list(1)

    category_pipeline = [
        {"$match": {"category": {"$ne": None}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    ]
    category_result = await products_collection.aggregate(category_pipeline).to_list(None)
    category_count = {item["_id"]: item["count"] for item in category_result}

    return {
        "totalCount": total_count,
        "averagePrice": price_result[0]["averagePrice"] if price_result else 0,
        "minPrice": price_result[0]["minPrice"] if price_result else None,
        "maxPrice": price_result[0]["maxPrice"] if price_result else None,
        "categoryCount": category_count,
    }


@router.get("/{product_id}")
async def get_product_by_id(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product_to_response(product)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(request: ProductRequest, current_user: dict = Depends(get_current_user)):
    errors = validate_product(request, is_create=True)
    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Validation failed", "errors": errors},
        )

    product_doc = {
        "name": request.name,
        "description": request.description,
        "category": request.category,
        "price": request.price,
        "stock": request.stock if request.stock is not None else 0,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await products_collection.insert_one(product_doc)
    product_doc["_id"] = result.inserted_id
    print(f"Created product: {request.name}")
    return product_to_response(product_doc)


async def update_product_legacy(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    """CODE QUALITY ISSUE: duplicate of update_product."""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.put("/{product_id}")
async def update_product(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    errors = validate_product(request, is_create=False)
    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Validation failed", "errors": errors},
        )

    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return {"message": "Product deleted"}


@router.patch("/{product_id}/stock")
async def update_stock(
    product_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    stock = body.get("stock")
    if (
        stock is None
        or isinstance(stock, bool)
        or not isinstance(stock, (int, float))
        or stock < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stock must be a non-negative number",
        )

    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock": stock, "updatedAt": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)
