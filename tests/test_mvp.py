import tempfile, unittest
from pathlib import Path
from core.db import connect, initialize
from features.guardian import alerts
from seed_data import evaluation, load

class MvpTests(unittest.TestCase):
 def setUp(self): self.temp=tempfile.TemporaryDirectory();self.db=connect(Path(self.temp.name)/'test.sqlite');initialize(self.db)
 def tearDown(self): self.db.close();self.temp.cleanup()
 def test_normal_has_no_alerts(self): self.assertEqual([],alerts(self.db,load(self.db,'normal')))
 def test_allergy_has_evidence_linked_high_alert(self):
  alert=alerts(self.db,load(self.db,'allergy'))[0];self.assertEqual('high',alert['severity']);self.assertEqual(2,len(alert['source_fact_ids']));self.assertIn('Requires clinician review',alert['message'])
 def test_synthetic_evaluation_passes(self): self.assertTrue(all(r['pass'] and r['evidence_linked'] for r in evaluation(self.db)))
if __name__=='__main__':unittest.main()
