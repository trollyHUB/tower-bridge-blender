"""Cache reuse is deliberately narrower than normal render cache invalidation."""
import copy
import hashlib
import json
import unittest
from tools.migrate_camera_cache import certified_identity

class CameraReuseProofTests(unittest.TestCase):
    def baseline(self):
        blocks={'meshes':{'body':'geometry'},'materials':{'paint':'nodes'}}
        digest=hashlib.sha256(json.dumps(blocks,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        old={'scene_sha256':'old','config_sha256':'config','implementation_sha256':'renderer','frames':1440}
        current=dict(old,scene_sha256='new')
        proof={'passed':True,'identity_before':old,'old_scene_sha256':'old','new_scene_sha256':'new',
               'patch_implementation_sha256':'patch','normalized_datablocks':blocks,
               'normalized_fingerprint_sha256':digest,'affected_frames':list(range(352,408)),
               'camera':'09 | Bus stop camera'}
        return proof,old,current

    def test_accepts_only_certified_scene_hash_change(self):
        proof,old,current=self.baseline()
        self.assertEqual(certified_identity(proof,old,current,'patch'),current)

    def test_rejects_geometry_fingerprint_tampering(self):
        proof,old,current=self.baseline();proof['normalized_datablocks']['meshes']['body']='modified'
        with self.assertRaisesRegex(ValueError,'Fingerprint'):certified_identity(proof,old,current,'patch')

    def test_rejects_renderer_config_scene_and_proof_changes(self):
        for key in ('config_sha256','implementation_sha256','scene_sha256'):
            proof,old,current=self.baseline();current[key]='different'
            with self.assertRaises(ValueError):certified_identity(proof,old,current,'patch')
        proof,old,current=self.baseline()
        with self.assertRaises(ValueError):certified_identity(proof,old,current,'changed_patch')

if __name__=='__main__':unittest.main()
