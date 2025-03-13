import logging
import signal
import asyncio
from aiohttp import web
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import torch
from typing import cast
from types import FrameType


# For translation example:
from transformers import T5ForConditionalGeneration, T5Tokenizer  # pyright: ignore[reportMissingTypeStubs]

class AiServer:
    def __init__(self, port:int=8080, num_workers:int=4, device:str="auto"):
        # device: "auto" (fastest hardware), "cuda" (Nvidia), "mps" (Mac Metal), "cpu"
        self.log: logging.Logger = logging.getLogger("AiServer")
        self.log.setLevel(logging.INFO)  # All important compliance info is logged!
        self.port: int = port
        self.num_workers: int = num_workers
        # ----------- Start specific for Translation example
        self.lock: threading.Lock = threading.Lock()  # Create a lock for thread-safe access
        model_name:str = 'jbochi/madlad400-3b-mt'
        # Since thread-safety of those is very dubious at best, we have to create N copies of model and tokenizer!
        self.thread_id_map:list[int] = []
        self.models: list[T5ForConditionalGeneration] = []
        self.tokenizers: list[T5Tokenizer] = []
        self.log.info("Instantiating models and tokenizers...")
        for i in range(self.num_workers):
            print(f"\rLoading {i+1}/{self.num_workers}...", end="", flush=True)
            self.thread_id_map.append(0)
            self.models.append(T5ForConditionalGeneration.from_pretrained(model_name, device_map=device)) # pyright: ignore[reportUnknownMemberType]
            self.tokenizers.append(T5Tokenizer.from_pretrained(model_name))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        print("\r", end="", flush=True)
        self.log.info("Models and tokenizers loaded.")
        # ----------- End specific for translation example
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.num_workers)  # Increased worker count
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.app: web.Application = web.Application()
        _ = self.app.router.add_post('/task', self.handle_post)
        self.log.info(f"AiServer active, using device {device}")

    # For translation example:
    def get_engine(self, thread_id: int) -> tuple[T5Tokenizer, T5ForConditionalGeneration] | None:
        with self.lock:  # Acquire the lock before accessing shared resources
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
        input_ret = tokenizer(text=text, return_tensors="pt")  # pyright: ignore[reportArgumentType]
        input_ids: torch.Tensor = cast(torch.Tensor, input_ret.input_ids.to(model.device))  # pyright: ignore[reportUnknownMemberType]
        outputs = model.generate(input_ids=input_ids)  # pyright: ignore[reportUnknownMemberType]
        translation = tokenizer.decode(outputs[0], skip_special_tokens=True)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
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
    ai_server = AiServer(num_workers=2, device="auto")
    return ai_server.app

def handle_sighup(_signum: int, _frame: FrameType | None) -> None:
    logging.info("Received SIGHUP signal")
    asyncio.get_event_loop().stop()

if __name__ == '__main__':
    _ = signal.signal(signal.SIGHUP, handle_sighup)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    try:
        web.run_app(main())
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        logging.info("Cancelled")
        pass
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
    finally:
        pass
    logging.info("Shutting down server...")

