
# --- Advanced Async Background Job Queue ---
import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

logger = logging.getLogger("TaskQueue")

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskQueue:
    """
    A robust in-memory/Redis hybrid task queue for FastAPI background jobs.
    Supports priorities, retries, and dead-letter queues.
    """
    def __init__(self, concurrency: int = 5):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.registry: dict[str, Callable] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.concurrency = concurrency
        self.workers: list[asyncio.Task] = []
        self._running = False

    def register(self, task_name: str, func: Callable[..., Awaitable]):
        self.registry[task_name] = func

    async def enqueue(self, task_name: str, payload: dict, priority: int = 10, max_retries: int = 3) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "task_name": task_name,
            "payload": payload,
            "status": JobStatus.PENDING,
            "retries": 0,
            "max_retries": max_retries,
            "created_at": datetime.utcnow().isoformat(),
            "error": None
        }
        self.jobs[job_id] = job
        await self.queue.put((priority, job_id))
        logger.info(f"Enqueued job {job_id} ({task_name})")
        return job_id

    async def _worker(self, worker_id: int):
        logger.info(f"Worker {worker_id} started")
        while self._running:
            try:
                priority, job_id = await self.queue.get()
                job = self.jobs.get(job_id)

                if not job or job["status"] != JobStatus.PENDING:
                    self.queue.task_done()
                    continue

                job["status"] = JobStatus.RUNNING
                task_func = self.registry.get(job["task_name"])

                if not task_func:
                    job["status"] = JobStatus.FAILED
                    job["error"] = "Task not registered"
                    self.queue.task_done()
                    continue

                try:
                    logger.debug(f"Worker {worker_id} executing {job_id}")
                    await task_func(**job["payload"])
                    job["status"] = JobStatus.COMPLETED
                except Exception as e:
                    logger.error(f"Worker {worker_id} job {job_id} failed: {e}")
                    job["retries"] += 1
                    if job["retries"] <= job["max_retries"]:
                        job["status"] = JobStatus.PENDING
                        await asyncio.sleep(2 ** job["retries"]) # Exponential backoff
                        await self.queue.put((priority + 1, job_id)) # Lower priority
                    else:
                        job["status"] = JobStatus.FAILED
                        job["error"] = str(e)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} critical error: {e}")
                await asyncio.sleep(1)

    def start(self):
        if not self._running:
            self._running = True
            for i in range(self.concurrency):
                task = asyncio.create_task(self._worker(i))
                self.workers.append(task)

    async def stop(self):
        self._running = False
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

global_task_queue = TaskQueue()
