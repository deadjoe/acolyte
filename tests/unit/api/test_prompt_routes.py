"""
提示词API路由测试
"""



class TestPromptRoutes:
    """测试提示词API路由"""

    def test_get_all_prompts(self, test_client, mock_prompt_service):
        """测试获取所有提示词"""
        response = test_client.get("/api/prompts")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["version"] == "1.0"

        # 验证服务调用
        mock_prompt_service.get_prompts.assert_called_once_with(model_target=None, version=None)

    def test_get_prompt(self, test_client, mock_prompt_service):
        """测试获取单个提示词"""
        response = test_client.get("/api/prompts/1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["version"] == "1.0"
        assert data["content"] == "Test prompt content"

        # 验证服务调用
        mock_prompt_service.get_prompt.assert_called_once_with(1)

    def test_create_prompt(self, test_client, mock_prompt_service):
        """测试创建提示词"""
        prompt_data = {
            "version": "1.0",
            "model_target": "general",
            "content": "Test prompt content",
            "is_active": True,
        }

        response = test_client.post("/api/prompts", json=prompt_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["version"] == "1.0"

        # 验证服务调用
        mock_prompt_service.create_prompt.assert_called_once()
        # 验证传递的参数
        call_args = mock_prompt_service.create_prompt.call_args[0][0]
        assert call_args["version"] == "1.0"
        assert call_args["model_target"] == "general"
        assert call_args["content"] == "Test prompt content"

    def test_update_prompt(self, test_client, mock_prompt_service):
        """测试更新提示词"""
        update_data = {"version": "1.1", "is_active": True}

        response = test_client.put("/api/prompts/1", json=update_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["version"] == "1.1"

        # 验证服务调用
        mock_prompt_service.update_prompt.assert_called_once_with(1, update_data)

    def test_delete_prompt(self, test_client, mock_prompt_service):
        """测试删除提示词"""
        response = test_client.delete("/api/prompts/1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "message" in data

        # 验证服务调用
        mock_prompt_service.delete_prompt.assert_called_once_with(1, delete_file=False)

    def test_create_prompt_invalid_data(self, test_client):
        """测试创建提示词时提供无效数据"""
        # 缺少必要字段
        invalid_data = {
            "version": "1.0"
            # 缺少content
        }

        response = test_client.post("/api/prompts", json=invalid_data)

        # 验证响应
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data  # 包含错误详情

    def test_get_nonexistent_prompt(self, test_client, mock_prompt_service):
        """测试获取不存在的提示词"""
        # 模拟服务返回错误
        mock_prompt_service.get_prompt.return_value = {"success": False, "error": "提示词不存在"}

        response = test_client.get("/api/prompts/999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
