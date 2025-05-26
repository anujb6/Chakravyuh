from fastapi import APIRouter

from routers.commodities import CommoditiesRouter

router = APIRouter()
commodities = CommoditiesRouter()

router.include_router(commodities.router)