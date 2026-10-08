import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from workload_campaign import safe,prepare,verify,expected
from workload_suite import cases,PAYLOAD
class WorkloadOracles(unittest.TestCase):
 def test_escape_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for p in ('../outside','/tmp/outside','files/../../outside'):
    with self.assertRaises(ValueError):safe(root,p)
   (root/'link').symlink_to('/tmp',target_is_directory=True)
   with self.assertRaises(ValueError):safe(root,'link/outside')
 def test_delete_rejects_keeper_damage_and_target_survivor(self):
  c={**next(x for x in cases() if x['id']=='delete-selected-1000'),'count':12}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);fixture=prepare(root,c)
   with self.assertRaises(AssertionError):verify(root,c,fixture,b'OK')
   for p in fixture[0]:safe(root,p).unlink()
   verify(root,c,fixture,b'OK')
   safe(root,fixture[1][0]).write_text('damaged')
   with self.assertRaises(AssertionError):verify(root,c,fixture,b'OK')
 def test_copy_rejects_corrupt_output_and_source(self):
  c={**next(x for x in cases() if x['operation']=='copy'),'count':12}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);fixture=prepare(root,c)
   for rel in fixture[0]:(root/'copied'/Path(rel).name).write_bytes(PAYLOAD.encode())
   verify(root,c,fixture,b'OK')
   (root/'copied'/Path(fixture[0][0]).name).write_bytes(b'bad')
   with self.assertRaises(AssertionError):verify(root,c,fixture,b'OK')
 def test_copy_rejects_source_metadata_changes(self):
  import os
  c={**next(x for x in cases() if x['operation']=='copy'),'count':12}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);fixture=prepare(root,c)
   for rel in fixture[0]:(root/'copied'/Path(rel).name).write_bytes(PAYLOAD.encode())
   safe(root,fixture[0][0]).chmod(0o400)
   with self.assertRaises(AssertionError):verify(root,c,fixture,b'OK')
 def test_creation_rejects_unexpected_path(self):
  c={**next(x for x in cases() if x['operation']=='create-empty'),'count':12}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);fixture=prepare(root,c)
   for rel in fixture[0]:safe(root,rel).touch()
   verify(root,c,fixture,b'OK');(root/'files/stray').touch()
   with self.assertRaises(AssertionError):verify(root,c,fixture,b'OK')
 def test_tree_mixes_targets_and_keepers_in_every_directory(self):
  from workload_campaign import paths
  c=next(x for x in cases() if x['id']=='delete-tree-100000')
  targets,keepers=paths(c)
  self.assertEqual({str(Path(x).parent) for x in targets},{str(Path(x).parent) for x in keepers})
  self.assertEqual(len({str(Path(x).parent) for x in targets}),100)
 def test_timeout_kills_process_group(self):
  from campaign_measure import measure,isolated_env
  with tempfile.TemporaryDirectory() as td:
   rec,_,_=measure(['/usr/bin/sleep','10'],Path(td),isolated_env(Path(td)/'home'),timeout=.1)
   self.assertTrue(rec['timeout']);self.assertIsNone(rec['wall_ms'])
if __name__=='__main__':unittest.main()
