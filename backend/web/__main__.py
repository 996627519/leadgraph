#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：__main__.py
@Author ：zlh
@Date ：2026-09-14 10:33 
"""
import os
import uvicorn
from backend.web.app import create_app

# 主入口
if __name__ == '__main__':
    uvicorn.run(create_app(), host='127.0.0.1', port=int(os.getenv('LEADGRAPH_PORT', '8080')),
                workers=1, log_level='warning')
