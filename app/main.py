from fastapi import FastAPI

app = FastAPI(title="Ultra Dash")

@app.get("/")
def root():
    return {"status": "alive"}
