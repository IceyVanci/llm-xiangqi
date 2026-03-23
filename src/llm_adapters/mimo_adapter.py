"""
MiMo LLM适配器

支持小米MiMo系列API（OpenAI兼容）
"""

import json
import asyncio
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

from .base_adapter import BaseLLMAdapter, LLMResponse


class MiMoAdapter(BaseLLMAdapter):
    """MiMo LLM适配器

    API格式:
    - Base URL: https://api.xiaomimimo.com/v1
    - 模型: mimo-v2-pro, mimo-v2-omni, mimo-v2-flash
    - 协议: OpenAI兼容
    """

    def __init__(
        self,
        api_key: str,
        model: str = "mimo-v2-pro",
        base_url: str = "https://api.xiaomimimo.com/v1",
        timeout: int = 60,
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

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""

        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")

        # 重试逻辑（带超时保护）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(**params)
                return self._parse_response(response)
            except asyncio.TimeoutError:
                last_error = Exception(f"MiMo API timeout after {self.timeout}s")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise last_error or Exception("MiMo API call failed")

    def _parse_response(self, response) -> LLMResponse:
        """解析MiMo响应"""
        choice = response.choices[0]

        # 提取tool_calls
        tool_calls = None
        if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
            tool_calls = []
            for tc in (choice.message.tool_calls or []):
                try:
                    args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "name": tc.function.name,
                    "arguments": args
                })

        # MiMo可能返回 reasoning_content (思考过程)
        thought = None
        if hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
            thought = choice.message.reasoning_content

        return LLMResponse(
            content=choice.message.content or "",
            thought=thought,
            tool_calls=tool_calls,
            raw_response=response
        )

    async def close(self):
        """关闭连接"""
        await self.client.close()
