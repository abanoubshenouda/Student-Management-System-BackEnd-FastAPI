import logging
import time
from collections import defaultdict, deque
from typing import Optional


request_counts = defaultdict(int)
response_times = defaultdict(list)
recent_requests = deque(maxlen=50)
recent_errors = deque(maxlen=20)
started_at = time.time()


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


logger = logging.getLogger("student_management")


def record_request(method: str, path: str, status_code: int, duration_ms: float):
    key = f"{method} {path}"
    request_counts[key] += 1
    response_times[key].append(duration_ms)

    entry = {
        "method": method,
        "endpoint": path,
        "status_code": status_code,
        "response_time_ms": round(duration_ms, 2),
    }
    recent_requests.appendleft(entry)

    log_level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(log_level, "api_request %s", entry)

    if status_code >= 400:
        recent_errors.appendleft(entry)


def log_auth_event(event: str, username: Optional[str], success: bool):
    logger.info("auth_event %s", {
        "event": event,
        "username": username,
        "success": success,
    })


def log_db_event(action: str, entity: str, entity_id=None, username: Optional[str] = None):
    logger.info("db_event %s", {
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "username": username,
    })


def log_error_event(message: str, details=None):
    logger.error("error_event %s", {
        "message": message,
        "details": details,
    })


def get_metrics():
    endpoints = []

    for endpoint, count in request_counts.items():
        times = response_times.get(endpoint, [])
        average = sum(times) / len(times) if times else 0
        endpoints.append({
            "endpoint": endpoint,
            "request_count": count,
            "average_response_time_ms": round(average, 2),
        })

    return {
        "uptime_seconds": round(time.time() - started_at, 2),
        "total_requests": sum(request_counts.values()),
        "total_errors": len(recent_errors),
        "error_rate": round(len(recent_errors) / sum(request_counts.values()), 4) if request_counts else 0,
        "endpoints": endpoints,
        "recent_requests": list(recent_requests),
        "recent_errors": list(recent_errors),
    }
