"""Local dynamic workflow agent with deterministic clinical guardrails."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core import curated, db, graph, guardian, llm, repo, vision, voice
from core.config import REASONING_EFFORT_HIGH, REASONING_EFFORT_LOW

MAX_STEPS = 8

ORCHESTRATOR_SYSTEM = """You are Confide's clinical workflow orchestrator. You do not make
clinical decisions or invent facts: you call tools. Tools named run_guardian,
reconcile_medication, and sweep_forgotten_orders execute deterministic curated
rules; report their outputs verbatim.

Choose tools from the input kind and content. A clinical round normally needs
extract_note_and_facts, ingest_facts, run_guardian, suggest_billing_codes,
draft_handoff, and draft_patient_summary. A document prescription normally needs
extraction, medication reconciliation, ingestion, and Guardian review. A short
correction needs only extraction and ingestion. Call only what the input needs,
then stop with a one-line summary. Never request or supply patient identifiers."""


@dataclass
class ToolContext:
    patient_id: int
    encounter_id: int | None
    source_kind: str
    language: str = "en"
    new_nodes: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    trace: list[dict] = field(default_factory=list)
    input_text: str = ""
    last_facts: list[dict] = field(default_factory=list)


def source_kind_for(input_kind: str, text: str) -> str:
    if input_kind in ("image", "document"):
        return "prescription"
    low = (text or "").strip().lower()
    if input_kind == "text" and any(low.startswith(word) for word in ("cancel ", "stop ", "remove ", "correct ")):
        return "correction"
    return "round"


def prepare_input(input_kind: str, *, text: str | None = None,
                  audio_path: str | None = None, image_path: str | None = None) -> tuple[str, str]:
    if input_kind == "speech":
        if (text or "").strip():
            return text.strip(), "speech"
        if not audio_path:
            raise ValueError("text or audio_path is required for speech input")
        transcript, _language = voice.transcribe(audio_path)
        return transcript, "speech"
    if input_kind in ("image", "document"):
        if not image_path:
            raise ValueError("image_path is required for image input")
        return vision.ocr(image_path), "document"
    if input_kind == "text":
        if not (text or "").strip():
            raise ValueError("text is required for text input")
        return text.strip(), "text"
    raise ValueError(f"unsupported input_kind: {input_kind}")


def extract_note_and_facts(ctx: ToolContext) -> dict:
    note, facts = graph.structure_and_extract(ctx.input_text)
    ctx.artifacts["note"] = note
    ctx.last_facts = facts
    return {"note": note, "facts": facts}


def _correction_targets(ctx: ToolContext, fact: dict) -> list[dict]:
    if ctx.source_kind != "correction":
        return []
    detail = f"{fact.get('label', '')} {fact.get('detail', '')}".lower()
    if fact.get("polarity") != "denied" and not any(word in detail for word in ("cancel", "stop", "remove")):
        return []
    label = str(fact.get("label") or "").lower().replace("cancel", "").strip()
    candidates = []
    for node in graph.nodes_for(ctx.patient_id, active_only=True):
        if node["ntype"] not in ("lab_order", "procedure", "medication"):
            continue
        if node.get("source_kind") == "correction":
            continue
        node_label = (node.get("label") or "").lower()
        if label and (label in node_label or node_label in label):
            candidates.append(node)
    return candidates


def ingest_facts(ctx: ToolContext, facts: list[dict] | None = None) -> dict:
    facts = facts if facts is not None else ctx.last_facts
    new_nodes = graph.ingest_facts(ctx.patient_id, facts or [], ctx.source_kind, ctx.encounter_id)
    superseded_ids = []
    for fact, new_node in zip(facts or [], new_nodes):
        for target in _correction_targets(ctx, fact):
            graph.supersede_node(target["id"])
            graph.add_edge(ctx.patient_id, new_node["id"], target["id"], "relates_to", "correction supersedes prior order")
            superseded_ids.append(target["id"])
    ctx.new_nodes.extend(new_nodes)
    return {"new_nodes": new_nodes, "superseded_node_ids": superseded_ids}


def run_guardian(ctx: ToolContext) -> dict:
    alerts = guardian.review_new_nodes(ctx.patient_id, ctx.new_nodes, ctx.encounter_id)
    ctx.alerts.extend(alerts)
    return {"alerts": alerts}


def reconcile_medication(ctx: ToolContext, drug: str) -> dict:
    return guardian.assess_medication(ctx.patient_id, drug)


def suggest_billing_codes(ctx: ToolContext) -> dict:
    note = ctx.artifacts.get("note") or {}
    prompt = f"""From this documented note and patient context, propose billing codes as JSON.
