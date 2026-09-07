#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：research_agent 
@File ：search_service.py
@Author ：zlh
@Date ：2026-07-20 15:33 
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
from typing import Optional

current_dir = Path(__file__).parent
env_path = current_dir/'..'/'config'/ '.env'
load_dotenv(env_path)

_init_lock = asyncio.Lock()

client = {}
tools = {}



async def init_tavily_client():
    tavily_api_key = os.environ.get("tavily_api_key")
    print(tavily_api_key)
    async with _init_lock:
        if "search" not in tools:
            client["tavily"] = MultiServerMCPClient(
                {
                    "tavily": {
                        "transport": "http",
                        "url": (
                            "https://mcp.tavily.com/mcp/"
                            f"?tavilyApiKey={tavily_api_key}"
                        )
                    }
                }
            )
            print("正在连接 Tavily MCP Server...")
            all_tools = await client["tavily"].get_tools()
            search_tool = None
            for tool in all_tools:
                if "search" in tool.name.lower():
                    search_tool = tool
                    break
            if search_tool is None:
                raise RuntimeError("没有找到搜索工具")
            tools["search"] = search_tool
        else:
            print("服务器已连接")


async def tavily_search(query):
    if "search" not in tools:
        await init_tavily_client()
    print(f"准备调用工具: {tools["search"].name}")
    print(f"搜索内容: {query}")
    result = await tools["search"].ainvoke(
        {
            "query": query
        }
    )
    print("\n========== 搜索完成 ==========\n")
    print(result)
    result = result[0]['text']
    # raw_response 可能是 list，也可能是 dict，这里做兼容处理
    if isinstance(result, list) and len(result) > 0:
        # 标准 MCP 格式: [{"type": "text", "text": "..."}]
        first_item = result[0]
        if isinstance(first_item, dict) and "text" in first_item:
            text_content = first_item["text"]
            # 3. 关键步骤：将内部的 JSON 字符串解析为字典
            if isinstance(text_content, str):
                parsed_data = json.loads(text_content)
                return parsed_data  # 这里就是包含 "results" 的字典了
    elif isinstance(result, dict):
        # 有些工具直接返回 dict，直接返回
        return result
    else:
        # 如果返回的是纯字符串，尝试直接解析
        if isinstance(result, str):
            result = json.loads(result)
            return result
    return result


if __name__ == "__main__":
    asyncio.run(
        tavily_search("喝牛奶的好处")
    )
