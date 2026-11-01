"""The language-model client and the agent loop (Anthropic SDK, our own loop).

`run_agent` is the whole agentic mechanism, in plain code so it can be read and graded:

    loop (at most max_llm_rounds):
        call the model with the agent's system prompt and tools
        if it asked for tools:   run each through the tool guardrail (or a sub-agent), return
                                 the results with their evidence references, and loop
        if the API paused a server tool (web search): send the turn back as-is, and loop
        otherwise:               the text is the agent's answer
    out of rounds: one last call with tools disabled, so the agent answers with what it has

The client is behind a tiny interface (`create(**kwargs) -> dict`), so the tests run the same
loop with a scripted fake model and no API key.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from agents.guardrails.tool_guard import ToolGuard, TurnState


class LLMClient(Protocol):
    def create(self, **kwargs) -> dict: ...


class AnthropicLLM:
    """Thin wrapper: returns plain dicts, so the loop does not depend on SDK types."""

    def __init__(self, api_key: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
                                          max_retries=3, timeout=180)

    def create(self, **kwargs) -> dict:
        r = self.client.messages.create(**kwargs)
        return {"content": [b.model_dump(exclude_none=True) for b in r.content],
                "stop_reason": r.stop_reason,
                "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}}


@dataclass
class AgentSpec:
    name: str                       # e.g. "investigator"
    title_he: str                   # shown in the UI
    system: str
    prompt_version: str
    tools: list[str]                # names in the tool registry
    delegates: dict = field(default_factory=dict)   # tool name -> (schema, callable(args, state))
    model: str | None = None


@dataclass
class AgentResult:
    agent: str
    text: str
    rounds: int
    tool_calls: int
    stopped: str                    # end_turn | max_rounds | error
    refs: list[str] = field(default_factory=list)


def _usage(state: TurnState, resp: dict):
    u = resp.get("usage") or {}
    state.usage["input_tokens"] += int(u.get("input_tokens", 0))
    state.usage["output_tokens"] += int(u.get("output_tokens", 0))
    state.usage["llm_calls"] += 1


def _register_web(content: list[dict], agent: str, state: TurnState) -> list[dict]:
    """Web search runs on Anthropic's side. Log the searches in the trace, and register each
    cited web source as external evidence, so web claims carry a reference like local ones."""
    out = []
    by_url: dict[str, str] = {}
    for b in content:
        t = b.get("type")
        if t == "server_tool_use":
            state.emit("tool_call", agent, tool=b.get("name", "web_search"), args=b.get("input", {}),
                       server=True)
        elif t == "web_search_tool_result":
            res = b.get("content")
            n = len(res) if isinstance(res, list) else 0
            state.emit("tool_result", agent, tool="web_search", status="ok" if n else "no_results",
                       results=n, server=True)
        if t == "text" and b.get("citations"):
            refs = []
            for c in b["citations"]:
                url = c.get("url")
                if not url:
                    continue
                if url not in by_url:
                    rec = state.store.register(
                        "web_search", agent, {"url": url},
                        {"tool": "web_search", "status": "ok", "title": c.get("title"), "url": url,
                         "cited_text": c.get("cited_text"), "evidence_id": f"web:{url}"},
                        external=True)
                    by_url[url] = rec.ref
                    state.emit("tool_result", agent, tool="web_source", ref=rec.ref, status="ok",
                               evidence_id=f"web:{url}")
                refs.append(by_url[url])
            b = {"type": "text", "text": b.get("text", "").rstrip() + f" [{', '.join(dict.fromkeys(refs))}]"
                 if refs else b.get("text", "")}
        out.append(b)
    return out


def _text_of(content: list[dict]) -> str:
    return "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()


def run_agent(spec: AgentSpec, task: str, *, llm: LLMClient, guard: ToolGuard, state: TurnState,
              config, history: list[dict] | None = None) -> AgentResult:
    registry = guard.registry
    tools = [registry[n].schema for n in spec.tools if n in registry]
    tools += [schema for schema, _ in spec.delegates.values()]
    allowed = set(spec.tools)
    messages = list(history or []) + [{"role": "user", "content": task}]
    model = spec.model or config.agent_model
    state.emit("agent_start", spec.name, title=spec.title_he, prompt_version=spec.prompt_version,
               model=model, tools=[t.get("name") for t in tools])
    t0, calls, final_parts = time.time(), 0, []

    def call(**extra) -> dict:
        resp = llm.create(model=model, system=spec.system, max_tokens=config.max_tokens,
                          messages=messages, tools=tools, **extra)
        _usage(state, resp)
        return resp

    for rnd in range(1, config.max_llm_rounds_per_agent + 1):
        try:
            resp = call()
        except Exception as e:
            state.emit("error", spec.name, error=f"{type(e).__name__}: {e}")
            raise
        content = _register_web(resp.get("content", []), spec.name, state)
        messages.append({"role": "assistant", "content": content})
        stop = resp.get("stop_reason")
        if stop == "pause_turn":
            final_parts.append(_text_of(content))
            continue
        uses = [b for b in content if b.get("type") == "tool_use"]
        if stop == "tool_use" and uses:
            results = []
            for b in uses:
                name, args = b.get("name"), b.get("input") or {}
                if name in spec.delegates:
                    state.emit("delegate", spec.name, to=name, args=args)
                    try:
                        payload = spec.delegates[name][1](args, state)
                    except Exception as e:
                        payload = {"status": "tool_failure", "status_reason": f"{type(e).__name__}: {e}"}
                else:
                    payload, _ = guard.execute(spec.name, allowed, name, args, state)
                    calls += 1
                results.append({"type": "tool_result", "tool_use_id": b["id"],
                                "content": json.dumps(payload, ensure_ascii=False, default=str)})
            messages.append({"role": "user", "content": results})
            final_parts = []
            continue
        final_parts.append(_text_of(content))
        text = "\n\n".join(p for p in final_parts if p).strip()
        state.emit("agent_end", spec.name, rounds=rnd, tool_calls=calls, ms=int(1000 * (time.time() - t0)))
        return AgentResult(spec.name, text, rnd, calls, "end_turn")

    # out of rounds: answer with the evidence gathered so far, tools disabled
    state.emit("guardrail", spec.name, guard="max_rounds",
               reason=f"{config.max_llm_rounds_per_agent} model rounds reached; answering without more tools")
    messages.append({"role": "user", "content": "You have reached the step limit. Answer now with "
                     "the evidence you already have, and say what is still missing."})
    resp = call(tool_choice={"type": "none"})
    content = _register_web(resp.get("content", []), spec.name, state)
    text = _text_of(content)
    state.emit("agent_end", spec.name, rounds=config.max_llm_rounds_per_agent + 1, tool_calls=calls,
               ms=int(1000 * (time.time() - t0)))
    return AgentResult(spec.name, text, config.max_llm_rounds_per_agent + 1, calls, "max_rounds")


def ask_once(llm: LLMClient, *, model: str, system: str, user: str, max_tokens: int,
             state: TurnState, tool: dict | None = None) -> dict:
    """One model call without the loop: the router (forced tool) and the reviser (plain text)."""
    kw = {"model": model, "system": system, "max_tokens": max_tokens,
          "messages": [{"role": "user", "content": user}]}
    if tool:
        kw.update(tools=[tool], tool_choice={"type": "tool", "name": tool["name"]})
    resp = llm.create(**kw)
    _usage(state, resp)
    if tool:
        for b in resp.get("content", []):
            if b.get("type") == "tool_use":
                return b.get("input") or {}
        return {}
    return {"text": _text_of(resp.get("content", []))}


def make_delegate(name: str, description: str, run: Callable[[str, str | None, TurnState], AgentResult]):
    """Expose an agent to another agent as a tool ("agent as a tool")."""
    schema = {"name": name, "description": description,
              "input_schema": {"type": "object", "properties": {
                  "question": {"type": "string", "description": "A precise question for the agent."},
                  "city": {"type": "string"}}, "required": ["question"]}}

    def handler(args: dict, state: TurnState) -> dict:
        res = run(args.get("question", ""), args.get("city"), state)
        return {"status": "ok" if res.text else "tool_failure", "agent": res.agent,
                "findings": res.text,
                "note": "The findings cite evidence references [E#] from the shared evidence store; "
                        "you may cite the same references."}

    return schema, handler
