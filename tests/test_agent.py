from core import agent, graph, repo


def tool_turn(*calls):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": f"call_{index}", "function": {"name": name, "arguments": arguments}}
            for index, (name, arguments) in enumerate(calls)
        ],
    }


def complete_turn():
    return {"role": "assistant", "content": "Complete.", "tool_calls": []}


def test_prepare_input_accepts_browser_pretranscribed_speech():
    assert agent.prepare_input("speech", text="spoken round") == ("spoken round", "speech")


def test_input_kinds_drive_distinct_model_selected_tool_paths(patient, monkeypatch):
    routes = {
        "speech": [
            ("extract_note_and_facts", {}), ("ingest_facts", {}), ("run_guardian", {}),
            ("suggest_billing_codes", {}), ("draft_handoff", {}),
            ("draft_patient_summary", {"language": "es"}),
        ],
        "document": [
            ("extract_note_and_facts", {}), ("reconcile_medication", {"drug": "ketorolac"}),
            ("ingest_facts", {}), ("run_guardian", {}),
        ],
        "text": [("extract_note_and_facts", {}), ("ingest_facts", {})],
    }
    current_kind = {"value": "speech"}

    def fake_tools(messages, schemas, effort=None):
        if any(message.get("role") == "tool" for message in messages):
            return complete_turn()
        return tool_turn(*routes[current_kind["value"]])

    monkeypatch.setattr(agent.llm, "ask_tools", fake_tools)
    monkeypatch.setattr(agent.graph, "structure_and_extract", lambda text: (
        {"summary": text, "chief_complaint": None, "medications": [], "follow_ups": [], "emotional_tone": None},
        [],
    ))
    monkeypatch.setattr(agent.llm, "ask_json", lambda *args, **kwargs: {
        "conditions": [], "em_level": "moderate", "em_evidence": "documented complexity"
    })
    monkeypatch.setattr(agent.llm, "ask", lambda *args, **kwargs: "Resumen para la paciente.")

    actual = {}
    for kind, text in (("speech", "round"), ("document", "ketorolac"), ("text", "cancel the EKG")):
        current_kind["value"] = kind
        encounter = repo.create_encounter(patient["id"], None, agent.source_kind_for(kind, text), raw_transcript=text)
        repo.create_agent_run(patient["id"], encounter["id"], kind, agent.source_kind_for(kind, text), "es", text)
        ctx = agent.ToolContext(patient["id"], encounter["id"], agent.source_kind_for(kind, text), "es")
        bundle = agent.run_agent(ctx, text, kind)
        actual[kind] = [event["tool"] for event in bundle["trace"]]

    assert actual["speech"] == [name for name, _ in routes["speech"]]
    assert actual["document"] == [name for name, _ in routes["document"]]
    assert actual["text"] == [name for name, _ in routes["text"]]


def test_document_medication_triggers_cross_modal_guardian_alert(patient, monkeypatch):
    graph.add_node(patient["id"], "medication", "Warfarin", category="anticoagulant", source_kind="admission")
    turns = iter([
        tool_turn(
            ("extract_note_and_facts", {}),
            ("reconcile_medication", {"drug": "ketorolac"}),
            ("ingest_facts", {}),
            ("run_guardian", {}),
        ),
        complete_turn(),
    ])
    monkeypatch.setattr(agent.llm, "ask_tools", lambda *args, **kwargs: next(turns))
    monkeypatch.setattr(agent.graph, "structure_and_extract", lambda text: (
        {"summary": "Outside ketorolac prescription", "chief_complaint": None,
         "medications": ["Ketorolac 10 mg"], "follow_ups": [], "emotional_tone": None},
        [{"ntype": "medication", "label": "Ketorolac", "category": "nsaid",
          "polarity": "asserted", "confidence": 0.99, "detail": "10 mg"}],
    ))
    encounter = repo.create_encounter(patient["id"], None, "prescription", raw_transcript="ketorolac 10 mg")
    repo.create_agent_run(patient["id"], encounter["id"], "document", "prescription", "es", "ketorolac 10 mg")
    ctx = agent.ToolContext(patient["id"], encounter["id"], "prescription", "es")

    bundle = agent.run_agent(ctx, "ketorolac 10 mg", "document")

    assert bundle["alerts"][0]["severity"] == "critical"
    assert "bleeding" in bundle["alerts"][0]["message"].lower()
    reconciliation = next(event for event in bundle["trace"] if event["tool"] == "reconcile_medication")
    assert reconciliation["result_summary"]["safe"] is False


