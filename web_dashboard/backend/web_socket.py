
import asyncio
import pandas as pd
from typing import Dict, List
from fastapi import WebSocket
from database import DatabaseManager


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.db = DatabaseManager()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast_data(self, market: str = "stock"):
        while True:
            try:
                data = {
                    "jangolist": self.db.get_jangolist(market),
                    "chegeollist": self.db.get_chegeollist(market),
                    "tradelist": self.db.get_tradelist(market),
                    "totaltradelist": self.db.get_totaltradelist(market),
                    "timestamp": pd.Timestamp.now().isoformat()
                }

                alerts = self.check_alerts(data["jangolist"])
                if alerts:
                    data["alerts"] = alerts

                for connection in self.active_connections.values():
                    try:
                        await connection.send_json(data)
                    except Exception as e:
                        print(f"Data transmission error: {e}")

                await asyncio.sleep(1)
            except Exception as e:
                print(f"Broadcast error: {e}")
                await asyncio.sleep(1)

    def check_alerts(self, jangolist: List[dict]) -> List[dict]:
        alerts = []
        for item in jangolist:
            if item.get("수익률", 0) > 5.0:
                alerts.append({
                    "type": "profit",
                    "message": f"{item['종목명']} profit rate {item['수익률']:.2f}% reached",
                    "stock": item['종목명']
                })
            elif item.get("수익률", 0) < -3.0:
                alerts.append({
                    "type": "loss",
                    "message": f"{item['종목명']} loss rate {item['수익률']:.2f}% reached",
                    "stock": item['종목명']
                })
        return alerts
