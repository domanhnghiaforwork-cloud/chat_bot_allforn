import argparse
import asyncio

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import AdminAuditLog, User


async def promote_admin(email: str, reason: str) -> None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if not user:
            raise SystemExit("Không tìm thấy user")
        old_role = user.role
        user.role = "admin"
        session.add(
            AdminAuditLog(
                admin_id=user.id,
                action="role_change",
                target=f"user:{user.id}",
                old_value=old_role,
                new_value="admin",
                reason=reason,
            )
        )
        await session.commit()
        print(f"Đã gán role=admin cho {user.email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lệnh quản trị chatbot v4.2")
    commands = parser.add_subparsers(dest="command", required=True)
    promote = commands.add_parser("promote-admin")
    promote.add_argument("email")
    promote.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "promote-admin":
        asyncio.run(promote_admin(args.email, args.reason))


if __name__ == "__main__":
    main()
