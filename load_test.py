import aiohttp
import asyncio
import time

url = 'http://localhost:8080/task'

job_desc: dict[str, str|int|float] = {
    "name": "Gartenarbeit tut not!",
    "important_id": 0,
    "start_time": 0
}

concurrent_requests:int = 20
job_id = 0

async def send_post(session:aiohttp.client.ClientSession, url:str, job_desc:dict[str, str|int|float]):
    global job_id
    job_desc["start_time"] = time.time()
    job_desc["important_id"] = job_id
    job_id += 1

    async with session.post(url, json=job_desc) as response:
        response_json: dict[str, str|int] = await response.json()
        print(response_json)

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            job_desc['important_id']
            tasks = [send_post(session, url, job_desc) for _ in range(concurrent_requests)]
            _ = await asyncio.gather(*tasks)
            await asyncio.sleep(0.1)  # 100 ms

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

