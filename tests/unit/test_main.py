"""
主程序测试
"""

import os
from unittest.mock import patch

from acolyte.main import main


class TestMain:
    """测试主程序"""

    def test_main_with_default_settings(self):
        """测试使用默认设置启动"""
        # 模拟uvicorn.run
        with patch("acolyte.main.uvicorn.run") as mock_run:
            # 模拟环境变量
            with patch.dict(os.environ, {}, clear=True):
                # 模拟日志
                with patch("acolyte.main.logger") as mock_logger:
                    # 执行主函数
                    main()

                    # 验证日志记录
                    assert mock_logger.info.call_count >= 7  # 至少7次info日志

                    # 验证uvicorn.run调用
                    mock_run.assert_called_once()
                    _, kwargs = mock_run.call_args
                    assert kwargs["host"] == "0.0.0.0"  # 实际默认主机
                    assert kwargs["port"] == 8000  # 默认端口
                    assert kwargs["log_level"] == "error"  # 实际日志级别

    def test_main_with_custom_settings(self):
        """测试使用自定义设置启动"""
        # 模拟uvicorn.run
        with patch("acolyte.main.uvicorn.run") as mock_run:
            # 模拟环境变量
            env_vars = {
                "ACOLYTE_HOST": "0.0.0.0",
                "ACOLYTE_PORT": "9000",
                "ACOLYTE_LOG_LEVEL": "debug",
                "ACOLYTE_LOG_TO_FILE": "1",
                "ACOLYTE_LOG_DIR": "/tmp/logs",
            }
            with patch.dict(os.environ, env_vars, clear=True):
                # 模拟日志
                with patch("acolyte.main.logger") as mock_logger:
                    # 执行主函数
                    main()

                    # 验证日志记录
                    assert mock_logger.info.call_count >= 7  # 至少7次info日志

                    # 验证uvicorn.run调用
                    mock_run.assert_called_once()
                    _, kwargs = mock_run.call_args
                    assert kwargs["host"] == "0.0.0.0"  # 自定义主机
                    assert kwargs["port"] == 9000  # 自定义端口
                    assert kwargs["log_level"] == "error"  # 实际日志级别

    def test_main_with_invalid_log_level(self):
        """测试使用无效的日志级别"""
        # 模拟uvicorn.run
        with patch("acolyte.main.uvicorn.run") as mock_run:
            # 模拟环境变量
            env_vars = {"ACOLYTE_LOG_LEVEL": "invalid"}
            with patch.dict(os.environ, env_vars, clear=True):
                # 模拟stderr
                with patch("sys.stderr") as mock_stderr:
                    # 模拟日志
                    with patch("acolyte.main.logger"):
                        # 执行主函数
                        main()

                        # 验证stderr警告
                        mock_stderr.write.assert_called_once()

                        # 验证日志级别被重置为info
                        assert os.environ["ACOLYTE_LOG_LEVEL"] == "info"

                        # 验证uvicorn.run调用
                        mock_run.assert_called_once()
                        _, kwargs = mock_run.call_args
                        assert kwargs["log_level"] == "error"  # 实际日志级别

    def test_main_with_invalid_port(self):
        """测试使用无效的端口"""
        # 模拟uvicorn.run
        with patch("acolyte.main.uvicorn.run") as mock_run:
            # 模拟环境变量
            env_vars = {"ACOLYTE_PORT": "invalid"}
            with patch.dict(os.environ, env_vars, clear=True):
                # 模拟日志
                with patch("acolyte.main.logger") as mock_logger:
                    # 模拟int函数
                    with patch("acolyte.main.int") as mock_int:
                        # 设置模拟对象的返回值
                        mock_int.side_effect = [
                            ValueError("invalid literal for int() with base 10: 'invalid'"),
                            8000,
                        ]

                        # 执行主函数
                        main()

                        # 验证日志警告
                        mock_logger.warning.assert_called_once()

                        # 验证uvicorn.run调用
                        mock_run.assert_called_once()
                        _, kwargs = mock_run.call_args
                        assert kwargs["port"] == 8000  # 默认端口
