import concurrent
import concurrent.futures
import os
import random
from typing import List

import jsonlines
from dotenv import load_dotenv
from langchain.llms import OpenAIChat
from loguru import logger
from tqdm import tqdm

load_dotenv()

class Scraper:
    def __init__(self, openai_api_keys: List[str]) -> None:
        self.openai_api_keys = openai_api_keys

    def get_responses(
        self, 
        all_prompts: List[dict], 
        i: int, 
        shard_size: int,
        model_settings: dict = {"max_tokens": -1},
        output_path: str = '',
        source: str = ''
    ):
        prompts = all_prompts[i : i + shard_size]
        model = OpenAIChat(
            model_name="gpt-3.5-turbo",
            openai_api_key=self.openai_api_keys[random.randint(0, len(self.openai_api_keys) - 1)],
            model_kwargs={"max_tokens": -1},
        )
        for prompt in tqdm(prompts):
            output = model(prompt)
            with jsonlines.open(os.path.join(output_path, "output.jsonl"), mode="a") as writer:
                try:
                    json_data = {"prompt": prompt, "response": output, "model_settings": model_settings, "source": 'laion/oib'}
                    writer.write(json_data)
                except (KeyboardInterrupt, ValueError, IndexError):
                    logger.warning("Something went wrong with this prompt! Skipping to next one")
                    with jsonlines.open(os.path.join(output_path, "fails.jsonl"), mode="a") as writer:
                        writer.write(prompt)

    def scrape(self, 
        all_prompts: List[dict],
        num_workers: int = 10,
        shard_size: int = 200,
        output_path: str = '',
        source: str = ''
    ):
        logger.info("Generating Pairs")

        progress = tqdm(total=len(all_prompts) // shard_size)
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(self.get_responses, i=i, all_prompts=all_prompts, shard_size=shard_size, output_path=output_path, source=source) for i in range(0, len(all_prompts), shard_size)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.exception(f"Error processing prompt: {e}")

                progress.update(1)


if __name__ == "__main__":
    scraper = Scraper(openai_api_keys=[os.environ[f"OPENAI_API_KEY{i}"] for i in range(6, 21)])

    all_data = []

    with jsonlines.open("input_prompts/all_data.jsonl", mode="r") as reader:
        for datum in reader:
            # datum = datum.replace("\n", "")
            print(datum)
            all_data.append(datum)


    scraper.scrape(all_prompts=all_data[0:10])

