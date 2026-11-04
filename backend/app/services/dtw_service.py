import numpy as np
from typing import Tuple, List, Dict, Any

class DTWService:
    """
    Dynamic Time Warping (DTW) for multi-dimensional biomechanical sequence alignment.
    
    Academic notes:
    - Compares temporal sequences of unequal durations.
    - Uses Euclidean distance in normalized kinematic feature space:
      [lead_knee/180, rear_knee/180, torso_inclination/90, stance_width/3, head_y]
    - Computes optimal warping path via dynamic programming recurrence:
      D(i, j) = cost(x_i, y_j) + min(D(i-1, j), D(i, j-1), D(i-1, j-1))
    """
    
    @staticmethod
    def compute_dtw(
        seq1: np.ndarray,
        seq2: np.ndarray
    ) -> Tuple[float, List[Tuple[int, int]], float]:
        """
        seq1: array of shape (N, D)
        seq2: array of shape (M, D)
        
        Returns:
            normalized_dtw_distance: float
            warping_path: List of (idx_seq1, idx_seq2) pairs
            similarity_score: float in [0, 100]
        """
        N, D1 = seq1.shape
        M, D2 = seq2.shape
        
        if N == 0 or M == 0 or D1 != D2:
            return 1e6, [], 0.0

        # Compute pairwise distance matrix
        # dist_matrix[i, j] = ||seq1[i] - seq2[j]||_2
        diff = seq1[:, np.newaxis, :] - seq2[np.newaxis, :, :]  # (N, M, D)
        dist_matrix = np.linalg.norm(diff, axis=-1)  # (N, M)

        # Dynamic programming cost matrix
        cost = np.full((N + 1, M + 1), np.inf, dtype=np.float64)
        cost[0, 0] = 0.0

        for i in range(1, N + 1):
            for j in range(1, M + 1):
                cost[i, j] = dist_matrix[i - 1, j - 1] + min(
                    cost[i - 1, j],      # insertion
                    cost[i, j - 1],      # deletion
                    cost[i - 1, j - 1]   # match
                )

        # Backtrack optimal warping path
        i, j = N, M
        path = []
        while i > 0 and j > 0:
            path.append((i - 1, j - 1))
            step = min(
                (cost[i - 1, j - 1], 1),
                (cost[i - 1, j], 2),
                (cost[i, j - 1], 3)
            )[1]
            
            if step == 1:
                i -= 1
                j -= 1
            elif step == 2:
                i -= 1
            else:
                j -= 1

        path.reverse()
        total_cost = float(cost[N, M])
        path_length = len(path)
        normalized_distance = total_cost / max(1, path_length)

        # Normalized kinematic similarity score on [0, 100] scale
        # Tau = 0.25 calibrated on normalized feature distances
        tau = 0.28
        similarity_score = float(100.0 * np.exp(-normalized_distance / tau))
        similarity_score = round(max(0.0, min(100.0, similarity_score)), 1)

        return round(normalized_distance, 4), path, similarity_score

dtw_service = DTWService()
