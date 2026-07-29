#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略流水线：强势股筛选 → 多选一辩论；飞书通知辅助。
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from agent_selection import select_core_agent_ids


def check_pipeline_token(request) -> Tuple[bool, Optional[str]]:
    token = (os.environ.get("PIPELINE_TRIGGER_TOKEN") or "").strip()
    if not token:
        return False, "服务端未配置 PIPELINE_TRIGGER_TOKEN"
    got = (request.headers.get("X-Pipeline-Token") or "").strip()
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        got = auth[7:].strip()
    if got != token:
        return False, "token 无效"
    return True, None


def execute_strategy_to_multi_debate(
    app,
    *,
    limit_time: str = "11:30",
    agent_ids: Optional[List[int]] = None,
    analysis_rounds: int = 2,
    debate_rounds: int = 1,
    override_api_key: Optional[str] = None,
) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    内部：GET strong_stocks → POST start_multi。
    返回 (True, payload) 或 (False, error_dict 或 str)
    """
    with app.test_client() as client:
        r = client.get(f"/api/strategy/strong_stocks?limit_time={limit_time}")
        if r.status_code != 200:
            try:
                err_body = r.get_json()
            except Exception:
                err_body = r.get_data(as_text=True)[:800]
            return False, {"error": "strategy_http", "status": r.status_code, "body": err_body}

        data = r.get_json()
        if not data:
            return False, {"error": "strategy_empty"}

        stocks = data.get("stocks") or []
        recommended = [s for s in stocks if isinstance(s, dict) and s.get("recommended")]
        selected_stocks = recommended or stocks[:5]
        codes = []
        for s in selected_stocks:
            c = s.get("code") if isinstance(s, dict) else None
            if c:
                c = str(c).strip()
                if c.isdigit() and len(c) == 6:
                    codes.append(c)
        if len(codes) < 2:
            return False, {
                "error": "not_enough_stocks",
                "message": f"当前强势股 {len(codes)} 只，多选一至少需要 2 只",
                "codes": codes,
            }

        resolved_ids = agent_ids
        if not resolved_ids:
            from models import SessionLocal
            from db import get_agents

            db = SessionLocal()
            try:
                agents = get_agents(db, enabled_only=True)
                resolved_ids = select_core_agent_ids(agents)
            finally:
                db.close()

        if len(resolved_ids) < 2:
            return False, {"error": "not_enough_agents", "message": "启用中的 Agent 少于 2 个"}

        body: Dict[str, Any] = {
            "codes": codes,
            "agent_ids": resolved_ids,
            "analysis_rounds": analysis_rounds,
            "debate_rounds": debate_rounds,
            "candidate_context": "\n".join([
                (
                    f"{stock.get('rank', '-')}. {stock.get('name', '')}({stock.get('code')}): "
                    f"量化评分 {stock.get('score', 'N/A')}，"
                    f"优势 {'；'.join(stock.get('score_reasons') or ['无'])}，"
                    f"风险 {'；'.join((stock.get('risk_flags') or []) + (stock.get('hard_filter_reasons') or [])) or '无'}"
                )
                for stock in selected_stocks
            ]),
        }
        if override_api_key:
            body["override_api_key"] = override_api_key

        r2 = client.post(
            "/api/ai/debate/start_multi",
            json=body,
            content_type="application/json",
        )
        out = r2.get_json()
        if r2.status_code != 200 or not (out and out.get("success")):
            return False, {"error": "start_multi_failed", "status": r2.status_code, "data": out}

        payload = {
            "job_id": (out.get("data") or {}).get("job_id"),
            "name": (out.get("data") or {}).get("name"),
            "codes": codes,
            "count": len(codes),
            "strategy": data.get("strategy"),
            "trade_dates": data.get("trade_dates"),
        }
        return True, payload


def feishu_webhook_send_text(webhook_url: str, text: str) -> None:
    if not webhook_url or not text:
        return
    try:
        requests.post(
            webhook_url,
            json={"msg_type": "text", "content": {"text": text[:20000]}},
            timeout=15,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
    except Exception as e:
        print(f"[飞书Webhook] 发送失败: {e}")


def parse_feishu_message_text(event_payload: dict) -> str:
    """从飞书消息事件中取出纯文本（尽力解析）。"""
    msg = event_payload.get("message") or {}
    raw = msg.get("content") or ""
    if isinstance(raw, dict):
        return (raw.get("text") or "").strip()
    if isinstance(raw, str):
        try:
            j = json.loads(raw)
            return (j.get("text") or "").strip()
        except Exception:
            return raw.strip()
    return ""


def feishu_should_trigger(text: str) -> bool:
    if not text:
        return False
    kw = (os.environ.get("PIPELINE_KEYWORD") or "策略辩论").strip()
    return kw in text


def handle_feishu_event_body(body: dict) -> Optional[dict]:
    """
    返回需要 JSON 响应给飞书的内容；无需响应则返回 None。
    - URL 校验：challenge 原样返回
    """
    if not body:
        return None
    if body.get("type") == "url_verification" and body.get("challenge"):
        return {"challenge": body["challenge"]}
    if "challenge" in body and len(body) == 1:
        return {"challenge": body["challenge"]}
    schema = body.get("schema")
    if schema == "2.0":
        h = body.get("header") or {}
        if h.get("event_type") == "url_verification":
            ch = (body.get("event") or {}).get("challenge") or body.get("challenge")
            if ch:
                return {"challenge": ch}
    return None


def verify_feishu_event_token(header: dict) -> bool:
    expected = (os.environ.get("FEISHU_VERIFICATION_TOKEN") or "").strip()
    if not expected:
        return True
    got = (header or {}).get("token") or (header or {}).get("verification_token")
    return got == expected


def run_pipeline_in_thread(app, kwargs: dict, webhook_url: Optional[str] = None) -> None:
    def _run():
        ok, result = execute_strategy_to_multi_debate(app, **kwargs)
        if webhook_url:
            if ok and isinstance(result, dict):
                jid = result.get("job_id")
                n = result.get("count")
                feishu_webhook_send_text(
                    webhook_url,
                    f"策略流水线已启动\n任务 job_id: {jid}\n股票数: {n}\n查询: GET /api/ai/debate/status/{jid}",
                )
            else:
                feishu_webhook_send_text(webhook_url, f"策略流水线失败\n{result}")

    threading.Thread(target=_run, daemon=True).start()
