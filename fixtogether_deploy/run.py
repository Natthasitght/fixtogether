import os
import sys
import uvicorn

# Ensure utf-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database import init_db
from app.seed_data import seed

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "app", "fixtogether.db")
    if not os.path.exists(db_path):
        print("Initializing and seeding database...")
        seed()
    else:
        init_db()

    print("================================================================")
    print(" [*] FixTogether - Smart Road Damage Management System with AI")
    print(" [*] Web Application running at: http://localhost:8000")
    print(" [*] Demo Accounts:")
    print("     - Citizen:     somchai       / 1234")
    print("     - Authority:   admin_bma     / 1234")
    print("     - Technician:  mechanic_jack / 1234")
    print("================================================================")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
