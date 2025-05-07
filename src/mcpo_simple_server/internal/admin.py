from fastapi import APIRouter

router = APIRouter(
    tags=["admin"],
)


@router.get("/")
async def read_admin():
    return {"admin": "Admin Panel"}


@router.get("/performance")
async def read_performance():
    return {"status": "OK", "performance": "Good"}
