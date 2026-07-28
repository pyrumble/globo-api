from fastapi import FastAPI, Form, Header, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
import shutil
import time
import sqlite3
import json
import os
from fastapi.staticfiles import StaticFiles
import uvicorn


conn = sqlite3.connect("database.db")
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS globos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gif_name TEXT NOT NULL,
    ext TEXT NOT NULL,
    mime TEXT NOT NULL,
    uploaded_at INTEGER NOT NULL,
    gif_url TEXT
    )
    """)
conn.close()

with open("config.json") as f:
    c = json.load(f)
    PORT = c["port"]
    HN = c["hostname"]
    AUTH = c["password"]

app = FastAPI()
app.mount("/gifs", StaticFiles(directory="storage/gifs"), name="gifs")


@app.post("/upload")
def upload(user_id: int = Form(), gif_name: str =  Form(), file: UploadFile = File(...),auth: str | None = Header(default=None, alias="password")):
    if auth != AUTH:
        return HTMLResponse(status_code=401)
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    ext = file.filename.split(".")[-1]
    cur.execute(
        """
        INSERT INTO globos(user_id,gif_name,ext, mime, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (   
            user_id,
            gif_name,
            ext,
            file.content_type,
            int(time.time())
        )
    )
    conn.commit()
    gif_id = cur.lastrowid
    url = f"http://{HN}:{PORT}/gifs/{gif_id}.gif"
    cur.execute("UPDATE globos SET gif_url=? WHERE id=?", (url,gif_id))
    conn.commit()
    path = f"storage/gifs/{gif_id}.{ext}"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn.close()

    return {"id": gif_id, "url": url}

@app.delete("/gif/{gif_id}")
def delete_gif(gif_id: int, auth: str | None = Header(default=None, alias="password")):
    if auth != AUTH:
        return HTMLResponse(status_code=401)
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT ext FROM globos WHERE id=?", (gif_id,))
    res = cur.fetchone()
    if not res: 
        return HTMLResponse(status_code=404)
    ext = res[0]
    cur.execute("DELETE FROM globos WHERE id=?", (gif_id,))
    conn.commit()
    os.remove(f"storage/gifs/{gif_id}.{ext}")
    conn.close()


@app.get("/gif/{gif_id}")
def gif(gif_id: int):

    conn = sqlite3.connect("database.db")

    row = conn.execute(
        "SELECT mime, ext FROM globos WHERE id=?",
        (gif_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return HTMLResponse(status_code=404)

    mime, ext = row

    return FileResponse(
        f"storage/gifs/{gif_id}.{ext}",
        media_type=mime
    )

@app.get("/mygifs/{user_id}")
def mygifs(user_id: int, auth: str | None = Header(default=None, alias="password")):
    if auth != AUTH:
        return HTMLResponse(status_code=401)
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, gif_name, gif_url, uploaded_at FROM globos WHERE user_id=?", (user_id,))
    res = cur.fetchall()
    conn.close()

    if len(res) < 1:
        return HTMLResponse(status_code=404)

    return res

@app.get("/ourgifs")
def gifs(auth: str | None = Header(default=None, alias="password")):
    if auth != AUTH:
        return HTMLResponse(status_code=401)
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, gif_name, gif_url, user_id, uploaded_at FROM globos",)
    res = cur.fetchall()
    conn.close()

    if len(res) < 1:
        return HTMLResponse(status_code=404)

    return res


uvicorn.run(app, port=PORT, host="0.0.0.0")