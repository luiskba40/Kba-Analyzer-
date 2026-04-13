"""
routes/operations.py
--------------------
Background-job / queue management endpoints (admin only).

POST /operations/jobs          — enqueue a new background job
GET  /operations/jobs          — list jobs with optional status filter
GET  /operations/jobs/<id>     — get a specific job
GET  /operations/jobs/dead     — list dead-letter jobs
"""

from flask import Blueprint, request, jsonify

from services.queue_service import enqueue_job
from models.job import Job
from utils.decorators import admin_required

ops_bp = Blueprint("operations", __name__)


@ops_bp.route("/jobs", methods=["POST"])
@admin_required
def create_job():
    data = request.get_json(silent=True) or {}
    job_type = data.get("job_type", "").strip()
    if not job_type:
        return jsonify({"error": "job_type is required"}), 400

    job = enqueue_job(
        job_type=job_type,
        payload=data.get("payload"),
        max_retries=data.get("max_retries"),
    )
    return jsonify({"job": job.to_dict()}), 202


@ops_bp.route("/jobs", methods=["GET"])
@admin_required
def list_jobs():
    status_filter = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Job.query.order_by(Job.enqueued_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "jobs": [j.to_dict() for j in paginated.items],
            "total": paginated.total,
            "page": page,
            "pages": paginated.pages,
        }
    ), 200


@ops_bp.route("/jobs/<job_id>", methods=["GET"])
@admin_required
def get_job(job_id):
    job = Job.query.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job": job.to_dict()}), 200


@ops_bp.route("/dead-jobs", methods=["GET"])
@admin_required
def list_dead_jobs():
    jobs = Job.query.filter_by(status="dead").order_by(Job.finished_at.desc()).all()
    return jsonify({"dead_jobs": [j.to_dict() for j in jobs]}), 200
