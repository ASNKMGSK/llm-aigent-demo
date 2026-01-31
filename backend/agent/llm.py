"""
agent/llm.py - LangChain 기반 LLM 호출 / 스트리밍
"""
import json
import time
import inspect
from typing import Optional, List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.messages.base import BaseMessage

from core.utils import safe_str, json_sanitize, normalize_model_name
from core.memory import memory_messages
import state as st


def _lc_from_memory(username: str) -> List[BaseMessage]:
    msgs: List[BaseMessage] = []
    hist = memory_messages(username)
    for m in hist:
        role = safe_str(m.get("role", "")).strip().lower()
        content = safe_str(m.get("content", ""))
        if not content:
            continue
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
    return msgs


def _tool_context_block(tool_results: Dict[str, Any]) -> str:
    try:
        safe_obj = json_sanitize(tool_results)
        s = json.dumps(safe_obj, ensure_ascii=False, indent=2)
    except Exception:
        s = safe_str(tool_results)
    return (
        "아래는 내부 분석/도구 결과(JSON)입니다.\n\n"
        "**활용 원칙**:\n"
        "1. 도구 결과가 질문과 관련 있으면 우선적으로 활용합니다.\n"
        "2. RAG 검색 결과가 질문과 무관하거나 없으면 일반 지식으로 답변합니다.\n"
        "3. 수치/라벨은 JSON 값 그대로 사용하고, 추측/단정은 하지 않습니다.\n\n"
        f"{s}"
    )


def build_langchain_messages(system_prompt: str, username: str, user_text: str, tool_results: Dict[str, Any]) -> List[BaseMessage]:
    msgs: List[BaseMessage] = []
    msgs.append(SystemMessage(content=safe_str(system_prompt)))
    msgs.extend(_lc_from_memory(username))

    context = _tool_context_block(tool_results) if isinstance(tool_results, dict) and len(tool_results) else ""
    if context:
        final_user = f"{safe_str(user_text)}\n\n[INTERNAL_TOOL_RESULTS]\n{context}"
    else:
        final_user = safe_str(user_text)

    msgs.append(HumanMessage(content=final_user))
    return msgs


def get_llm(
    model: str,
    api_key: str,
    max_tokens: int,
    streaming: bool,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    timeout_ms: Optional[int] = None,
    max_retries: Optional[int] = None,
) -> ChatOpenAI:
    model_final = normalize_model_name(model)
    is_gpt5 = model_final.lower().startswith("gpt-5")

    kwargs: Dict[str, Any] = {
        "model": model_final,
        "openai_api_key": api_key,
        "streaming": bool(streaming),
    }

    try:
        if max_tokens and int(max_tokens) > 0:
            kwargs["max_tokens"] = int(max_tokens)
    except Exception:
        pass

    model_kwargs: Dict[str, Any] = {}

    if (not is_gpt5) and (temperature is not None):
        try:
            kwargs["temperature"] = float(temperature)
        except Exception:
            pass

    if top_p is not None:
        try:
            model_kwargs["top_p"] = float(top_p)
        except Exception:
            pass

    if presence_penalty is not None:
        try:
            model_kwargs["presence_penalty"] = float(presence_penalty)
        except Exception:
            pass

    if frequency_penalty is not None:
        try:
            model_kwargs["frequency_penalty"] = float(frequency_penalty)
        except Exception:
            pass

    if seed is not None and safe_str(seed).strip() != "":
        try:
            model_kwargs["seed"] = int(seed)
        except Exception:
            pass

    if model_kwargs:
        kwargs["model_kwargs"] = model_kwargs

    try:
        sig = inspect.signature(ChatOpenAI.__init__)
        allowed = set(sig.parameters.keys())

        if timeout_ms is not None:
            try:
                sec = float(timeout_ms) / 1000.0
                if "timeout" in allowed:
                    kwargs["timeout"] = sec
                elif "request_timeout" in allowed:
                    kwargs["request_timeout"] = sec
            except Exception:
                pass

        if max_retries is not None:
            try:
                mr = int(max_retries)
                if "max_retries" in allowed:
                    kwargs["max_retries"] = mr
            except Exception:
                pass
    except Exception:
        pass

    return ChatOpenAI(**kwargs)


def invoke_with_retry(llm: ChatOpenAI, messages: List[BaseMessage], max_retries: int = 3) -> str:
    last_exception = None
    for attempt in range(max_retries):
        try:
            st.logger.info("LANGCHAIN_INVOKE attempt=%d model=%s", attempt + 1, getattr(llm, "model_name", ""))
            out = llm.invoke(messages)
            txt = safe_str(getattr(out, "content", "")).strip()
            return txt
        except Exception as e:
            last_exception = e
            st.logger.warning("LANGCHAIN_INVOKE_FAIL attempt=%d err=%s", attempt + 1, safe_str(e))
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise last_exception
    return ""


def chunk_text(chunk: Any) -> str:
    try:
        c = getattr(chunk, "content", "")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts = []
            for x in c:
                if isinstance(x, str):
                    parts.append(x)
                elif isinstance(x, dict):
                    parts.append(safe_str(x.get("text", "")))
                else:
                    parts.append(safe_str(x))
            return "".join([p for p in parts if p])
        return safe_str(c)
    except Exception:
        return ""


def pick_api_key(req_api_key: str) -> str:
    api_key = safe_str(req_api_key).strip()
    if api_key:
        return api_key

    import os
    api_key = safe_str(st.OPENAI_API_KEY).strip()
    if api_key:
        return api_key

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return api_key
