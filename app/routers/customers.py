import csv
import io
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.customer import Customer, CustomerHistory
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerV1Response,
    CustomerBulkCreate, CustomerBulkResponse, DuplicateCheckRequest, DuplicateCheckResponse
)
from app.dependencies import get_current_user, require_permission
from app.services.audit_service import log_audit
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/customers", tags=["Customer Management"])


@router.post("", response_model=CustomerV1Response, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create"))
):
    customer = Customer(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        age=payload.age,
        status=payload.status or "ACTIVE",
        version=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    history = CustomerHistory(
        customer_id=customer.id,
        version=1,
        snapshot_data=json.dumps({"name": customer.name, "email": customer.email, "phone": customer.phone, "age": customer.age, "status": customer.status}),
        changed_by=current_user.email
    )
    db.add(history)
    db.commit()

    log_audit(db, action="CREATE", entity="Customer", entity_id=str(customer.id), user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"Created customer {customer.name}")
    cache_service.delete(f"customer:{customer.id}")
    return customer

@router.get("", response_model=List[CustomerV1Response])
def get_customers_dynamic_filtering(
    name: Optional[str] = None,
    email: Optional[str] = None,
    status: Optional[str] = None,
    status__ne: Optional[str] = None,
    status__in: Optional[str] = Query(None, description="Comma-separated status values e.g. ACTIVE,INACTIVE"),
    age__gt: Optional[int] = None,
    age__lt: Optional[int] = None,
    age__gte: Optional[int] = None,
    age__lte: Optional[int] = None,
    name__contains: Optional[str] = None,
    name__startswith: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)
    if name:
        query = query.filter(Customer.name == name)
    if email:
        query = query.filter(Customer.email == email)
    if status:
        query = query.filter(Customer.status == status)
    if status__ne:
        query = query.filter(Customer.status != status__ne)
    if status__in:
        statuses = [s.strip() for s in status__in.split(",") if s.strip()]
        query = query.filter(Customer.status.in_(statuses))
    if age__gt is not None:
        query = query.filter(Customer.age > age__gt)
    if age__lt is not None:
        query = query.filter(Customer.age < age__lt)
    if age__gte is not None:
        query = query.filter(Customer.age >= age__gte)
    if age__lte is not None:
        query = query.filter(Customer.age <= age__lte)
    if name__contains:
        query = query.filter(Customer.name.contains(name__contains))
    if name__startswith:
        query = query.filter(Customer.name.startswith(name__startswith))
    return query.all()

@router.get("/search")
def search_customers(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)
    if q:
        search_pattern = f"%{q}%"
        query = query.filter(or_(Customer.name.like(search_pattern), Customer.email.like(search_pattern), Customer.phone.like(search_pattern)))

    total = query.count()
    sort_attr = getattr(Customer, sort_by, Customer.name)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())

    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "age": c.age,
                "status": c.status
            } for c in items
        ],
        "page": page,
        "limit": limit,
        "total": total
    }

@router.post("/bulk", response_model=CustomerBulkResponse)
def bulk_create_customers(
    payload: CustomerBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create"))
):
    created_ids = []
    updated_ids = []
    errors = []
    seen_emails_in_batch = set()

    total_records = len(payload.customers)

    for idx, item in enumerate(payload.customers):
        try:
            # Check if customer exists by ID
            existing_cust = None
            if item.id:
                existing_cust = db.query(Customer).filter(
                    Customer.id == item.id,
                    Customer.tenant_id == current_user.tenant_id
                ).first()

            # If not found by ID but email is supplied, check by email
            if not existing_cust and item.email:
                existing_cust = db.query(Customer).filter(
                    Customer.email == item.email,
                    Customer.tenant_id == current_user.tenant_id
                ).first()

            if existing_cust:
                # Perform bulk update
                if item.name:
                    existing_cust.name = item.name
                if item.phone:
                    existing_cust.phone = item.phone
                if item.age is not None:
                    existing_cust.age = item.age
                if item.status:
                    existing_cust.status = item.status
                existing_cust.version += 1
                db.flush()
                updated_ids.append(existing_cust.id)
                log_audit(db, action="UPDATE", entity="Customer", entity_id=str(existing_cust.id), user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"Bulk updated customer {existing_cust.name}")
            else:
                # Validate mandatory fields for new record
                if not item.name or not item.email:
                    errors.append({"index": idx, "error": "Missing mandatory fields 'name' or 'email' for creation"})
                    continue

                if item.email in seen_emails_in_batch:
                    errors.append({"index": idx, "email": item.email, "error": "Duplicate email in bulk payload"})
                    continue

                seen_emails_in_batch.add(item.email)

                cust = Customer(
                    tenant_id=current_user.tenant_id,
                    name=item.name,
                    email=item.email,
                    phone=item.phone,
                    age=item.age,
                    status=item.status or "ACTIVE",
                    version=1
                )
                db.add(cust)
                db.flush()
                created_ids.append(cust.id)
                log_audit(db, action="CREATE", entity="Customer", entity_id=str(cust.id), user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"Bulk created customer {cust.name}")
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    db.commit()

    successful = len(created_ids) + len(updated_ids)
    failed = len(errors)

    return CustomerBulkResponse(
        total_records=total_records,
        successful=successful,
        failed=failed,
        created_ids=created_ids,
        updated_ids=updated_ids,
        errors=errors,
        message="Bulk operations completed",
        count=successful
    )

