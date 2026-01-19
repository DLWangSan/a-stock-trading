#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI服务调用模块"""

import requests
import json
import os
from typing import Dict, Optional

class AIService:
    """统一的AI服务调用类"""
    
    @staticmethod
    def call_openai(api_key: str, model: str, prompt: str) -> str:
        """调用OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    @staticmethod
    def call_deepseek(api_key: str, model: str, prompt: str) -> str:
        """调用DeepSeek API"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    @staticmethod
    def call_qwen(api_key: str, model: str, prompt: str) -> str:
        """调用通义千问API（兼容OpenAI模式）"""
        base_url = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    @staticmethod
    def call_gemini(api_key: str, model: str, prompt: str) -> str:
        """调用Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    
    @staticmethod
    def call_siliconflow(api_key: str, model: str, prompt: str) -> str:
        """调用硅基流动API"""
        base_url = os.getenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn").rstrip("/")
        url = f"{base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    @classmethod
    def call_agent(cls, provider: str, api_key: str, model: str, prompt: str) -> str:
        """统一调用接口"""
        provider_map = {
            "openai": cls.call_openai,
            "deepseek": cls.call_deepseek,
            "qwen": cls.call_qwen,
            "gemini": cls.call_gemini,
            "siliconflow": cls.call_siliconflow
        }
        
        if provider not in provider_map:
            raise ValueError(f"不支持的AI提供商: {provider}")
        
        return provider_map[provider](api_key, model, prompt)
    
    @staticmethod
    def get_models(provider: str, api_key: str) -> list:
        """获取指定提供商的可用模型列表"""
        if provider == "openai":
            # OpenAI需要调用models API
            url = "https://api.openai.com/v1/models"
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                # 过滤出chat模型
                models = [m["id"] for m in result.get("data", []) 
                         if "gpt" in m["id"].lower() and ("chat" in m["id"].lower() or "turbo" in m["id"].lower())]
                return sorted(models)
            except:
                # 如果API调用失败，返回常用模型列表
                return ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
        elif provider == "deepseek":
            # DeepSeek兼容OpenAI模型列表接口
            url = "https://api.deepseek.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                models = [m["id"] for m in result.get("data", [])]
                return sorted(models) if models else ["deepseek-chat", "deepseek-coder"]
            except:
                return ["deepseek-chat", "deepseek-coder"]
        elif provider == "qwen":
            # 通义千问兼容OpenAI模型列表接口
            base_url = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                models = [m["id"] for m in result.get("data", [])]
                return sorted(models) if models else ["qwen-turbo", "qwen-plus", "qwen-max"]
            except:
                return ["qwen-turbo", "qwen-plus", "qwen-max"]
        elif provider == "gemini":
            # Gemini模型列表接口
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                result = response.json()
                models = [m.get("name", "") for m in result.get("models", []) if m.get("name")]
                # Gemini返回形如 "models/gemini-1.5-pro"，需要去掉前缀
                models = [m.replace("models/", "") for m in models]
                return sorted(models) if models else ["gemini-pro", "gemini-pro-vision"]
            except:
                return ["gemini-pro", "gemini-pro-vision"]
        elif provider == "siliconflow":
            # 硅基流动兼容OpenAI模型列表接口
            base_url = os.getenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn").rstrip("/")
            url = f"{base_url}/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                models = [m["id"] for m in result.get("data", [])]
                if models:
                    return sorted(models)
            except:
                pass
            # 兜底常用模型列表
            return [
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2.5-32B-Instruct",
                "Qwen/Qwen2.5-14B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "meta-llama/Llama-3.1-70B-Instruct",
                "meta-llama/Llama-3.1-8B-Instruct",
                "deepseek-ai/DeepSeek-V2.5",
                "deepseek-ai/DeepSeek-V2",
            ]
        else:
            return []
    
    @staticmethod
    def test_connection(provider: str, api_key: str, model: str = None) -> dict:
        """测试API连接"""
        try:
            # 如果没有指定模型，使用默认模型
            if not model:
                default_models = {
                    "openai": "gpt-3.5-turbo",
                    "deepseek": "deepseek-chat",
                    "qwen": "qwen-turbo",
                    "gemini": "gemini-pro",
                    "siliconflow": "Qwen/Qwen2.5-7B-Instruct"
                }
                model = default_models.get(provider, "gpt-3.5-turbo")
            
            # 使用简单的测试prompt
            test_prompt = "Hello, please respond with 'OK' to confirm the connection."
            result = AIService.call_agent(provider, api_key, model, test_prompt)
            
            return {
                "success": True,
                "message": "连接成功",
                "response": result[:100]  # 只返回前100个字符
            }
        except requests.HTTPError as e:
            response_text = ""
            try:
                response_text = e.response.text if e.response is not None else ""
            except Exception:
                response_text = ""
            detail = f"{str(e)}"
            if response_text:
                detail = f"{detail} | {response_text[:200]}"
            return {
                "success": False,
                "message": f"连接失败: {detail}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}"
            }