def test_document_fallback_reconciles_each_extracted_medication(patient, monkeypatch):
    monkeypatch.setattr(agent.llm, "ask_tools", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline model unavailable")))
    monkeypatch.setattr(agent.graph, "structure_and_extract", lambda text: (
        {"summary": "Ketorolac", "chief_complaint": None, "medications": ["Ketorolac"],
         "follow_ups": [], "emotional_tone": None},
        [{"ntype": "medication", "label": "Ketorolac", "category": "nsaid",
          "polarity": "asserted", "confidence": 1.0, "detail": None}],
    ))
    ctx = agent.ToolContext(patient["id"], None, "prescription", "en")

    bundle = agent.run_agent(ctx, "Ketorolac", "document")

    assert [event["tool"] for event in bundle["trace"]] == [
        "extract_note_and_facts", "reconcile_medication", "ingest_facts", "run_guardian"
    ]


def test_billing_tool_drops_hallucinated_code_and_uses_curated_labels(patient, monkeypatch):
    ctx = agent.ToolContext(patient["id"], None, "round", "en")
    ctx.artifacts["note"] = {"summary": "Atrial fibrillation with moderate complexity."}
    monkeypatch.setattr(agent.llm, "ask_json", lambda *args, **kwargs: {
        "codes": [
            {"system": "ICD-10", "code": "I48.91", "evidence": "Atrial fibrillation"},
            {"system": "ICD-10", "code": "FAKE.1", "evidence": "invented"},
            {"system": "CPT", "code": "99232", "evidence": "moderate complexity"},
        ]
    })

    result = agent.suggest_billing_codes(ctx)

    assert [item["code"] for item in result["codes"]] == ["I48.91", "99232"]
    assert all(item["validated"] for item in result["codes"])
    assert result["rejected"] == [{"system": "ICD-10", "code": "FAKE.1", "reason": "not in curated tables"}]


def test_correction_supersedes_matching_order_with_audit_edge(patient, monkeypatch):
    ekg = graph.add_node(patient["id"], "lab_order", "Repeat EKG", source_kind="round")
    ctx = agent.ToolContext(patient["id"], None, "correction", "en")
    ctx.last_facts = [{"ntype": "lab_order", "label": "EKG", "category": None,
                       "polarity": "denied", "confidence": 1.0, "detail": "cancel"}]

    result = agent.ingest_facts(ctx)

    updated = next(node for node in graph.nodes_for(patient["id"]) if node["id"] == ekg["id"])
    assert updated["status"] == "superseded"
    assert result["superseded_node_ids"] == [ekg["id"]]
    assert any(edge["relation"] == "relates_to" and edge["dst_node_id"] == ekg["id"] for edge in graph.edges_for(patient["id"]))


def test_approval_commits_only_selected_drafts(patient):
    encounter = repo.create_encounter(patient["id"], None, "round", raw_transcript="round")
    bundle = {
        "note": {"summary": "Draft note", "chief_complaint": "Chest pain", "medications": [],
                 "follow_ups": [], "emotional_tone": None},
        "codes": [
            {"system": "ICD-10", "code": "I48.91", "label": "Atrial fibrillation, unspecified",
             "evidence": "atrial fibrillation", "validated": True},
            {"system": "CPT", "code": "99232", "label": "Subsequent hospital care, moderate complexity",
             "evidence": "moderate", "validated": True},
        ],
        "handoff": {"situation": "Draft only"},
        "patient_summary": "Draft only",
        "staged_orders": [], "alerts": [], "new_nodes": [], "trace": [],
    }
    repo.create_agent_run(patient["id"], encounter["id"], "speech", "round", "es", "round")
    repo.update_agent_run(encounter["id"], bundle=bundle, trace=[], status="draft")

    result = agent.approve_run(patient["id"], encounter["id"], {
        "sign_note": False,
        "codes": [{"system": "ICD-10", "code": "I48.91"}],
        "handoff": False,
        "send_summary": False,
        "orders": {},
    })

    assert repo.get_encounter(encounter["id"])["summary"] is None
    assert [item["code"] for item in repo.list_billing_codes(patient["id"])] == ["I48.91"]
    assert repo.list_handoffs(patient["id"]) == []
    assert result["committed"]["codes"][0]["code"] == "I48.91"
    assert repo.get_agent_run(encounter["id"])["bundle"]["approval"]["codes"][0]["code"] == "I48.91"
