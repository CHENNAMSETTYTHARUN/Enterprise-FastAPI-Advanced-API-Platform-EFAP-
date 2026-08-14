from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerV1Response
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/customers", tags=["API Versioning"])

@router.get("/{id}", response_model=CustomerV1Response)
def get_customer_v1(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == id, Customer.tenant_id == current_user.tenant_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerV1Response(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        age=customer.age,
        status=customer.status
    )
