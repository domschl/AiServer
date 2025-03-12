import logging
import asyncio
from aiohttp import web
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import torch
from typing import cast

# For translation example:
from transformers import T5ForConditionalGeneration, T5Tokenizer

class AiServer:
    def __init__(self, port:int=8080, num_workers:int=2):
        self.log: logging.Logger = logging.getLogger("AiServer")
        self.log.setLevel(logging.INFO)  # All important compliance info is logged!
        self.port: int = port
        self.num_workers: int = num_workers
        # ----------- Start specific for Translation example
        model_name = 'jbochi/madlad400-3b-mt'
        # Since thread-safety of those is very dubious at best, we have to create N copies of model and tokenizer!
        self.thread_id_map:list[int] = [0 for _ in range(self.num_workers)]
        self.log.info("Instantiating models...")
        self.models: list[T5ForConditionalGeneration] = [T5ForConditionalGeneration.from_pretrained(model_name, device_map="auto") for _ in range(self.num_workers)]
        self.log.info("Instantiating tokenizers...")
        self.tokenizers: list[T5Tokenizer] = [T5Tokenizer.from_pretrained(model_name) for _ in range(self.num_workers)]
        self.log.info("Models and tokenizers loaded.")
        # ----------- End specific for translation example
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.num_workers)  # Increased worker count
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.app: web.Application = web.Application()
        _ = self.app.router.add_post('/task', self.handle_post)
        self.log.info("AiServer active")

    # For translation example:
    def get_engine(self, thread_id: int) -> tuple[T5Tokenizer, T5ForConditionalGeneration] | None:
        empty_id: int = -1
        for ind, id in enumerate(self.thread_id_map):
            if id == thread_id:
                return (self.tokenizers[ind], self.models[ind])
            if id == 0:
                empty_id = ind
        if empty_id == -1:
            self.log.error(f"Cannot identify engine for thread_id {thread_id}")
            return None
        self.thread_id_map[empty_id] = thread_id
        return (self.tokenizers[empty_id], self.models[empty_id])

    def ai_worker(self, job_desc: dict[str, str|int|float]):
        thread_id = threading.get_ident()
        self.log.info(f"Worker {thread_id} starting job...")
        # ============= Insert AI stuff here =================
        eng = self.get_engine(thread_id)
        if eng is None:
            result = {
                "name": job_desc['name'],
                "your_important_id": job_desc['important_id'],
                "duration": time.time() - cast(float, job_desc['start_time']),
                "thread_id": thread_id,
                "text": job_desc['text'],
                "language_code": job_desc['NONE'],
                "translation": "**FAILURE**",
                "result": "Error: No engine available!"
            }
            return result, "ERROR"
        tokenizer = eng[0]
        model = eng[1]
        text = f"<2{job_desc['language_code']}> {job_desc['text']}"
        input_ids: torch.Tensor = tokenizer(text, return_tensors="pt").input_ids.to(model.device)
        outputs = model.generate(input_ids=input_ids)
        translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # ====================================================
        result = {
            "name": job_desc['name'],
            "your_important_id": job_desc['important_id'],
            "duration": time.time() - cast(float, job_desc['start_time']),
            "thread_id": thread_id,
            "text": job_desc['text'],
            "language_code": job_desc['language_code'],
            "translation": translation,
            "result": "OK"
        }
        self.log.info(f"Worker {thread_id} finished.")
        return result, "OK"

    async def handle_post(self, request: web.Request) -> web.Response:
        job_desc: dict[str, str|int|float] = cast(dict[str, str|int|float], await request.json())
        job_desc["name"] = "Hotzenplot-task"
        
        result, status = await self.loop.run_in_executor(
            self.executor, 
            self.ai_worker,
            job_desc
        )

        return web.json_response({
            "status": status,
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

