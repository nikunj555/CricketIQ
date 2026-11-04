import numpy as np
import pytest
from backend.app.services.dtw_service import dtw_service

def test_dtw_identical_sequences():
    seq = np.array([
        [0.8, 0.9, 0.2, 0.4, 0.3],
        [0.7, 0.85, 0.25, 0.5, 0.32],
        [0.6, 0.8, 0.3, 0.6, 0.35]
    ], dtype=np.float64)
    dist, path, sim = dtw_service.compute_dtw(seq, seq)
    assert dist == 0.0
    assert sim == 100.0
    assert len(path) == 3
    assert path == [(0, 0), (1, 1), (2, 2)]

def test_dtw_time_warped_sequences():
    # Sequence 1: 3 frames
    seq1 = np.array([
        [0.8, 0.9, 0.2, 0.4, 0.3],
        [0.7, 0.85, 0.25, 0.5, 0.32],
        [0.6, 0.8, 0.3, 0.6, 0.35]
    ], dtype=np.float64)
    # Sequence 2: 5 frames (stretched temporal pacing)
    seq2 = np.array([
        [0.8, 0.9, 0.2, 0.4, 0.3],
        [0.8, 0.9, 0.2, 0.4, 0.3],
        [0.7, 0.85, 0.25, 0.5, 0.32],
        [0.6, 0.8, 0.3, 0.6, 0.35],
        [0.6, 0.8, 0.3, 0.6, 0.35]
    ], dtype=np.float64)
    dist, path, sim = dtw_service.compute_dtw(seq1, seq2)
    assert dist == 0.0
    assert sim == 100.0
    assert len(path) >= 5

def test_dtw_divergent_sequences():
    seq1 = np.zeros((10, 5), dtype=np.float64)
    seq2 = np.ones((10, 5), dtype=np.float64)
    dist, path, sim = dtw_service.compute_dtw(seq1, seq2)
    assert dist > 1.0
    assert sim < 50.0
