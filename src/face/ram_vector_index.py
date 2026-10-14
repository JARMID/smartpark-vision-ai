"""
In-Memory Vector Search Index and Distance Calibration Engine.
Executes sub-millisecond 1:N cosine distance matching across enrolled 512-D float32 embeddings.
Decouples barrier access decisions from external database network latency.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import numpy as np


class MatchDecision(str, Enum):
    MATCH = "match"
    BORDERLINE_RESAMPLE = "borderline_resample"
    NO_MATCH = "no_match"
    BLACKLIST_HIT = "blacklist_hit"


@dataclass
class EnrolledProfile:
    person_id: str
    full_name: str
    embedding: np.ndarray  # Shape: (512,), float32, L2 normalized
    is_blacklisted: bool = False
    blacklist_reason: Optional[str] = None


@dataclass
class SearchResult:
    decision: MatchDecision
    person_id: Optional[str] = None
    full_name: Optional[str] = None
    cosine_distance: float = 1.0
    similarity_score: float = 0.0
    is_blacklisted: bool = False
    blacklist_reason: Optional[str] = None
    frames_averaged: int = 1


class RamVectorIndex:
    """
    In-memory vector similarity index using normalized inner product cosine distance.
    Calibrated specifically for vehicle driver access control.
    """

    def __init__(
        self,
        dimension: int = 512,
        match_threshold: float = 0.52,
        resample_upper_bound: float = 0.55,
    ):
        self.dimension = dimension
        self.match_threshold = match_threshold
        self.resample_upper_bound = resample_upper_bound
        self.profiles: Dict[str, EnrolledProfile] = {}
        self.id_list: List[str] = []
        self.matrix: Optional[np.ndarray] = None  # Shape (N, 512)

    def _rebuild_matrix(self):
        """Reconstruct contiguous 2D float32 array for batch matrix multiplication."""
        if not self.id_list:
            self.matrix = None
            return
        vectors = [self.profiles[pid].embedding for pid in self.id_list]
        self.matrix = np.vstack(vectors).astype(np.float32)

    def enroll(
        self,
        person_id: str,
        full_name: str,
        embedding: np.ndarray,
        is_blacklisted: bool = False,
        blacklist_reason: Optional[str] = None,
    ):
        """Enroll or update a normalized facial embedding in the in-memory index."""
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        profile = EnrolledProfile(
            person_id=person_id,
            full_name=full_name,
            embedding=emb,
            is_blacklisted=is_blacklisted,
            blacklist_reason=blacklist_reason,
        )
        self.profiles[person_id] = profile
        if person_id not in self.id_list:
            self.id_list.append(person_id)

        self._rebuild_matrix()

    def remove(self, person_id: str):
        """Remove a profile from the index."""
        if person_id in self.profiles:
            del self.profiles[person_id]
            self.id_list.remove(person_id)
            self._rebuild_matrix()

    def search(self, query_vector: np.ndarray) -> SearchResult:
        """
        Execute 1:N cosine distance search across all enrolled profiles in RAM.
        Returns immediate decision: MATCH, BORDERLINE_RESAMPLE, NO_MATCH, or BLACKLIST_HIT.
        """
        if self.matrix is None or len(self.id_list) == 0:
            return SearchResult(decision=MatchDecision.NO_MATCH)

        q = np.asarray(query_vector, dtype=np.float32).flatten()
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        # Batch inner product: Shape (N,)
        # Since both matrix and query are L2-normalized, dot product equals cosine similarity
        similarities = np.dot(self.matrix, q)
        distances = 1.0 - similarities

        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        best_similarity = float(similarities[best_idx])
        matched_id = self.id_list[best_idx]
        profile = self.profiles[matched_id]

        # Check blacklist priority first
        if profile.is_blacklisted and best_distance <= self.resample_upper_bound:
            return SearchResult(
                decision=MatchDecision.BLACKLIST_HIT,
                person_id=profile.person_id,
                full_name=profile.full_name,
                cosine_distance=best_distance,
                similarity_score=best_similarity,
                is_blacklisted=True,
                blacklist_reason=profile.blacklist_reason,
                frames_averaged=1,
            )

        # Clear match zone
        if best_distance <= self.match_threshold:
            return SearchResult(
                decision=MatchDecision.MATCH,
                person_id=profile.person_id,
                full_name=profile.full_name,
                cosine_distance=best_distance,
                similarity_score=best_similarity,
                is_blacklisted=False,
                frames_averaged=1,
            )

        # Borderline dead zone (0.52 < distance <= 0.55) -> triggers multi-frame resample
        if best_distance <= self.resample_upper_bound:
            return SearchResult(
                decision=MatchDecision.BORDERLINE_RESAMPLE,
                person_id=profile.person_id,
                full_name=profile.full_name,
                cosine_distance=best_distance,
                similarity_score=best_similarity,
                is_blacklisted=False,
                frames_averaged=1,
            )

        # Outside all thresholds
        return SearchResult(
            decision=MatchDecision.NO_MATCH,
            person_id=profile.person_id,
            full_name=profile.full_name,
            cosine_distance=best_distance,
            similarity_score=best_similarity,
            frames_averaged=1,
        )

    def search_multi_frame(self, frame_vectors: List[np.ndarray]) -> SearchResult:
        """
        Average embeddings across multiple camera frames temporally before decision.
        Used when single-frame distance falls into the borderline band (0.52 to 0.55).
        """
        if not frame_vectors:
            return SearchResult(decision=MatchDecision.NO_MATCH)

        # Sum vectors and re-normalize to compute the centroid
        accumulated = np.zeros(self.dimension, dtype=np.float32)
        valid_frames = 0
        for vec in frame_vectors:
            v = np.asarray(vec, dtype=np.float32).flatten()
            norm = np.linalg.norm(v)
            if norm > 0:
                accumulated += (v / norm)
                valid_frames += 1

        if valid_frames == 0:
            return SearchResult(decision=MatchDecision.NO_MATCH)

        centroid = accumulated / np.linalg.norm(accumulated)

        # Execute search on the temporally smoothed centroid vector
        raw_res = self.search(centroid)
        raw_res.frames_averaged = valid_frames

        # If after multi-frame averaging it remains in borderline band, map to NO_MATCH (guard review)
        if raw_res.decision == MatchDecision.BORDERLINE_RESAMPLE:
            raw_res.decision = MatchDecision.NO_MATCH

        return raw_res
