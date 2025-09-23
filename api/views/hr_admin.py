from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.permissions import IsSuperUser
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from db.models.skill import InterestedSkill
import numpy as np


class GlobalSkillTrendsView(APIView):
	"""
	On-demand global clustering of similar skill recommendations and popularity counts (distinct users).

		POST body (all optional):
			- timeframe_days (int, default 7; max 60)
			- top_n (int, default 50)
			- sim_threshold (float, default 0.85)

		Caching (per-step):
			- We cache only the fetched rows (user_id, title, vector) for a short TTL per timeframe.
			- We DO NOT cache the final clustered output so it always reflects thresholds.

		Returns: Top clusters sorted by distinct user popularity, with a representative title and a few samples.
	"""
	permission_classes = [IsSuperUser]

	def post(self, request):
		# Parse parameters individually to return descriptive errors
		def parse_int(name, default):
			raw = request.data.get(name, default)
			try:
				return int(raw), None
			except Exception:
				return None, f"{name} must be an integer"

		def parse_float(name, default):
			raw = request.data.get(name, default)
			try:
				return float(raw), None
			except Exception:
				return None, f"{name} must be a number"

		timeframe_days, err = parse_int("timeframe_days", 7)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
		top_n, err = parse_int("top_n", 50)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
		sim_threshold, err = parse_float("sim_threshold", 0.85)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

		# Clamp ranges
		timeframe_days = max(1, min(timeframe_days, 60))  # max ~2 months
		top_n = max(1, min(top_n, 200))
		sim_threshold = max(0.0, min(sim_threshold, 0.9999))

		since = timezone.now() - timedelta(days=timeframe_days)

		# Step cache: fetch rows (user_id, title, vector) for timeframe only
		rows_cache_key = f"gst:rows:{timeframe_days}"
		cached_rows = cache.get(rows_cache_key)

		if cached_rows is None:
			qs = (
				InterestedSkill.objects
				.filter(set_at__gte=since, title_vector__isnull=False)
				.only("id", "user", "skill_title", "title_vector")
				.order_by("id")
			)
			total = qs.count()
			if total == 0:
				return Response({
					"computed_at": timezone.now(),
					"timeframe_days": timeframe_days,
					"clusters": [],
					"stats": {"rows_processed": 0, "total_rows": 0, "cache": "miss"}
				}, status=status.HTTP_200_OK)

			items = list(qs)
			rows_processed = len(items)

			# Serialize minimal rows for cache (avoid numpy truthiness; convert explicitly)
			cached_rows = []
			for it in items:
				v = getattr(it, "title_vector", None)
				if v is None:
					continue
				try:
					vec_list = v.tolist() if hasattr(v, "tolist") else list(v)
				except Exception:
					# Fallback: skip if not iterable
					continue
				cached_rows.append({"u": it.user_id, "t": it.skill_title, "v": vec_list})
			# Cache for a short TTL so repeated admin calls are faster
			cache.set(rows_cache_key, {"rows": cached_rows, "total": total}, timeout=300)
		else:
			total = cached_rows.get("total", len(cached_rows.get("rows", [])))
			cached_rows = cached_rows.get("rows", [])

		if not cached_rows:
			return Response({
				"computed_at": timezone.now(),
				"timeframe_days": timeframe_days,
				"clusters": [],
				"stats": {"rows_processed": 0, "total_rows": total, "cache": "hit-empty"}
			}, status=status.HTTP_200_OK)

		# Prepare arrays for clustering
		vectors = [np.asarray(row["v"], dtype=np.float32) for row in cached_rows]
		titles = [row["t"] for row in cached_rows]
		users = [row["u"] for row in cached_rows]

		if not vectors:
			return Response({
				"computed_at": timezone.now(),
				"timeframe_days": timeframe_days,
				"clusters": [],
				"stats": {"rows_processed": 0, "total_rows": total}
			}, status=status.HTTP_200_OK)

		# Greedy centroid clustering with cosine similarity
		clusters = []  # list of dict: {centroid: np.array, users: set, titles: list}

		def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
			# robust cosine for np arrays
			na = np.linalg.norm(a)
			nb = np.linalg.norm(b)
			if na == 0 or nb == 0:
				return 0.0
			return float(np.dot(a, b) / (na * nb))

		for vec, title, uid in zip(vectors, titles, users):
			best_idx = -1
			best_sim = -1.0
			for idx, cl in enumerate(clusters):
				sim = cosine_sim(vec, cl["centroid"])  # compare to centroid
				if sim > best_sim:
					best_sim = sim
					best_idx = idx
			if best_sim >= sim_threshold and best_idx >= 0:
				cl = clusters[best_idx]
				cl["members"].append((uid, title, vec))
				cl["users"].add(uid)
				# Update centroid (incremental mean)
				n = len(cl["members"])
				cl["centroid"] = cl["centroid"] + (vec - cl["centroid"]) / n
			else:
				clusters.append({
					"centroid": vec.copy(),
					"members": [(uid, title, vec)],
					"users": {uid},
				})

		# Prepare results
		result = []
		for cl in clusters:
			user_count = len(cl["users"])
			# Representative title: nearest member to centroid
			best_title = None
			best_sim = -1.0
			for uid, title, vec in cl["members"]:
				sim = cosine_sim(vec, cl["centroid"])
				if sim > best_sim:
					best_sim = sim
					best_title = title
			sample_titles = [t for _, t, _ in cl["members"][:3]]
			result.append({
				"representative_title": best_title,
				"popularity_users": user_count,
				"members_count": len(cl["members"]),
				"sample_titles": sample_titles,
			})

		# Sort by popularity desc and trim to top_n
		result.sort(key=lambda x: x["popularity_users"], reverse=True)
		result = result[:top_n]

		return Response({
			"computed_at": timezone.now(),
			"timeframe_days": timeframe_days,
			"clusters": result,
		}, status=status.HTTP_200_OK)

