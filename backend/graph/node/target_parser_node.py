#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：target_parser_node.py
@Author ：zlh
@Date ：2026-09-04 19:52 
"""
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.prompts.graph_prompts import target_parser_prompts
from backend.graph.llm.deepseek import get_structured_deepseek
from backend.graph.states.target_profile import TargetProfile

def target_parser_node(state: LeadGraphState):
    print("进入target_parser_node")
    user_input = state['user_input']
    structured_llm = get_structured_deepseek(TargetProfile)
    message =[
        SystemMessage(
            content=target_parser_prompts
        ),
        HumanMessage(
            content=f"""
        用户的要求如下:
        {user_input}
        """
        )
    ]
    result = structured_llm.invoke(message)
    print("===============================target_parser_node处理完毕===============================")
    print(result)
    return {
        "target_parser_content": result
    }



