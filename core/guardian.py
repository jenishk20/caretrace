"""The Guardian — Confide's "Watch over".

An always-on reasoning loop that checks what's said and done against the graph and
speaks up on its own. Three behaviors, all triggered by deterministic code against
curated data (core/curated.py). Gemma is used ONLY to phrase the human sentence —
never to decide whether there's a problem.

  1. allergy / interaction  — a newly ordered drug vs. the patient's active
     allergies and current meds.
  2. contradiction          — a patient statement that denies something the record
     asserts ("not on blood thinners" vs. warfarin on file).
  3. forgotten order        — an ordered lab/recheck whose window has elapsed with
     nothing marking it done.

Every alert is persisted to guardian_alerts, so the record of what Confide caught
survives across the whole stay.
"""
from __future__ import annotations

import json

from core import db, graph
from core.config import GUARDIAN_LLM_PHRASING
from core.curated import allergy_conflict, interaction_between
from core.llm import ask


def _create_alert(patient_id, atype, severity, title, message, node_ids, encounter_id=None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO guardian_alerts
               (patient_id, atype, severity, title, message, node_ids, encounter_id, status, created_at)
               VALUES (?,?,?,?,?,?,?, 'active', ?)""",
            (patient_id, atype, severity, title, message, json.dumps(node_ids), encounter_id, db.now()),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM guardian_alerts WHERE id=?", (cur.lastrowid,)).fetchone())


def _phrase(kind: str, facts: str, fallback: str) -> str:
    """Phrase a gentle, clinician-facing alert. Templates are instant and read
    naturally (default); Gemma phrasing is optional but adds latency on stage."""
    if not GUARDIAN_LLM_PHRASING:
        return fallback
    try:
        prompt = (
            f"You are Confide, a calm bedside clinical assistant. In ONE or TWO short sentences, "
            f"gently and factually flag this to the care team. Do not give orders; just surface the "
            f"concern and the evidence. Context ({kind}): {facts}"
        )
        return ask(prompt, temperature=0.3, max_tokens=120)
    except Exception:
        return fallback


def _already_alerted(patient_id: int, atype: str, node_ids: list[int]) -> bool:
    """Avoid duplicate alerts for the same implicated nodes."""
    key = set(node_ids)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT node_ids FROM guardian_alerts WHERE patient_id=? AND atype=? AND status!='dismissed'",
            (patient_id, atype),
        ).fetchall()
    for r in rows:
        try:
            if set(json.loads(r["node_ids"] or "[]")) & key:
                return True
        except json.JSONDecodeError:
            continue
    return False


# --- 1. allergy / interaction ------------------------------------------------

def check_medication(patient_id: int, med_node: dict, encounter_id: int | None = None) -> list[dict]:
    """Called for every newly extracted medication node. Cross-check against the
    patient's active allergies and current meds using the curated tables."""
    alerts: list[dict] = []
    cat = med_node.get("category")
    if not cat:
        return alerts

    # a) allergy conflict
    for allergy in [n for n in graph.nodes_for(patient_id, active_only=True) if n["ntype"] == "allergy"]:
        acat = allergy.get("category")
        if acat and allergy_conflict(acat, cat) and not _already_alerted(patient_id, "allergy", [med_node["id"], allergy["id"]]):
            graph.add_edge(patient_id, med_node["id"], allergy["id"], "conflicts_with", "allergy conflict")
            msg = _phrase(
                "allergy conflict",
                f"The team is about to start {med_node['label']} ({cat}), but {allergy['label']} is on file.",
                f"Hold on — {med_node['label']} conflicts with the patient's {allergy['label']} on file.",
            )
            alerts.append(_create_alert(
                patient_id, "allergy", "critical",
                f"Allergy conflict: {med_node['label']}",
                msg, [med_node["id"], allergy["id"]], encounter_id,
            ))

    # b) drug-drug interaction with other active meds
    for other in [n for n in graph.nodes_for(patient_id, active_only=True)
                  if n["ntype"] == "medication" and n["id"] != med_node["id"] and n.get("category")]:
        inter = interaction_between(cat, other["category"])
        if inter and not _already_alerted(patient_id, "interaction", [med_node["id"], other["id"]]):
            severity, why = inter
            graph.add_edge(patient_id, med_node["id"], other["id"], "conflicts_with", why)
            msg = _phrase(
                "drug interaction",
                f"{med_node['label']} and {other['label']} together: {why}",
                f"{med_node['label']} interacts with {other['label']}. {why}",
            )
            alerts.append(_create_alert(
                patient_id, "interaction", severity,
                f"Interaction: {med_node['label']} + {other['label']}",
                msg, [med_node["id"], other["id"]], encounter_id,
            ))
    return alerts


# --- pure assessment (no persistence) ----------------------------------------

def assess_medication(patient_id: int, drug_label: str, drug_category: str | None = None) -> dict:
    """Check a candidate drug against the patient's active allergies and current meds WITHOUT
    writing anything to the record. Powers the patient-facing 'is this safe to take?' scan —
    the same curated judgment as check_medication, but read-only and returning plain findings.

    Returns {drug, category, safe, conflicts:[{kind, severity, with, message}]}.
    """
    from core.curated import category_for_drug

    cat = category_for_drug(drug_label, fallback=drug_category) or drug_category
    conflicts: list[dict] = []
    if cat:
        actives = graph.nodes_for(patient_id, active_only=True)
        for allergy in [n for n in actives if n["ntype"] == "allergy" and n.get("category")]:
            if allergy_conflict(allergy["category"], cat):
                conflicts.append({
                    "kind": "allergy", "severity": "critical", "with": allergy["label"],
                    "message": f"{drug_label} can react with your {allergy['label']} allergy.",
                })
        for other in [n for n in actives if n["ntype"] == "medication" and n.get("category")]:
            inter = interaction_between(cat, other["category"])
            if inter:
                severity, why = inter
                conflicts.append({
                    "kind": "interaction", "severity": severity, "with": other["label"],
                    "message": f"{drug_label} together with your {other['label']}: {why}.",
                })
    return {"drug": drug_label, "category": cat, "safe": len(conflicts) == 0, "conflicts": conflicts}


# --- 2. contradiction --------------------------------------------------------

def check_contradiction(patient_id: int, stmt_node: dict, encounter_id: int | None = None) -> list[dict]:
    """Called for every newly extracted node with polarity 'denied'. If the record
    already asserts something in the same category, that's a contradiction."""
    alerts: list[dict] = []
    if stmt_node.get("polarity") != "denied":
        return alerts
    cat = stmt_node.get("category")
    if not cat:
        return alerts
    for existing in graph.active_nodes_by_category(patient_id, cat):
        if existing["id"] == stmt_node["id"]:
            continue
        if existing.get("polarity") == "asserted" and existing["ntype"] in ("medication", "condition", "allergy"):
            if _already_alerted(patient_id, "contradiction", [stmt_node["id"], existing["id"]]):
                continue
            graph.add_edge(patient_id, stmt_node["id"], existing["id"], "contradicts",
                           f"patient denies {cat}, but {existing['label']} is on file")
            msg = _phrase(
                "record contradiction",
                f"The patient just said they are not on {cat.replace('_',' ')}, but "
                f"{existing['label']} was recorded on {existing.get('source_kind','file')}.",
                f"Just a gentle flag — {existing['label']} was recorded on "
                f"{existing.get('source_kind','admission')}, which doesn't line up with the patient "
                f"just saying they aren't on any {cat.replace('_',' ')}.",
            )
            alerts.append(_create_alert(
                patient_id, "contradiction", "warning",
                f"Possible contradiction: {existing['label']}",
                msg, [stmt_node["id"], existing["id"]], encounter_id,
            ))
    return alerts


# --- 3. forgotten order ------------------------------------------------------

def sweep_forgotten_orders(patient_id: int) -> list[dict]:
    """Find lab_order nodes whose recheck window has elapsed and that were never
    marked done. Called on demand (end-of-encounter button) and periodically."""
    alerts: list[dict] = []
    now = db.now_dt()
    for node in graph.nodes_for(patient_id):
        if node["ntype"] != "lab_order" or node["completed"]:
            continue
        due = node.get("recheck_due_at")
        if not due:
            continue
        try:
            from datetime import datetime
            due_dt = datetime.fromisoformat(due)
        except ValueError:
            continue
        if now >= due_dt and not _already_alerted(patient_id, "forgotten_order", [node["id"]]):
            msg = _phrase(
                "forgotten order",
                f"'{node['label']}' was ordered earlier and its recheck window has passed "
                f"with nothing marking it done.",
                f"One thing before you go — {node['label']} was ordered earlier and hasn't "
                f"been rechecked yet.",
            )
            alerts.append(_create_alert(
                patient_id, "forgotten_order", "warning",
                f"Un-rechecked order: {node['label']}",
                msg, [node["id"]],
            ))
    return alerts


# --- run all checks on a batch of newly ingested nodes -----------------------

def review_new_nodes(patient_id: int, new_nodes: list[dict], encounter_id: int | None = None) -> list[dict]:
    """Run every relevant Guardian check across a batch of freshly ingested nodes.
    Returns all alerts raised, most-critical first."""
    alerts: list[dict] = []
    for node in new_nodes:
        if node["ntype"] == "medication":
            alerts += check_medication(patient_id, node, encounter_id)
        if node.get("polarity") == "denied":
            alerts += check_contradiction(patient_id, node, encounter_id)
    order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: order.get(a["severity"], 3))
    return alerts


def list_alerts(patient_id: int, status: str | None = None) -> list[dict]:
    q = "SELECT * FROM guardian_alerts WHERE patient_id=?"
    params: list = [patient_id]
    if status:
        q += " AND status=?"
        params.append(status)
    q += " ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, created_at DESC"
    with db.connect() as conn:
        return db.rows_to_list(conn.execute(q, params).fetchall())


def update_alert(alert_id: int, status: str) -> dict | None:
    with db.connect() as conn:
        conn.execute(
            "UPDATE guardian_alerts SET status=?, resolved_at=? WHERE id=?",
            (status, db.now() if status != "active" else None, alert_id),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM guardian_alerts WHERE id=?", (alert_id,)).fetchone())