Return {{"codes":[{{"system":"ICD-10"|"CPT","code":"...","evidence":"verbatim note quote"}}]}}.
Use a verbatim note quote for every item. Do not add diagnoses not documented.

NOTE: {json.dumps(note, ensure_ascii=False)}
CONTEXT: {graph.context_text(ctx.patient_id)}"""
    data = llm.ask_json(prompt, system="Extract coding candidates only; code validates every result.",
                        effort=REASONING_EFFORT_LOW)
    proposed = data.get("codes", []) if isinstance(data, dict) else []
    codes = []
    rejected = []
    for item in proposed:
        details = curated.code_details(str(item.get("system") or ""), str(item.get("code") or ""))
        if not details:
            rejected.append({
                "system": item.get("system"), "code": item.get("code"),
                "reason": "not in curated tables",
            })
            continue
        codes.append({**details, "evidence": str(item.get("evidence") or ""), "validated": True})
    ctx.artifacts["codes"] = codes
    return {"codes": codes, "rejected": rejected}


def draft_handoff(ctx: ToolContext) -> dict:
    active_alerts = guardian.list_alerts(ctx.patient_id, status="active")
    data = llm.ask_json(
        "Write a concise SBAR draft as JSON with priority_note, situation, background, assessment, recommendation.\n"
        f"Recorded facts:\n{graph.context_text(ctx.patient_id)}\nAlerts: {json.dumps(active_alerts, ensure_ascii=False)}",
        system="Draft from recorded facts only. Do not invent.", effort=REASONING_EFFORT_LOW,
    )
    handoff = {key: data.get(key) for key in ("priority_note", "situation", "background", "assessment", "recommendation")}
    ctx.artifacts["handoff"] = handoff
    return {"sbar": handoff}


def draft_patient_summary(ctx: ToolContext, language: str | None = None) -> dict:
    language = language or ctx.language
    summary = llm.ask(
        f"Recorded care:\n{graph.context_text(ctx.patient_id)}\n\nDraft a 4-6 sentence patient summary in language '{language}'.",
        system="Use only recorded facts, plain language, and no new medical advice.",
        effort=REASONING_EFFORT_LOW,
    )
    ctx.artifacts["patient_summary"] = summary
    return {"summary": summary, "language": language}


def sweep_forgotten_orders(ctx: ToolContext) -> dict:
    alerts = guardian.sweep_forgotten_orders(ctx.patient_id)
    ctx.alerts.extend(alerts)
    return {"alerts": alerts}


TOOL_REGISTRY: dict[str, Callable[..., dict]] = {
    "extract_note_and_facts": extract_note_and_facts,
    "ingest_facts": ingest_facts,
    "run_guardian": run_guardian,
    "reconcile_medication": reconcile_medication,
    "suggest_billing_codes": suggest_billing_codes,
    "draft_handoff": draft_handoff,
    "draft_patient_summary": draft_patient_summary,
    "sweep_forgotten_orders": sweep_forgotten_orders,
}


def _schema(name: str, description: str, properties: dict | None = None,
            required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
    }}


TOOL_SCHEMAS = [
    _schema("extract_note_and_facts", "Extract a structured note and stated facts from the bound input."),
    _schema("ingest_facts", "Persist extracted observations for the bound patient. Patient ids are server-owned."),
    _schema("run_guardian", "Deterministically check newly persisted facts. Trust its clinical output verbatim."),
    _schema("reconcile_medication", "Deterministically check a drug against active allergies and medications. Trust its output.",
            {"drug": {"type": "string", "description": "Drug name as written on the source"}}, ["drug"]),
    _schema("suggest_billing_codes", "Draft evidence-backed codes; curated code validates every candidate."),
    _schema("draft_handoff", "Draft an SBAR handoff from recorded facts; does not persist it."),
    _schema("draft_patient_summary", "Draft a patient-facing summary; does not send it.",
            {"language": {"type": "string"}}),
    _schema("sweep_forgotten_orders", "Deterministically find overdue orders and persist safety alerts."),
]


def _result_summary(result: dict) -> dict:
    if "safe" in result:
        return {"safe": result["safe"], "conflicts": result.get("conflicts", [])}
    if "alerts" in result:
        return {"alerts": [{"id": a.get("id"), "severity": a.get("severity"), "title": a.get("title")} for a in result["alerts"]]}
    if "new_nodes" in result:
        return {"new_nodes": [{"id": n.get("id"), "type": n.get("ntype"), "label": n.get("label")} for n in result["new_nodes"]],
                "superseded_node_ids": result.get("superseded_node_ids", [])}
    if "codes" in result:
        return {"codes": [{"system": c.get("system"), "code": c.get("code"), "validated": c.get("validated")} for c in result["codes"]],
                "rejected": result.get("rejected", [])}
    return {key: value for key, value in result.items() if key not in ("facts", "note", "sbar", "summary")}


def _fallback_route(ctx: ToolContext, input_kind: str) -> list[tuple[str, dict]]:
    if ctx.source_kind == "correction":
        return [("extract_note_and_facts", {}), ("ingest_facts", {})]
    if input_kind in ("image", "document"):
        return [("extract_note_and_facts", {}), ("ingest_facts", {}), ("run_guardian", {})]
    return [
        ("extract_note_and_facts", {}), ("ingest_facts", {}), ("run_guardian", {}),
        ("suggest_billing_codes", {}), ("draft_handoff", {}),
        ("draft_patient_summary", {"language": ctx.language}),
    ]


def _execute_tool(ctx: ToolContext, name: str, arguments: dict) -> dict:
    function = TOOL_REGISTRY.get(name)
    if not function:
        raise ValueError(f"unknown tool: {name}")
    return function(ctx, **arguments)


def build_bundle(ctx: ToolContext) -> dict:
    implicated = set()
    for alert in ctx.alerts:
        raw = alert.get("node_ids") or []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = []
        implicated.update(raw)
    staged_orders = []
    for node in ctx.new_nodes:
        if node.get("ntype") in ("medication", "lab_order", "procedure"):
            staged_orders.append({
                "node_id": node["id"], "label": node["label"], "type": node["ntype"],
                "flagged": node["id"] in implicated,
            })
    ctx.artifacts["staged_orders"] = staged_orders
    return {
        "encounter_id": ctx.encounter_id,
        "trace": ctx.trace,
        "note": ctx.artifacts.get("note"),
        "new_nodes": [{key: node.get(key) for key in ("id", "ntype", "label", "category", "status")} for node in ctx.new_nodes],
        "alerts": ctx.alerts,
        "codes": ctx.artifacts.get("codes", []),
        "handoff": ctx.artifacts.get("handoff"),
        "patient_summary": ctx.artifacts.get("patient_summary"),
        "staged_orders": staged_orders,
    }


def run_agent(ctx: ToolContext, model_input_text: str, input_kind: str) -> dict:
    ctx.input_text = model_input_text
    messages = [
        {"role": "system", "content": ORCHESTRATOR_SYSTEM},
        {"role": "user", "content": f"INPUT_KIND={input_kind}\n\n{model_input_text}"},
    ]
    began = time.monotonic()
    used_tool = False
    model_failed = False
    for _step in range(MAX_STEPS):
        try:
            message = llm.ask_tools(messages, TOOL_SCHEMAS, effort=REASONING_EFFORT_HIGH)
        except Exception:
            model_failed = True
            break
        messages.append(message)
        calls = message.get("tool_calls") or []
        if not calls:
            break
        for call in calls:
            name = call.get("function", {}).get("name", "")
            arguments = call.get("function", {}).get("arguments") or {}
            try:
                result = _execute_tool(ctx, name, arguments)
                summary = _result_summary(result)
                ctx.trace.append({"tool": name, "args": arguments, "status": "ok", "result_summary": summary})
                tool_payload = {"ok": True, "result": result}
                used_tool = True
            except Exception as exc:
                summary = {"error": str(exc)}
                ctx.trace.append({"tool": name, "args": arguments, "status": "error", "result_summary": summary})
                tool_payload = {"ok": False, "error": str(exc)}
            messages.append({
                "role": "tool", "tool_name": name,
                "content": json.dumps(tool_payload, ensure_ascii=False, default=str),
            })
    if not used_tool:
        for name, arguments in _fallback_route(ctx, input_kind):
            try:
                result = _execute_tool(ctx, name, arguments)
                ctx.trace.append({"tool": name, "args": arguments, "status": "ok",
                                  "fallback": True, "result_summary": _result_summary(result)})
                if name == "extract_note_and_facts" and input_kind in ("image", "document"):
                    for fact in ctx.last_facts:
                        if fact.get("ntype") != "medication":
                            continue
                        reconcile_args = {"drug": fact.get("label", "")}
                        reconciliation = _execute_tool(ctx, "reconcile_medication", reconcile_args)
                        ctx.trace.append({
                            "tool": "reconcile_medication", "args": reconcile_args,
                            "status": "ok", "fallback": True,
                            "result_summary": _result_summary(reconciliation),
                        })
            except Exception as exc:
                ctx.trace.append({"tool": name, "args": arguments, "status": "error",
                                  "fallback": True, "result_summary": {"error": str(exc)}})
    bundle = build_bundle(ctx)
    if ctx.encounter_id is not None and repo.get_agent_run(ctx.encounter_id):
        repo.update_agent_run(
            ctx.encounter_id, trace=ctx.trace, bundle=bundle,
            status="failed" if model_failed and not ctx.trace else "draft",
            latency_ms=round((time.monotonic() - began) * 1000),
        )
    return bundle


def approve_run(patient_id: int, encounter_id: int, approvals: dict) -> dict:
    run = repo.get_agent_run(encounter_id)
    if not run or run["patient_id"] != patient_id:
        raise ValueError("agent run not found for patient")
    bundle = run["bundle"]
    committed: dict[str, Any] = {"codes": [], "orders": []}
    if approvals.get("sign_note") and bundle.get("note"):
        committed["note"] = repo.sign_encounter_note(encounter_id, bundle["note"])
    approved_keys = {(item.get("system"), item.get("code")) for item in approvals.get("codes", [])}
    selected_codes = [item for item in bundle.get("codes", []) if (item.get("system"), item.get("code")) in approved_keys]
    committed["codes"] = repo.finalize_billing_codes(patient_id, encounter_id, selected_codes)
    if approvals.get("handoff") and bundle.get("handoff"):
        h = bundle["handoff"]
        committed["handoff"] = repo.create_handoff(
            patient_id, None, h.get("situation"), h.get("background"), h.get("assessment"),
            h.get("recommendation"), h.get("priority_note"), [encounter_id],
        )
    if approvals.get("send_summary") and bundle.get("patient_summary"):
        committed["patient_summary"] = repo.create_document(
            patient_id, None, "patient_summary", explanation=bundle["patient_summary"]
        )
    staged = {str(item["node_id"]): item for item in bundle.get("staged_orders", [])}
    for raw_id, action in (approvals.get("orders") or {}).items():
        item = staged.get(str(raw_id))
        if not item or action not in ("keep", "cancel"):
            continue
        node_id = int(raw_id)
        if action == "cancel":
            node = graph.supersede_node(node_id)
        else:
            node = next((n for n in graph.nodes_for(patient_id) if n["id"] == node_id), None)
            if node and node.get("ntype") == "lab_order":
                repo.create_reminder(patient_id, node["label"], schedule_text="Follow ordered recheck timing")
        committed["orders"].append({"node_id": node_id, "action": action, "node": node})
        for alert in guardian.list_alerts(patient_id, status="active"):
            try:
                node_ids = json.loads(alert.get("node_ids") or "[]")
            except json.JSONDecodeError:
                node_ids = []
            if node_id in node_ids:
                guardian.update_alert(alert["id"], "acknowledged")
    bundle["approval"] = committed
    repo.update_agent_run(encounter_id, bundle=bundle, status="approved", approved=True)
    return {"encounter_id": encounter_id, "committed": committed}


def get_trace(encounter_id: int) -> list[dict]:
    run = repo.get_agent_run(encounter_id)
    if not run:
        raise ValueError("agent run not found")
    return run["trace"]


def recent_runs(patient_id: int, limit: int = 3) -> list[dict]:
    return repo.list_agent_runs(patient_id, limit)


def patient_roi(patient_id: int) -> dict:
    """Conservative, clearly labeled estimates derived from local records."""
    with db.connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS runs, COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
               FROM agent_runs WHERE patient_id=? AND status!='failed'""",
            (patient_id,),
        ).fetchone()
        code_count = conn.execute(
            "SELECT COUNT(*) FROM billing_codes WHERE patient_id=?", (patient_id,)
        ).fetchone()[0]
        near_misses = conn.execute(
            "SELECT COUNT(*) FROM guardian_alerts WHERE patient_id=? AND severity='critical'",
            (patient_id,),
        ).fetchone()[0]
    runs = int(row["runs"] or 0)
    return {
        "runs": runs,
        "documentation_minutes_saved_estimate": runs * 8,
        "coding_revenue_captured_estimate_usd": int(code_count) * 75,
        "finalized_codes": int(code_count),
        "near_misses_prevented": int(near_misses),
        "runs_per_shift": runs,
        "avg_latency_ms": round(float(row["avg_latency_ms"] or 0)),
        "methodology": {
            "documentation": "8 minutes estimated per completed agent run",
            "coding": "$75 nominal estimate per finalized code; not actual reimbursement",
            "near_misses": "critical deterministic Guardian alerts",
            "throughput": "all recorded runs in the current demo dataset",
        },
    }
