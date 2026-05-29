"""
WebSocket连接管理器。
管理所有WebSocket连接，负责行情推送和预警通知。

遵循架构方案4.2节 WebSocket事件定义：
- market:update - 行情刷新
- warning:trigger - 预警触发
- warning:resolve - 预警解除
- config:changed - 配置变更
- heartbeat - 心跳
"""

import json
import asyncio
from typing import Set, Any, Dict
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)

    async def broadcast(self, event: str, data: Any):
        """广播消息到所有连接的客户端"""
        message = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False)
        stale = set()
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.add(ws)
        self._connections -= stale

    async def broadcast_market_update(self, quotes: list):
        """广播行情更新 (market:update)"""
        await self.broadcast("market:update", quotes)

    async def broadcast_warning_trigger(self, warning: Dict[str, Any]):
        """广播预警触发 (warning:trigger)"""
        await self.broadcast("warning:trigger", warning)

    async def broadcast_warning_resolve(self, warning_id: str):
        """广播预警解除 (warning:resolve)"""
        await self.broadcast("warning:resolve", {"id": warning_id})

    async def broadcast_config_change(self, change_type: str):
        """广播配置变更 (config:changed)"""
        await self.broadcast("config:changed", {"type": change_type})

    async def send_heartbeat(self):
        """发送心跳"""
        import time
        await self.broadcast("heartbeat", {"timestamp": time.time()})

    @property
    def count(self) -> int:
        return len(self._connections)


# 全局单例
ws_manager = ConnectionManager()
