"""Synthetic scenarios used by the dashboard and tests."""
from core.graph import add_encounter, add_fact, add_patient
from features.guardian import alerts, run

SCENARIOS={
 "normal":("Avery Demo",[("observation","Blood pressure","120/80","Blood pressure recorded as 120/80.")]),
 "allergy":("Jordan Demo",[("allergy","Penicillin allergy","penicillin","Allergy list documents penicillin allergy."),("medication","Penicillin 250 mg","penicillin","Prescription lists penicillin 250 mg.")]),
 "duplicate":("Riley Demo",[("medication","Acetaminophen 500 mg","acetaminophen","Medication list includes acetaminophen 500 mg."),("medication","Acetaminophen 325 mg","acetaminophen","Prescription lists acetaminophen 325 mg.")])}
def load(db, name):
    if name not in SCENARIOS: raise KeyError(name)
    display,fact_list=SCENARIOS[name]; patient_id=add_patient(db,display); encounter_id=add_encounter(db,patient_id,f"Synthetic {name} scenario")
    for kind,label,value,source in fact_list: add_fact(db,patient_id,encounter_id,kind,label,value,source,True)
    run(db,patient_id); return patient_id
def evaluation(db):
    expected={"normal":0,"allergy":1,"duplicate":1}; result=[]
    for scenario,count in expected.items():
        patient_id=load(db,scenario); items=alerts(db,patient_id); result.append({"scenario":scenario,"pass":len(items)==count,"alerts":len(items),"evidence_linked":all(bool(i['source_fact_ids']) for i in items)})
    return result
