#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：main_graph.py
@Author ：zlh
@Date ：2026-09-05 16:47 
"""
import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.node.target_parser_node import target_parser_node
from backend.graph.node.company_planner import company_planner
from backend.graph.node.company_merge import company_merge
from backend.graph.node.company_score import company_score
from backend.graph.company_graph import get_company_graph
from backend.graph.router.router import send_company_work
from backend.graph.router.router import send_company_score


def create_graph(checkpointer):
    # 主图
    builder_main = StateGraph(LeadGraphState)

    builder_main.add_node(
        "target_profile",
        target_parser_node
    )

    builder_main.add_node(
        "company_planner",
        company_planner
    )
    # 公司搜索提取子图
    company_work = get_company_graph()

    builder_main.add_node(
        "company_work",
        company_work
    )

    builder_main.add_node(
        "company_merge",
        company_merge
    )

    builder_main.add_node(
        "company_score",
        company_score
    )

    builder_main.add_edge(
        START,
        "target_profile"
    )

    builder_main.add_edge(
        "target_profile",
        "company_planner"
    )

    builder_main.add_conditional_edges(
        "company_planner",
        send_company_work
    )

    builder_main.add_edge(
        "company_work",
        "company_merge"
    )

    builder_main.add_conditional_edges(
        "company_merge",
        send_company_score
    )

    builder_main.add_edge(
        "company_score",
        END
    )

    graph = builder_main.compile(checkpointer=checkpointer)
    return graph


async def test_graph():
    checkpointer = MemorySaver()
    graph = create_graph(checkpointer)
    user_input = "我是一名销售，主要销售牛奶大型消毒设备，需要寻找英国地区，牛奶行业的公司人员，将设备销售给他们，尽量寻找对面有联系方式的人，比如领英平台的邮箱。"
    task_id = "task001"
    config = {
        "configurable": {
            "thread_id": task_id
        }
    }
    async for event in graph.astream(
            {
                "user_input": user_input
            },
            config=config
    ): print(event)

if __name__ == "__main__":
    asyncio.run(test_graph())
