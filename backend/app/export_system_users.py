"""Private Docker-to-Docker export; stdout must be captured, never displayed."""
import asyncio
import json

from sqlalchemy import select
from app.db.database import SessionLocal, engine
from app.models import User


async def main():
    async with SessionLocal() as session:
        users = (await session.scalars(select(User).order_by(User.created_at))).all()
        print(json.dumps([{
            "email": user.email, "password_hash": user.password_hash,
            "role": user.role, "created_at": user.created_at.isoformat(),
        } for user in users]))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
