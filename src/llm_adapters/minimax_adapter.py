"""
MiniMax LLM适配器

支持MiniMax API（Anthropic兼容模式）
"""

import os
import asyncio
from typing import List, Dict, Any, Optional

import anthropic

from .base_adapter import BaseLLMAdapter, LLMResponse


class MiniMaxAdapter(BaseLLMAdapter):
    """MiniMax LLM适配器 (Anthropic兼容模式)

    API格式:
    - Base URL: https://api.minimaxi.com/anthropic
    - 模型: MiniMax-M2.7
    - 协议: Anthropic SDK兼容
    """

    def __init__(
        self,
        api_key: str,
        model: str = "MiniMax-M2.7",
        base_url: str = "https://api.minimaxi.com/anthropic",
        timeout: int = 30,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens
        )

        os.environ["ANTHROPIC_BASE_URL"] = base_url
        os.environ["ANTHROPIC_API_KEY"] = api_key

        # Anthropic SDK的timeout参数直接使用秒数
        self.client = anthropic.Anthropic(
            timeout=timeout
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求（M2.7支持thinking和tool use）"""

        # 提取system消息
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        # 构建Anthropic格式
        anthropic_messages = []
        for msg in filtered_messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": content}]
                })
            elif isinstance(content, list):
                # 处理复杂内容格式
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": content
                })

        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "system": system_msg,
            "messages": anthropic_messages,
        }

        # 添加tools（MCP格式）
        if tools:
            params["tools"] = tools

        # 重试逻辑（带超时保护）
        last_error = None
        timeout = self.timeout

        for attempt in range(self.max_retries):
            try:
                # messages.create是同步的，需要在线程池中运行
                # 使用asyncio.wait_for添加超时保护
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.client.messages.create(**params)
                    ),
                    timeout=timeout
                )
                return self._parse_response(response)
            except asyncio.TimeoutError:
                last_error = Exception(f"MiniMax API timeout after {timeout}s")
                timeout = min(timeout * 1.5, 60)  # 递增超时，最长60秒
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise last_error or Exception("MiniMax API call failed")

    def _parse_response(self, response) -> LLMResponse:
        """解析MiniMax M2.7响应"""
        content_blocks = response.content

        thought = None
        text_content = []
        tool_calls = None

        for block in content_blocks:
            if block.type == "thinking":
                thought = block.thinking
            elif block.type == "text":
                text_content.append(block.text)
            elif block.type == "tool_use":
                tool_calls = tool_calls or []
                tool_calls.append({
                    "name": block.name,
                    "arguments": block.input
                })

        return LLMResponse(
            content="\n".join(text_content),
            thought=thought,
            tool_calls=tool_calls,
            raw_response=response
        )

    async def close(self):
        """关闭连接（Anthropic SDK不需要显式关闭）"""
        pass
