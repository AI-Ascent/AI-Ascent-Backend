from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.permissions import IsSuperUser
from django.utils import timezone
from datetime import timedelta
from db.models.skill import InterestedSkill
from db.models.feedback import NegativeFeedback
import numpy as np

SIM_THRESHOLD = 0.85

class GlobalSkillTrendsView(APIView):
	"""
	On-demand global clustering of similar skill recommendations and popularity counts (distinct users).

		POST body (all optional):
			- timeframe_days (int, default 7; max 60)
			- top_n (int, default 10)

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

		timeframe_days, err = parse_int("timeframe_days", 7)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
		top_n, err = parse_int("top_n", 10)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

		# Clamp ranges
		timeframe_days = max(1, min(timeframe_days, 60))  # max ~2 months
		top_n = max(1, min(top_n, 200))

		since = timezone.now() - timedelta(days=timeframe_days)

		# Always fetch rows from database for fresh computation
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
				"stats": {"rows_processed": 0, "total_rows": 0}
			}, status=status.HTTP_200_OK)

		items = list(qs)

		# Prepare arrays for clustering directly from items
		vectors = []
		titles = []
		users = []
		for it in items:
			v = getattr(it, "title_vector", None)
			if v is None:
				continue
			try:
				vec_list = v.tolist() if hasattr(v, "tolist") else list(v)
			except Exception:
				# Fallback: skip if not iterable
				continue
			vectors.append(np.asarray(vec_list, dtype=np.float32))
			titles.append(it.skill_title)
			users.append(it.user_id)

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
			if best_sim >= SIM_THRESHOLD and best_idx >= 0:
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


class GlobalNegativeFeedbackTrendsView(APIView):
	"""
	On-demand global clustering of similar negative feedback insights and popularity counts (distinct users).

		POST body (all optional):
			- timeframe_days (int, default 7; max 60)
			- top_n (int, default 10)

		Returns: Top clusters sorted by distinct user popularity, with a representative feedback and a few samples.
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

		timeframe_days, err = parse_int("timeframe_days", 7)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
		top_n, err = parse_int("top_n", 10)
		if err:
			return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

		# Clamp ranges
		timeframe_days = max(1, min(timeframe_days, 60))  # max ~2 months
		top_n = max(1, min(top_n, 200))

		since = timezone.now() - timedelta(days=timeframe_days)

		# Always fetch rows from database for fresh computation
		qs = (
			NegativeFeedback.objects
			.filter(created_at__gte=since, feedback_vector__isnull=False)
			.only("id", "user", "feedback_text", "feedback_vector")
			.order_by("id")
		)
		total = qs.count()
		if total == 0:
			return Response({
				"computed_at": timezone.now(),
				"timeframe_days": timeframe_days,
				"clusters": [],
				"stats": {"rows_processed": 0, "total_rows": 0}
			}, status=status.HTTP_200_OK)

		items = list(qs)

		# Prepare arrays for clustering directly from items
		vectors = []
		feedbacks = []
		users = []
		for it in items:
			v = getattr(it, "feedback_vector", None)
			if v is None:
				continue
			try:
				vec_list = v.tolist() if hasattr(v, "tolist") else list(v)
			except Exception:
				# Fallback: skip if not iterable
				continue
			vectors.append(np.asarray(vec_list, dtype=np.float32))
			feedbacks.append(it.feedback_text)
			users.append(it.user_id)

		if not vectors:
			return Response({
				"computed_at": timezone.now(),
				"timeframe_days": timeframe_days,
				"clusters": [],
				"stats": {"rows_processed": 0, "total_rows": total}
			}, status=status.HTTP_200_OK)

		# Greedy centroid clustering with cosine similarity
		clusters = []  # list of dict: {centroid: np.array, users: set, feedbacks: list}

		def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
			# robust cosine for np arrays
			na = np.linalg.norm(a)
			nb = np.linalg.norm(b)
			if na == 0 or nb == 0:
				return 0.0
			return float(np.dot(a, b) / (na * nb))

		for vec, feedback, uid in zip(vectors, feedbacks, users):
			best_idx = -1
			best_sim = -1.0
			for idx, cl in enumerate(clusters):
				sim = cosine_sim(vec, cl["centroid"])  # compare to centroid
				if sim > best_sim:
					best_sim = sim
					best_idx = idx
			if best_sim >= SIM_THRESHOLD and best_idx >= 0:
				cl = clusters[best_idx]
				cl["members"].append((uid, feedback, vec))
				cl["users"].add(uid)
				# Update centroid (incremental mean)
				n = len(cl["members"])
				cl["centroid"] = cl["centroid"] + (vec - cl["centroid"]) / n
			else:
				clusters.append({
					"centroid": vec.copy(),
					"members": [(uid, feedback, vec)],
					"users": {uid},
				})

		# Prepare results
		result = []
		for cl in clusters:
			user_count = len(cl["users"])
			# Representative feedback: nearest member to centroid
			best_feedback = None
			best_sim = -1.0
			for uid, feedback, vec in cl["members"]:
				sim = cosine_sim(vec, cl["centroid"])
				if sim > best_sim:
					best_sim = sim
					best_feedback = feedback
			sample_feedbacks = [f for _, f, _ in cl["members"][:3]]
			result.append({
				"representative_feedback": best_feedback,
				"popularity_users": user_count,
				"members_count": len(cl["members"]),
				"sample_feedbacks": sample_feedbacks,
			})

		# Sort by popularity desc and trim to top_n
		result.sort(key=lambda x: x["popularity_users"], reverse=True)
		result = result[:top_n]

		return Response({
			"computed_at": timezone.now(),
			"timeframe_days": timeframe_days,
			"clusters": result,
		}, status=status.HTTP_200_OK)

