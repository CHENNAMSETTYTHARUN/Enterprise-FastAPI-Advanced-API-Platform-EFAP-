from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base, SessionLocal
from app.core.logging import ContextLoggingMiddleware
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.security import hash_password

from app.models.tenant import Tenant
from app.models.user import User, Role, Permission
from app.models.customer import Customer
from app.models.inventory import InventoryItem

from app.routers import (
    auth, customers_v1, customers_v2, customers, sessions,
    permissions, audit, approval, bookings, inventory,
    idempotency, webhooks, external, health, tasks, performance, tenants, scheduled_jobs
)


def seed_demo_data():
    db = SessionLocal()
    try:
        tenant_a = db.query(Tenant).filter(Tenant.domain == "company-a.com").first()
        if not tenant_a:
            tenant_a = Tenant(name="Company A", domain="company-a.com")
            db.add(tenant_a)
            db.commit()
            db.refresh(tenant_a)

        tenant_b = db.query(Tenant).filter(Tenant.domain == "company-b.com").first()
        if not tenant_b:
            tenant_b = Tenant(name="Company B", domain="company-b.com")
            db.add(tenant_b)
            db.commit()
            db.refresh(tenant_b)

        perms = [
            ("customer:create", "Create Customer"),
            ("customer:read", "Read Customer"),
            ("customer:update", "Update Customer"),
            ("customer:delete", "Delete Customer"),
            ("audit:read", "Read Audit Logs"),
            ("admin:all", "Full Admin Privileges")
        ]
        perm_objs = {}
        for p_name, p_desc in perms:
            p_obj = db.query(Permission).filter(Permission.name == p_name).first()
            if not p_obj:
                p_obj = Permission(name=p_name, description=p_desc)
                db.add(p_obj)
                db.commit()
                db.refresh(p_obj)
            perm_objs[p_name] = p_obj

        roles = [("Admin", "Administrator"), ("Manager", "Manager"), ("User", "Standard User")]
        role_objs = {}
        for r_name, r_desc in roles:
            r_obj = db.query(Role).filter(Role.name == r_name).first()
            if not r_obj:
                r_obj = Role(name=r_name, description=r_desc)
                db.add(r_obj)
                db.commit()
                db.refresh(r_obj)
            role_objs[r_name] = r_obj

        if perm_objs["admin:all"] not in role_objs["Admin"].permissions:
            role_objs["Admin"].permissions.append(perm_objs["admin:all"])
        for p in ["customer:create", "customer:read", "customer:update"]:
            if perm_objs[p] not in role_objs["Manager"].permissions:
                role_objs["Manager"].permissions.append(perm_objs[p])
        if perm_objs["customer:read"] not in role_objs["User"].permissions:
            role_objs["User"].permissions.append(perm_objs["customer:read"])
        db.commit()

        admin = db.query(User).filter(User.email == "admin@company-a.com").first()
        if not admin:
            admin = User(
                tenant_id=tenant_a.id,
                email="admin@company-a.com",
                full_name="Admin User",
                hashed_password=hash_password("admin123"),
                phone="9999999999"
            )
            admin.roles.append(role_objs["Admin"])
            db.add(admin)
            db.commit()

        tenant_b_user = db.query(User).filter(User.email == "user@company-b.com").first()
        if not tenant_b_user:
            tenant_b_user = User(
                tenant_id=tenant_b.id,
                email="user@company-b.com",
                full_name="Tenant B User",
                hashed_password=hash_password("user123"),
                phone="8888888888"
            )
            tenant_b_user.roles.append(role_objs["User"])
            db.add(tenant_b_user)
            db.commit()

        if db.query(Customer).count() == 0:
            c1 = Customer(tenant_id=tenant_a.id, name="Tharun", email="tharun@company-a.com", phone="9876543210", age=25, status="ACTIVE", version=1)
            c2 = Customer(tenant_id=tenant_a.id, name="Bharath", email="bharath@gmail", phone="9876543211", age=30, status="ACTIVE", version=1)
            c3 = Customer(tenant_id=tenant_b.id, name="guru", email="guru@gmail", phone="9876543212", age=35, status="INACTIVE", version=1)
            db.add_all([c1, c2, c3])
            db.commit()

            import json
            for c in [c1, c2, c3]:
                h = CustomerHistory(
                    customer_id=c.id,
                    version=1,
                    snapshot_data=json.dumps({"name": c.name, "email": c.email, "phone": c.phone, "age": c.age, "status": c.status}),
                    changed_by="system_seed"
                )
                db.add(h)
            db.commit()

        if db.query(InventoryItem).count() == 0:
            item1 = InventoryItem(name="Laptop", quantity=10)
            item2 = InventoryItem(name="Smartphone", quantity=5)
            db.add_all([item1, item2])
            db.commit()

    except Exception as exc:
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(
    title="Enterprise FastAPI Advanced API Platform (EFAP)",
    description="Full implementation of 29 Advanced FastAPI Modules",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(ContextLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to Enterprise FastAPI Advanced API Platform (EFAP)"
        }

app.include_router(auth.router)
app.include_router(customers_v1.router)
app.include_router(customers_v2.router)
app.include_router(customers.router)
app.include_router(sessions.router)
app.include_router(permissions.router)
app.include_router(audit.router)
app.include_router(approval.router)
app.include_router(bookings.router)
app.include_router(inventory.router)
app.include_router(idempotency.router)
app.include_router(webhooks.router)
app.include_router(external.router)
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(performance.router)
app.include_router(tenants.router)
app.include_router(scheduled_jobs.router)


