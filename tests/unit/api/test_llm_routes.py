"""
LLM配置API路由测试
"""

from acolyte.core.db.models import LlmRole


class TestLlmRoutes:
    """测试LLM配置API路由"""

    def test_get_all_llms(self, test_client, mock_llm_service):
        """测试获取所有LLM配置"""
        response = test_client.get("/api/llms")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Test LLM"

        # 验证服务调用
        mock_llm_service.get_llms.assert_called_once()

    def test_get_llm(self, test_client, mock_llm_service):
        """测试获取单个LLM配置"""
        response = test_client.get("/api/llms/1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test LLM"

        # 验证服务调用
        mock_llm_service.get_llm.assert_called_once_with(1)

    def test_create_llm(self, test_client, mock_llm_service):
        """测试创建LLM配置"""
        llm_data = {
            "name": "Test LLM",
            "api_key": "test_key",
            "base_url": "https://api.test.com",
            "model_name": "test-model",
            "role": LlmRole.NORMAL.value,
            "is_default": True,
        }

        # 设置模拟响应
        mock_llm_service.add_llm.return_value = {
            "success": True,
            "id": 1,
            "name": "Test LLM",
            "base_url": "https://api.test.com",
            "model_name": "test-model",
            "role": "normal",
            "is_default": True,
        }

        response = test_client.post("/api/llms", json=llm_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test LLM"

        # 验证服务调用
        mock_llm_service.add_llm.assert_called_once()
        # 验证传递的参数
        call_args = mock_llm_service.add_llm.call_args[0][0]
        assert call_args["name"] == "Test LLM"
        assert call_args["api_key"] == "test_key"

    def test_update_llm(self, test_client, mock_llm_service):
        """测试更新LLM配置"""
        update_data = {"name": "Updated LLM"}

        response = test_client.put("/api/llms/1", json=update_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Updated LLM"

        # 验证服务调用
        mock_llm_service.update_llm.assert_called_once_with(1, update_data)

    def test_delete_llm(self, test_client, mock_llm_service):
        """测试删除LLM配置"""
        response = test_client.delete("/api/llms/1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "message" in data

        # 验证服务调用
        mock_llm_service.delete_llm.assert_called_once_with(1)

    def test_set_as_default(self, test_client, mock_llm_service):
        """测试设置默认LLM"""
        response = test_client.post("/api/llms/1/set-default")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test LLM"

        # 验证服务调用
        mock_llm_service.set_default_llm.assert_called_once_with(1)

    def test_test_connection(self, test_client, mock_llm_service):
        """测试LLM连接测试"""
        response = test_client.post("/api/llms/1/test")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "elapsed_time" in data

        # 验证服务调用
        mock_llm_service.test_connection.assert_called_once_with(1)

    def test_create_llm_invalid_data(self, test_client):
        """测试创建LLM配置时提供无效数据"""
        # 缺少必要字段
        invalid_data = {
            "name": "Test LLM"
            # 缺少api_key, base_url, model_name
        }

        response = test_client.post("/api/llms", json=invalid_data)

        # 验证响应
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data  # 包含错误详情

    def test_get_nonexistent_llm(self, test_client, mock_llm_service):
        """测试获取不存在的LLM配置"""
        # 模拟服务返回错误
        mock_llm_service.get_llm.return_value = {"success": False, "error": "LLM配置不存在"}

        response = test_client.get("/api/llms/999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
