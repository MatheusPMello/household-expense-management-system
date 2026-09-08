from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.households import router as households_router
from app.api.v1.persons import router as persons_router
from app.api.v1.fixed_templates import router as fixed_templates_router
from app.api.v1.cycles import router as cycles_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.settlements import router as settlements_router
from app.api.v1.reports import router as reports_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(households_router)
api_v1_router.include_router(persons_router)
api_v1_router.include_router(fixed_templates_router)
api_v1_router.include_router(cycles_router)
api_v1_router.include_router(expenses_router)
api_v1_router.include_router(settlements_router)
api_v1_router.include_router(reports_router)
