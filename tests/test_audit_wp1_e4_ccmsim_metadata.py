"""WP1-E4 wholly synthetic small-source fixtures; no music/audio or participant files."""
from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_wp1_e4_ccmsim_metadata as e4


def make_csv(header,rows):
    output=StringIO(newline="")
    writer=csv.DictWriter(output,fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def fictional_tables():
    ids=[]
    mappings=[]
    for i,source in enumerate(e4.SOURCES):
        for j in range(54):
            sid=f"fake{i:02d}_{j:02d}"
            mappings.append(dict(
                survey_audio_id=sid,dataset=source,
                audio_file_path="fictional-unpublished-track.mp3",
                survey_start_second="0",survey_end_second="20"))
            ids.append(sid)
    # Exactly 463 fictional audio IDs; at least a cycle gives one
    # connected component. 667 more unique pairs added deterministically.
    active=ids[:463]
    pairs=set()
    for i in range(463):
        pairs.add(tuple(sorted((active[i],active[(i+1)%463]))))
    for step in range(2,463):
        if len(pairs)==1130:
            break
        for i in range(463):
            p=tuple(sorted((active[i],active[(i+step)%463])))
            pairs.add(p)
            if len(pairs)==1130:
                break
    rows=[]
    multiplicities=[1]*1052+[2]*48+[3]*22+[4]*4+[5]*4
    for pair,k in zip(sorted(pairs),multiplicities):
        row={name:"0.5" for name in e4.LABELS}
        row.update({
            "audio_pair":"-".join(pair),
            "overall_music_similarity_annotations":"[1]",
            "cultural_similarity_annotations":"[1]",
            "recommendation_level_annotations":"[1]",
            "num_annotators":str(k),
        })
        rows.append(row)
    return make_csv(e4.MAPPING_COLUMNS,mappings),make_csv(e4.LABEL_COLUMNS,rows)


class CcmsimMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping_raw,cls.human_raw=fictional_tables()

    def test_fictional_1130_pair_count_annotator_quality_grouping(self):
        report=e4.profile(self.mapping_raw,self.human_raw)
        self.assertEqual(report["published_unique_annotated_pairs"],1130)
        self.assertEqual(report["published_mapping_rows"],486)
        self.assertEqual(report["published_unique_audio_clips_used_by_rated_pairs"],463)
        self.assertEqual(report["all_annotator_votes"],1250)
        self.assertEqual(report["observed_annotator_votes_per_pair"],
                         {"1":1052,"2":48,"3":22,"4":4,"5":4})
        self.assertEqual(report["pair_graph_source_connected_component_count"],1)
        self.assertFalse(report["general_metric_selected"])
        self.assertFalse(report["general_metric_quality_measured"])
        self.assertFalse(report["source_clip_to_artist_or_album_grouping_verified"])
        self.assertTrue(report[
            "upstream_readme_claims_52_clips_per_dataset_not_same_as_mapping_54"])
        serialized=json.dumps(report)
        for private in ("fictional-unpublished-track","audio_file_path",
                        "survey_audio_id","fake00_00","participant_id"):
            self.assertNotIn(private,serialized)

    def test_fail_closed_on_duplicate_pair_and_missing_clip_mapping(self):
        sample=e4.read_csv(self.human_raw,e4.LABEL_COLUMNS)
        wrong=[dict(row) for row in sample]
        wrong[1]["audio_pair"]=wrong[0]["audio_pair"]
        with self.assertRaises(ValueError):
            e4.profile(self.mapping_raw,make_csv(e4.LABEL_COLUMNS,wrong))
        wrong=[dict(row) for row in sample]
        wrong[0]["audio_pair"]="not_in_pinned_map-also_missing"
        with self.assertRaises(ValueError):
            e4.profile(self.mapping_raw,make_csv(e4.LABEL_COLUMNS,wrong))

    def test_fail_closed_on_missing_annotator_or_bad_scores(self):
        rows=e4.read_csv(self.human_raw,e4.LABEL_COLUMNS)
        for patch in ({"num_annotators":"0"},
                      {"overall_music_similarity":"nan"},
                      {"overall_music_similarity":"1.5"}):
            modified=[dict(r) for r in rows]
            modified[0].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                e4.profile(self.mapping_raw,make_csv(e4.LABEL_COLUMNS,modified))

    def test_fail_closed_on_new_source_schema_and_bad_source_count(self):
        bad=self.mapping_raw.replace(b"survey_audio_id",b"song_key",1)
        with self.assertRaises(ValueError):
            e4.profile(bad,self.human_raw)
        mapping=e4.read_csv(self.mapping_raw,e4.MAPPING_COLUMNS)
        del mapping[-1]
        with self.assertRaises(ValueError):
            e4.profile(make_csv(e4.MAPPING_COLUMNS,mapping),self.human_raw)

    def test_git_blob_identity_is_exact_and_has_no_unapproved_requests(self):
        sample=b"safe-synthetic-test"
        self.assertEqual(e4.git_blob_sha(sample),
          __import__("hashlib").sha1(b"blob 19\x00"+sample).hexdigest())
        with self.assertRaises(ValueError):
            e4.pinned_download("data/annotations/responses/raw-person.json")
        class Response:
            def __init__(self,payload,url):
                self.payload=payload
                self.status=200
                self.url=url
                self.headers={}
            def geturl(self): return self.url
            def read(self,n): return self.payload[:n]
            def __enter__(self): return self
            def __exit__(self,*args): return False
        path="data/annotations/human_similarity.csv"
        url=e4.ORIGIN+path
        with self.assertRaises(ValueError):
            e4.pinned_download(path,opener=lambda req,timeout:Response(sample,url))
        self.assertEqual(len(e4.FILES),2)


if __name__=="__main__":
    unittest.main()
