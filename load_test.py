import aiohttp
import asyncio
import time

url = 'http://localhost:8080/task'

job_desc: dict[str, str|int|float] = {
    "name": "Gartenarbeit tut not!",
    "important_id": 0,
    "start_time": 0,
    "language_code": "de",
    "text": ""
}

concurrent_requests:int = 5
job_id = 0

test_data = [
    "Good morning, today is an exceptionally nice day!",
    "Guten morgen, heute ist wirkich ein besonders schöner Tag!",
]
target_languages = ["de", "en", "fr", "it", "es", "fi"]

async def send_post(session:aiohttp.client.ClientSession, url:str, job_desc:dict[str, str|int|float]):
    global job_id
    job_desc["start_time"] = time.time()
    job_desc["important_id"] = job_id
    job_desc["language_code"] = target_languages[job_id % len(target_languages)]
    job_desc["text"] = test_data[job_id % len(test_data)]
    job_id += 1

    async with session.post(url, json=job_desc) as response:
        response_json: dict[str, dict[str, str | dict[str, str|int|float]]] = await response.json()
        status  = response_json['status']
        result = response_json['result']
        print(f"{status} {result['duration']:.2f} sec: {result['text']} -> {result['language_code']}: {result['translation']}")

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

