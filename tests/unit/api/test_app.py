"""
API应用测试
"""

import json
from datetime import datetime
from enum import Enum

from acolyte.api.app import CustomJSONEncoder, FastAPICustomJSONResponse


class TestApiApp:
    """测试API应用"""

    def test_app_startup(self, test_client):
        """测试应用启动"""
        response = test_client.get("/api/health")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    def test_custom_json_encoder_datetime(self):
        """测试自定义JSON编码器处理datetime"""
        now = datetime.now()
        encoder = CustomJSONEncoder()

        # 编码datetime对象
        encoded = encoder.encode({"time": now})
        decoded = json.loads(encoded)

        # 验证结果
        assert "time" in decoded
        assert decoded["time"] == now.isoformat()

    def test_custom_json_encoder_enum(self):
        """测试自定义JSON编码器处理枚举"""

        # 创建测试枚举
        class TestEnum(Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        encoder = CustomJSONEncoder()

        # 编码枚举对象
        encoded = encoder.encode({"enum": TestEnum.VALUE1})
        decoded = json.loads(encoded)

        # 验证结果
        assert "enum" in decoded
        assert decoded["enum"] == "value1"

    def test_custom_json_response(self):
        """测试自定义JSON响应"""
        # 创建测试数据
        now = datetime.now()

        class TestEnum(Enum):
            VALUE1 = "value1"

        test_data = {"time": now, "enum": TestEnum.VALUE1, "string": "test", "number": 123}

        # 创建响应
        response = FastAPICustomJSONResponse(content=test_data)
        content = response.body.decode("utf-8")
        decoded = json.loads(content)

        # 验证结果
        assert decoded["time"] == now.isoformat()
        assert decoded["enum"] == "value1"
        assert decoded["string"] == "test"
        assert decoded["number"] == 123

    def test_cors_middleware(self, test_client):
        """测试CORS中间件"""
        # 发送预检请求
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        response = test_client.options("/api/health", headers=headers)

        # 验证CORS头
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

        # 验证允许的源
        # FastAPI的CORS中间件在处理预检请求时，会将access-control-allow-origin头设置为请求中的Origin值
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
