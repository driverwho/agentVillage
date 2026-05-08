import pytest
from httpx import AsyncClient
from server.main import app


@pytest.mark.asyncio
async def test_full_game_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 获取世界状态
        r = await client.get("/world")
        assert r.status_code == 200
        assert "farmer" in r.json()["npcs"]
        assert "bartender" in r.json()["npcs"]

        # 2. 推进时间
        r = await client.post("/time/advance", params={"minutes": 60})
        assert r.status_code == 200
        data = r.json()
        assert "game_time" in data

        # 3. 与农夫对话
        r = await client.post("/api/chat/farmer", params={"message": "你好"})
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert "options" in data

        # 4. 获取玩家状态
        r = await client.get("/api/player")
        assert r.status_code == 200
        data = r.json()
        assert "health" in data

        # 5. 与酒保对话
        r = await client.post("/api/chat/bartender", params={"message": "最近有什么新闻？"})
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data

        # 6. 切换NPC对话
        r = await client.post("/time/toggle")
        assert r.status_code == 200

        # 7. 验证不存在的NPC返回404
        r = await client.post("/api/chat/unknown", params={"message": "hello"})
        assert r.status_code == 404

        # 8. 健康检查
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
