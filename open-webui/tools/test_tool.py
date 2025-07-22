"""
title: Test Tool
author: Test
description: Simple test tool
version: 1.0.0
"""

class Tools:
    def __init__(self):
        pass
    
    def hello(self, name: str = "World") -> str:
        """Say hello to someone"""
        return f"Hello, {name}!"