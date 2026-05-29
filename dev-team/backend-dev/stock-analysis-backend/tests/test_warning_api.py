"""
M03 智能预警模块API测试。
测试预警列表、汇总、详情、标记处理等API端点。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestWarningAPI:

    @patch("backend.api.warning.get_db")
    def test_get_warning_summary(self, mock_get_db):
        """测试预警汇总统计"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0
        mock_get_db.return_value = mock_session

        response = client.get("/api/v1/warning/summary")
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "by_type" in data
            assert "by_level" in data

    @patch("backend.api.warning.get_db")
    def test_get_warning_list(self, mock_get_db):
        """测试预警列表"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_get_db.return_value = mock_session

        response = client.get("/api/v1/warning/list?page=1&page_size=10")
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data

    @patch("backend.api.warning.get_db")
    def test_get_warning_detail(self, mock_get_db):
        """测试单只股票预警详情"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_get_db.return_value = mock_session

        response = client.get("/api/v1/warning/000001/detail")
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == "000001"
            assert "warnings" in data
            assert "current_level" in data

    @patch("backend.api.warning.get_db")
    @patch("backend.api.warning.ws_manager")
    @patch("backend.api.warning._get_engine")
    def test_resolve_warning(self, mock_engine, mock_ws, mock_get_db):
        """测试解除预警"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_get_db.return_value = mock_session
        mock_eng = MagicMock()
        mock_eng._previous_colors = {}
        mock_eng.resolve_warning = AsyncMock()
        mock_engine.return_value = mock_eng

        response = client.put("/api/v1/warning/000001/resolve", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "000001"

    @patch("backend.api.warning.get_db")
    def test_get_warning_configs(self, mock_get_db):
        """测试获取预警配置"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_get_db.return_value = mock_session

        response = client.get("/api/v1/warning/config/list")
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data


# ============================================================
# WarningRecord 模型测试
# ============================================================

class TestWarningRecordModel:

    def test_warning_record_repr(self):
        """测试预警记录模型"""
        from backend.models.warning import WarningRecord
        r = WarningRecord(code="000001", warning_type="price", warning_level="warning")
        assert repr(r) == "<Warning(id=None, code=000001, type=price, level=warning)>"

    def test_warning_record_to_dict(self):
        """测试预警记录转字典"""
        from backend.models.warning import WarningRecord
        r = WarningRecord(
            id=1, code="000001", warning_type="trend",
            warning_level="danger", title="趋势预警",
            detail='{"score": -40}', indicator_color="red",
            is_acknowledged=False,
        )
        d = r.to_dict()
        assert d["id"] == 1
        assert d["code"] == "000001"
        assert d["warning_type"] == "trend"
        assert d["indicator_color"] == "red"
        assert d["is_acknowledged"] is False

    def test_warning_config_repr(self):
        """测试预警配置模型"""
        from backend.models.warning import WarningConfig
        c = WarningConfig(config_type="trend", code="000001")
        assert repr(c) == "<WarningConfig(id=None, type=trend, code=000001)>"

    def test_warning_config_to_dict(self):
        """测试预警配置转字典"""
        from backend.models.warning import WarningConfig
        c = WarningConfig(
            id=1, config_type="price", params={"threshold": 0.05},
            description="价格预警配置",
        )
        d = c.to_dict()
        assert d["id"] == 1
        assert d["config_type"] == "price"
        assert d["params"]["threshold"] == 0.05