@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate_customer(
    payload: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    if payload.email:
        exist = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id, Customer.email == payload.email).first()
        if exist:
            return DuplicateCheckResponse(is_duplicate=True, matched_field="email", message="Customer with this email already exists")
    if payload.phone:
        exist = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id, Customer.phone == payload.phone).first()
        if exist:
            return DuplicateCheckResponse(is_duplicate=True, matched_field="phone", message="Customer with this phone already exists")
    return DuplicateCheckResponse(is_duplicate=False, matched_field=None, message="No duplicates found")

@router.post("/import")
async def import_customers_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create"))
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV format")
        
    contents = await file.read()
    decoded = contents.decode("utf-8")
    io_string = io.StringIO(decoded)
    reader = csv.DictReader(io_string)
    
    total = 0
    imported = 0
    failed = 0
    
    for row in reader:
        total += 1
        name = row.get("name")
        email = row.get("email")
        if not name or not email:
            failed += 1
            continue
        try:
            cust = Customer(
                tenant_id=current_user.tenant_id,
                name=name,
                email=email,
                phone=row.get("phone"),
                age=int(row.get("age")) if row.get("age") and row.get("age").isdigit() else None,
                status=row.get("status") or "ACTIVE",
                version=1
            )
            db.add(cust)
            db.commit()
            imported += 1
        except Exception:
            db.rollback()
            failed += 1
            
    return {"total_records": total, "imported": imported, "failed": failed}

@router.get("/export")
def export_customers_csv(
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)
    if status_filter:
        query = query.filter(Customer.status == status_filter)
    customers = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Age", "Status", "Version"])

    for c in customers:
        writer.writerow([c.id, c.name, c.email, c.phone or "", c.age or "", c.status, c.version])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers_export.csv"}
    )

@router.get("/{id}", response_model=CustomerV1Response)
def get_customer_cached(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    cache_key = f"customer:{id}"
    cached = cache_service.get(cache_key)
    if cached:
        return CustomerV1Response(**json.loads(cached))

    customer = db.query(Customer).filter(Customer.id == id, Customer.tenant_id == current_user.tenant_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    res_data = CustomerV1Response.model_validate(customer)
    cache_service.set(cache_key, res_data.model_dump_json(), ttl_seconds=120)
    return res_data

@router.put("/{id}", response_model=CustomerV1Response)
def update_customer_with_history(
    id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:update"))
):
    customer = db.query(Customer).filter(Customer.id == id, Customer.tenant_id == current_user.tenant_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    if payload.name is not None:
        customer.name = payload.name
    if payload.email is not None:
        customer.email = payload.email
    if payload.phone is not None:
        customer.phone = payload.phone
    if payload.age is not None:
        customer.age = payload.age
    if payload.status is not None:
        customer.status = payload.status

    customer.version += 1
    db.commit()
    db.refresh(customer)

    history = CustomerHistory(
        customer_id=customer.id,
        version=customer.version,
        snapshot_data=json.dumps({"name": customer.name, "email": customer.email, "phone": customer.phone, "age": customer.age, "status": customer.status}),
        changed_by=current_user.email
    )
    db.add(history)
    db.commit()

    log_audit(db, action="UPDATE", entity="Customer", entity_id=str(customer.id), user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"Updated customer {customer.name} to v{customer.version}")
    cache_service.delete(f"customer:{customer.id}")
    return customer

@router.get("/{id}/history")
def get_customer_history(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:read"))
):
    customer = db.query(Customer).filter(Customer.id == id, Customer.tenant_id == current_user.tenant_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    history_records = db.query(CustomerHistory).filter(CustomerHistory.customer_id == id).order_by(CustomerHistory.version.asc()).all()
    return [
        {
            "id": h.id,
            "version": h.version,
            "snapshot_data": json.loads(h.snapshot_data),
            "changed_by": h.changed_by,
            "created_at": h.created_at
        } for h in history_records
    ]

@router.delete("/{id}")
def delete_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:delete"))
):
    customer = db.query(Customer).filter(Customer.id == id, Customer.tenant_id == current_user.tenant_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    old_values = {"name": customer.name, "email": customer.email, "status": customer.status}
    db.delete(customer)
    db.commit()

    cache_service.delete(f"customer:{id}")
    log_audit(
        db,
        action="DELETE",
        entity="Customer",
        entity_id=str(id),
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        old_values=old_values,
        details=f"Deleted customer {id}"
    )
    return {"message": "Customer deleted successfully", "id": id}

