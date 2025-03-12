import logging
import asyncio
from aiohttp import web
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import cast

class AiServer:
    def __init__(self, port:int=8080, num_workers:int=10):
        self.log: logging.Logger = logging.getLogger("AiServerComplianceWurschtelLogger")
        self.log.setLevel(logging.INFO)  # All important compliance info is logged!
        self.port: int = port
        self.num_workers: int = num_workers
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.num_workers)  # Increased worker count
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.app: web.Application = web.Application()
        _ = self.app.router.add_post('/task', self.handle_post)
        self.log.info("AiServer active")

    def ai_worker(self, job_desc: dict[str, str|int|float]):
        thread_id = threading.get_ident()
        self.log.info(f"Worker {thread_id} starting to do something.")
        # ============= Insert AI stuff here =================
        time.sleep(3)  # Simulate important AI work
        # ====================================================
        result = {
            "name": job_desc['name'],
            "your_important_id": job_desc['important_id'],
            "duration": time.time() - cast(float, job_desc['start_time']),
            "thread_id": thread_id,
            "result": "We did a lot of things, slowly"
        }
        self.log.info(f"Worker {thread_id} finished to do something.")
        return result

    async def handle_post(self, request: web.Request) -> web.Response:
        self.log.info("Received POST at /task")
        job_desc: dict[str, str|int|float] = cast(dict[str, str|int|float], await request.json())
        job_desc["name"] = "Hotzenplot-task"
        
        result = await self.loop.run_in_executor(
            self.executor, 
            self.ai_worker,
            job_desc
        )

        return web.json_response({
            "status": "success",
            "result": result,
        })

async def main():
    ai_server = AiServer()
    return ai_server.app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        web.run_app(main())
    except KeyboardInterrupt:
        pass

