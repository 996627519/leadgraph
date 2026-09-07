#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_score.py
@Author ：zlh
@Date ：2026-09-07 13:24 
"""
from backend.graph.states.company_score_state import CompanyScore, CompanyScoreState
from backend.graph.llm.deepseek import get_structured_deepseek
from backend.graph.prompts.graph_prompts import company_score_prompt
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.utils.company_utils import calculate_company_score, get_company_recommendation
from backend.graph.error.error_handle import invoke_structured_with_retry


def company_score(state: CompanyScoreState):
    print("进入company_score")
    company = state["company"]
    target_profile = state["target_profile"]
    structured_deepseek = get_structured_deepseek(CompanyScore)
    message = [
        SystemMessage(
            content=company_score_prompt
        ),
        HumanMessage(
            content=f"""
            target_profile:
            {target_profile}
            ---
            company:
            {company}
            """
        )
    ]
    try:
        response = structured_deepseek.invoke(message)["parsed"]
    except Exception as e:
        # 失败重试
        response = invoke_structured_with_retry(structured_deepseek, CompanyScore, message)
    if response is None:
        print(f"[company_score] scoring failed: "f"{company.name}")
        return {"company_score": []}
    total_score = calculate_company_score(response)
    recommendation = get_company_recommendation(total_score, response.hard_constraint_pass, response.confidence)
    result = CompanyScore(
        company=company,
        industry_fit=response.industry_fit,
        company_type_fit=response.company_type_fit,
        geography_fit=response.geography_fit,
        capability_fit=response.capability_fit,
        company_size_fit=response.company_size_fit,
        hard_constraint_pass=response.hard_constraint_pass,
        failed_hard_constraints=response.failed_hard_constraints,
        missing_information=response.missing_information,
        total_score=total_score,
        confidence=response.confidence,
        recommendation=recommendation,
        summary=response.summary
    )
    print("===============================company_score处理完毕===============================")
    print(result)
    return {
        "company_score": [result]
    }