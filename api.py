from fastapi import FastAPI
from core.db import Database

app = FastAPI(title="ForgeOps Issue API")

db = Database()


@app.get("/issues")
def list_issues():
    """Return all issues stored in the database."""
    return db.get_issues()
