#!/usr/bin/env python3
"""WP2-P4: synthetic four-way group-disjoint score calibration/validation.

FICTIONAL ONLY: no local music, real listener labels, audio, or personal
model activation. Same fixed pair relevance target calibrates General and
Personal via frozen sigmoid transforms; separate validation gates precede
an untouched grouped synthetic test. Untrained General is always present.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics

from general_personal_blend_contract import PersonalEvidence, choose_scores
from research_grouped_split import grouped_triplet_partition
from research_personal_synthetic_metric_learning import (
    DIM, SEED, Model, fictional_cohort, fit, squared_distance, _oracle_d2,
)

SCHEMA = "wp2-p4-fictional-fourway-score-calibration-v1"
METHODS = ("diagonal", "diagonal_plus_rank2")
BLENDS = (0, 25, 50, 75, 100)
# Invented absolute threshold for binary *pair closeness*, independent of
# model predictions and of the test set. It is NOT a musical relevance label.
FICTIONAL_ORACLE_THRESHOLD_SQUARED = {
    "axis_sparse": 20.0, "cross_feature": 70.0,
}
CAL_EPOCHS = 600
CAL_STEP = 0.6
CAL_L2 = 0.005
CALIBRATION_VERSION = "fictional-pair-relevance-sigmoid-v1"


def split_four_ways(triplets, metadata, seed=SEED):
    """192/48/48/96 question split, with track/artist/album/recording disjoint."""
    outer = grouped_triplet_partition(
        triplets, metadata, seed=seed, test_fraction=0.25)
    development = outer["train_triplet_indices"]
    middle = grouped_triplet_partition(
        [triplets[i] for i in development], metadata,
        seed=seed + 1, test_fraction=1.0/3.0)
    train = tuple(development[i] for i in middle["train_triplet_indices"])
    dev = tuple(development[i] for i in middle["holdout_triplet_indices"])
    inner = grouped_triplet_partition(
        [triplets[i] for i in dev], metadata,
        seed=seed + 2, test_fraction=0.5)
    calibration = tuple(dev[i] for i in inner["train_triplet_indices"])
    validation = tuple(dev[i] for i in inner["holdout_triplet_indices"])
    result = {
        "train": train, "calibration": calibration,
        "validation": validation, "test": outer["holdout_triplet_indices"],
    }
    identity_groups = []
    for indices in result.values():
        groups = {
            metadata[track]["artist_group"]
            for idx in indices for track in triplets[idx]
        }
        identity_groups.append(groups)
    if any(a & b for a,b in itertools.combinations(identity_groups,2)):
        raise ValueError("Four-way source group leakage")
    if (len(triplets) != 384 or sorted(len(x) for x in result.values())
            != [48,48,96,192]):
        raise ValueError("Expected immutable fictional four-way split")
    return result


def group_pairs(triplets, features, metadata, indices, scenario):
    """Every pair once per disjoint six-song group, no duplicate question weights."""
    keys = {track for index in indices for track in triplets[index]}
    by_group = {}
    for key in keys:
        if key not in features or key not in metadata:
            raise ValueError("Required synthetic feature/identity missing")
        by_group.setdefault(metadata[key]["artist_group"], []).append(key)
    samples = []
    for group in sorted(by_group):
        names = sorted(by_group[group])
        if len(names) != 6:
            raise ValueError("Incomplete source-group six-song pair catalog")
        for a,b in itertools.combinations(names,2):
            label = int(_oracle_d2(features[a], features[b], scenario)
                        <= FICTIONAL_ORACLE_THRESHOLD_SQUARED[scenario])
            samples.append((a, b, label))
    if len(samples) != len(by_group)*15:
        raise AssertionError("Pair denominator drift")
    return samples


def _sigmoid(x):
    if not math.isfinite(x):
        raise ValueError("Invalid calibrator logit")
    if x >= 0:
        return 1.0/(1.0+math.exp(-x))
    expx=math.exp(x)
    return expx/(1.0+expx)


class Calibrator:
    def __init__(self, center, intercept, slope):
        if (any(not math.isfinite(x) for x in (center, intercept, slope))
                or center <= 0 or slope < 0):
            raise ValueError("Calibrator must be finite, monotone and frozen")
        self.center, self.intercept, self.slope = center, intercept, slope

    def predict(self, distance):
        if not math.isfinite(distance) or distance < 0:
            raise ValueError("Invalid distance")
        return _sigmoid(self.intercept - self.slope * distance/self.center)

    def digest(self):
        payload=json.dumps([CALIBRATION_VERSION,self.center,
                            self.intercept,self.slope],separators=(",",":"))
        return hashlib.sha256(payload.encode("ascii")).hexdigest()


def distances(pairs, features, model):
    return [(math.sqrt(squared_distance(features[a],features[b],model)), label)
            for a,b,label in pairs]


def calibrate(observations):
    """Train-only-of-calibration monotone logistic fit with frozen versioned scale."""
    if len(observations) < 60 or not all(
            type(y) is int and y in (0,1) and
            type(d) in (int,float) and math.isfinite(d) and d >= 0
            for d,y in observations):
        raise ValueError("Invalid or insufficient fictional calibration data")
    positives=sum(y for _,y in observations)
    if min(positives,len(observations)-positives) < 8:
        raise ValueError("Class support insufficient for calibrated mapping")
    center=statistics.median(d for d,_ in observations)
    if center <= 0:
        raise ValueError("Degenerate distances")
    xys=[(d/center,y) for d,y in observations]
    intercept=math.log(positives/(len(observations)-positives))
    slope=0.65
    for _ in range(CAL_EPOCHS):
        grad_a=grad_b=0.0
        for x,y in xys:
            error=_sigmoid(intercept-slope*x)-y
            grad_a += error
            grad_b += -error*x
        grad_a/=len(xys)
        grad_b=grad_b/len(xys)+CAL_L2*slope
        intercept=max(-15.,min(15.,intercept-CAL_STEP*grad_a))
        slope=max(0.,min(20.,slope-CAL_STEP*grad_b))
    return Calibrator(center,intercept,slope)


def reliability(observations, mapper):
    if not observations or set(y for _,y in observations) != {0,1}:
        raise ValueError("Reliability evaluation needs two classes")
    pairs=[(mapper.predict(d),y) for d,y in observations]
    brier=math.fsum((p-y)**2 for p,y in pairs)/len(pairs)
    logloss=-math.fsum(y*math.log(max(1e-12,p))+
                         (1-y)*math.log(max(1e-12,1-p))
                       for p,y in pairs)/len(pairs)
    ece=0.
    for bucket in range(5):
        members=[(p,y) for p,y in pairs
                 if min(4,int(p*5))==bucket]
        if members:
            ece+=len(members)/len(pairs)*abs(
                statistics.mean(p for p,_ in members)-
                statistics.mean(y for _,y in members))
    return {
        "pair_count":len(pairs),
        "positive_count":sum(y for _,y in pairs),
        "brier":round(brier,8), "log_loss":round(logloss,8),
        "ece_5_equal_width_bins":round(ece,8),
    }


def validation_gate(validation_stats):
    """Fictional acceptance checks fixed before inspecting sealed TEST.

    This does NOT prove real user/model quality or true common calibration.
    """
    return (validation_stats["pair_count"] >= 60
            and validation_stats["positive_count"] >= 8
            and validation_stats["pair_count"]-
                validation_stats["positive_count"] >= 8
            and validation_stats["brier"] < 0.25
            and validation_stats["ece_5_equal_width_bins"] < 0.25)


def score_triplets(triplets, features, indices, general, personal,
                   general_map, personal_map, enable_personal):
    """Evaluate actual 3-pair queries without any query-local normalization."""
    if not indices:
        raise ValueError("Empty sealed test")
    counts={}
    for requested in BLENDS:
        correct=tied=fallback=0
        for idx in indices:
            a,b,c=triplets[idx]
            pairs=((a,b),(a,c),(b,c))
            gen=tuple(general_map.predict(
                math.sqrt(squared_distance(features[u],features[v],general))
            ) for u,v in pairs)
            per=tuple(personal_map.predict(
                math.sqrt(squared_distance(features[u],features[v],personal))
            ) for u,v in pairs)
            # Same contract ID is merely an engineering compatibility tag.
            # Only independently specified *fictional* quality/calibration
            # evidence may set these booleans; never activate production.
            contract=hashlib.sha256((
                CALIBRATION_VERSION+"|"+general_map.digest()+"|"+
                personal_map.digest()).encode("ascii")).hexdigest()
            opts={
                "expected_profile":"fictional-user",
                "expected_feature_fingerprint":"fictional-bliss23-v1",
                "expected_score_calibration_id":contract,
                "expected_candidate_cohort_fingerprint":"fictional-query-v1",
            }
            evidence=PersonalEvidence(
                profile_id=opts["expected_profile"],
                feature_fingerprint=opts["expected_feature_fingerprint"],
                score_calibration_id=contract,
                candidate_cohort_fingerprint=opts["expected_candidate_cohort_fingerprint"],
                version=1,quality_validated=enable_personal,
                calibration_validated=enable_personal,scores=per,
            )
            result=choose_scores(gen,requested_personal_percent=requested,
                                 personal=evidence,**opts)
            if result.effective_personal_percent==0 and requested>0:
                fallback+=1
                if result.scores != gen:
                    raise AssertionError("No exact General fallback")
            scores=result.scores
            best=max(scores)
            if sum(abs(v-best)<=1e-12 for v in scores)>1:
                tied+=1
            elif scores[0]==best:
                correct+=1
        counts[str(requested)]={
            "correct":correct,"denominator":len(indices),
            "ties_as_incorrect":tied,
            "accuracy":round(correct/len(indices),8),
            "fallback_queries":fallback,
            "effective_personal_percent":
                requested if enable_personal else 0,
        }
    return counts


def run(seed=SEED):
    scenarios={}
    for scenario in ("axis_sparse","cross_feature"):
        triplets,features,metadata=fictional_cohort(seed,scenario)
        partitions=split_four_ways(triplets,metadata,seed=seed)
        models={"raw_bliss23_euclidean":Model((1.0,)*DIM)}
        for capacity in METHODS:
            models[capacity]=fit(triplets,features,
                                 partitions["train"][:100],
                                 capacity=capacity,seed=seed+3)
        calib_pairs=group_pairs(triplets,features,metadata,
                               partitions["calibration"],scenario)
        validation_pairs=group_pairs(triplets,features,metadata,
                                    partitions["validation"],scenario)
        test_pairs=group_pairs(triplets,features,metadata,
                              partitions["test"],scenario)
        mapping={name:calibrate(distances(calib_pairs,features,model))
                 for name,model in models.items()}
        validation={name:reliability(
            distances(validation_pairs,features,model),mapping[name])
                    for name,model in models.items()}
        # No test scores/labels read before model/calibrator/gating frozen.
        # A stronger qualitative model must independently beat fixed
        # General *on validation triplets*, not the sealed test.
        val_triples={name:score_triplets(
            triplets,features,partitions["validation"],
            models["raw_bliss23_euclidean"],model,
            mapping["raw_bliss23_euclidean"],mapping[name],
            enable_personal=True)["100"]["accuracy"]
                     for name,model in models.items()}
        base_val=val_triples["raw_bliss23_euclidean"]
        gate={name:(validation_gate(validation[name]) and
                    validation_gate(validation["raw_bliss23_euclidean"]) and
                    val_triples[name] > base_val)
              for name in METHODS}
        tested={}
        for name in METHODS:
            tested[name]={
                "validation_pair_reliability":validation[name],
                "validation_triplet_accuracy":val_triples[name],
                "fictional_validation_gate_passed":gate[name],
                "sealed_test_pair_reliability":reliability(
                    distances(test_pairs,features,models[name]),mapping[name]),
                "sealed_test_blend":score_triplets(
                    triplets,features,partitions["test"],
                    models["raw_bliss23_euclidean"],models[name],
                    mapping["raw_bliss23_euclidean"],mapping[name],
                    enable_personal=gate[name]),
            }
        scenarios[scenario]={
            "fictional_track_count":len(features),
            "fictional_triplet_count":len(triplets),
            "split_triplet_counts":{k:len(v) for k,v in partitions.items()},
            "split_artist_group_counts":{k:len({
                metadata[track]["artist_group"] for i in ids
                for track in triplets[i]})
                for k,ids in partitions.items()},
            "train_only_fictional_triplets_fit":100,
            "calibration_pairs_per_model":len(calib_pairs),
            "validation_pairs_per_model":len(validation_pairs),
            "test_pairs_per_model":len(test_pairs),
            "raw_general_validation_reliability":
                validation["raw_bliss23_euclidean"],
            "raw_general_validation_triplet_accuracy":base_val,
            "raw_general_sealed_test_pair_reliability":reliability(
                distances(test_pairs,features,models["raw_bliss23_euclidean"]),
                mapping["raw_bliss23_euclidean"]),
            "learned_candidates":tested,
        }
    return {
        "schema":SCHEMA,"status":"FICTIONAL_CALIBRATION_PROTOCOL_ONLY",
        "seed":seed,"bliss_dimension":DIM,
        "target":"invented_fixed_threshold_binary_pair_closeness",
        "calibration":"train_only_of_separate_calibration_groups_monotone_sigmoid",
        "predeclared_validation_brier_max_exclusive":0.25,
        "predeclared_validation_ece_max_exclusive":0.25,
        "actual_calibration_parameters_or_personal_weights_exported":False,
        "test_used_to_fit_or_select_model":False,
        "real_calibration_or_music_similarity_certified":False,
        "personal_model_eligible_for_runtime_activation":False,
        "general_metric_selected":False,
        "scenarios":scenarios,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
        parser.error("Output must be new file in existing directory")
    report=run()
    with args.out.open("x",encoding="utf-8",newline="\n") as out:
        json.dump(report,out,indent=2,sort_keys=True,allow_nan=False)
        out.write("\n")
    print(json.dumps({
        "schema":report["schema"],
        "status":report["status"],
        "scenarios":list(report["scenarios"]),
        "real_model_activated":False,
    },indent=2))


if __name__=="__main__":
    main()
