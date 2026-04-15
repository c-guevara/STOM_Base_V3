
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from web_socket import WebSocketManager


app = FastAPI(title="STOM Trading Dashboard API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ws_manager = WebSocketManager()


@app.get("/")
async def root():
    return {"message": "STOM Trading Dashboard API"}


@app.get("/api/market/{market}")
async def get_market_data(market: str):
    from database import DatabaseManager
    db = DatabaseManager()
    return {
        "jangolist": db.get_jangolist(market),
        "chegeollist": db.get_chegeollist(market),
        "tradelist": db.get_tradelist(market),
        "totaltradelist": db.get_totaltradelist(market)
    }


@app.websocket("/ws/{market}")
async def websocket_endpoint(websocket: WebSocket, market: str):
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)

    try:
        import asyncio
        asyncio.create_task(ws_manager.broadcast_data(market))

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
