#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：research_agent 
@File ：search_service.py
@Author ：zlh
@Date ：2026-07-20 15:33 
"""
import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path

current_dir = Path(__file__).parent
env_path = current_dir/'..'/'config'/ '.env'
load_dotenv(env_path)

client = {}
tools = {}

async def init_tavily_client():
    tavily_api_key = os.environ.get("tavily_api_key")
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
    return result[0]['text']


if __name__ == "__main__":
    asyncio.run(tavily_search("牛奶的功效"))