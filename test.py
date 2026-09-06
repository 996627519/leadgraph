#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test.py
@Author ：zlh
@Date ：2026-09-05 15:16 
"""
from langgraph.graph import StateGraph, START, END
from backend.graph.states.lead_graph_state import LeadGraphState
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(LeadGraphState)

def nodeA(state: LeadGraphState):
    print("进入A")

def nodeB(state: LeadGraphState):
    task = state["task"]
    print(f"进入B,task:{task}")

def nodeC(state: LeadGraphState):
    print("进入C")
    return {
        "test": ['test']
    }

def send_B(state: LeadGraphState):
    return[
        Send("nodeB",{"task": i}) for i in range(1,5)
    ]

builder.add_node(
    "nodeA",
    nodeA
)
builder.add_node(
    "nodeB",
    nodeB
)
builder.add_node(
    "nodeC",
    nodeC
)

builder.add_edge(
    START,
    "nodeA"
)
builder.add_conditional_edges(
    "nodeA",
    send_B
)
builder.add_edge(
    "nodeB",
    "nodeC"
)
builder.add_edge(
    "nodeC",
    END
)
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
task_id = "task001"
config = {
    "configurable": {
        "thread_id": task_id
    }
}
for event in graph.stream(
        {},
        config=config
): print(event)