from redis import Redis
from rq import Queue
from rq.registry import FailedJobRegistry

class TaskManager:
    def __init__(self):
        self.redis = Redis(host='redis', port=6379)
        self.queue = Queue(connection=self.redis)
        self.registry = FailedJobRegistry(queue=self.queue)
        
    def enqueue_task(self, func, *args):
        return self.queue.enqueue(func, *args)
    
    def retry_failed(self):
        for job_id in self.registry.get_job_ids():
            job = self.queue.fetch_job(job_id)
            self.queue.enqueue(job.func, *job.args, **job.kwargs)
            self.registry.remove(job)
    
    def monitor_queue(self):
        return {
            "pending": self.queue.count,
            "failed": len(self.registry),
            "workers": len(self.queue.get_worker_ids())
        } 