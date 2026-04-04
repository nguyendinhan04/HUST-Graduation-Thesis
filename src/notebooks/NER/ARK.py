# Import libraries related to asynchronous programming for handling asynchronous tasks. Coroutines are a core concept in asynchronous programming.
import asyncio
# Import system-related libraries, which can be used to interact with the Python interpreter and the system, such as standard error output.
import sys
# Import operating system-related libraries for accessing the functions of the operating system, such as reading environment variables.
import os
import json
import aiofiles
# Import the date and time processing library for recording and calculating the execution time of the program.
from datetime import datetime
# Import the asynchronous ModelArk client library of BytePlus for asynchronous communication with the ModelArk service of BytePlus.
from byteplussdkarkruntime import AsyncArk
import dotenv


async def file_writer(queue, filename, batch_size=50):
    async with aiofiles.open(filename, mode='a', encoding='utf-8') as f:
        batch = [] # Danh sách tạm để gom dữ liệu
        
        while True:
            result = await queue.get()
            
            # Nếu nhận được tín hiệu kết thúc (None)
            if result is None:
                # Ghi nốt những phần tử còn sót lại trong batch (nếu có) trước khi thoát
                if batch:
                    await f.writelines(batch)
                queue.task_done()
                break
                
            # Thêm kết quả đã chuyển thành chuỗi JSON vào batch
            batch.append(json.dumps(result, ensure_ascii=False) + '\n')
            queue.task_done()
            
            # Nếu batch đã đủ số lượng, tiến hành ghi xuống ổ cứng
            if len(batch) >= batch_size:
                await f.writelines(batch) # Ghi nhiều dòng cùng lúc
                batch.clear() # Làm trống batch để gom đợt mới




async def worker(
    # The unique identifier of the asyncio task coroutine, used to distinguish different worker coroutines.
    worker_id: int,
    # The asynchronous ModelArk client instance, used to call the batch chat completion interface to handle requests.
    client: AsyncArk,
    # The queue of requests to be processed, storing the requests that need to be handled.
    requests: asyncio.Queue[dict],

    write_request_queue: asyncio.Queue[dict]
):
    """
    An asynchronous coroutine function responsible for getting requests from the queue and processing them.

    :param worker_id: The unique identifier of the coroutine, used to distinguish different coroutines in the logs.
    :param client: The asynchronous ModelArk client instance, through which the service interface is called to process requests.
    :param requests: The queue of requests to be processed, storing the information of the requests to be processed.
    :param write_request_queue: The queue for storing requests to be written to the file.
    """
    # Print the startup information of the coroutine.
    print(f"Worker {worker_id} is starting.")
    while True:
        # Get a request from the queue. If the queue is empty, it will block and wait.
        # The await keyword here is used to pause the execution of the coroutine and wait for an element to be available in the queue.
        request = await requests.get()
        try:
            # Call the batch chat completion interface of the client to process the request, using the unpacking operation to pass the request dictionary as a parameter.
            # Also use the await keyword to pause the coroutine and wait for the interface call to complete.
            
            # print(f"Worker {worker_id} is processing request: {request["model_request"]}")
            model_request = request["model_request"]
            # completion = await client.batch_chat.completions.create(**model_request)
            completion = await client.chat.completions.create(

                # model=model_request["model"],
                model= "seed-2-0-lite-260228",
                messages=model_request["messages"]
            )
            
            # Print the processing result.
            # print(completion)


            #tat
            await write_request_queue.put({"content": completion.choices[0].message.content, "id": request["id"]})
        except Exception as e:
            # If an exception occurs during the processing of the request, print the error message to the standard error output.
            print(e, file=sys.stderr)
        finally:
            # Mark that the request has been processed and notify the queue that the task is completed.
            requests.task_done()

async def main():
    """
    The main function is responsible for initializing the client, generating requests, starting coroutines, and monitoring the completion of tasks.

    Coroutines are used to achieve concurrent processing of requests, avoiding the relatively large overhead brought by using threads.
    Multiple coroutines can execute concurrently in a single thread, improving the performance of the program.
    """
    dotenv.load_dotenv("./.env")
    import time

    OUTPUT_FILE = f"../data/ner_labeled_results_{time.time()}.jsonl"
    BATCH_WRITE_SIZE = 20

    with open(OUTPUT_FILE, mode='w', encoding='utf-8') as f:
        pass

    import pandas as pd

    job_df = pd.read_csv("../data/detail_jobs_202603291653.csv")
    job_df.info()
    # job_df_first100 = job_df.head(300)
    # job_jb_df = job_df_first100[["id","desc_mota", "desc_yeucau"]]


    # get next 300 rows from job_df
    job_jb_df = job_df[300:600][["id","desc_mota", "desc_yeucau"]]

    # get next 300 rows from job_df
    # job_jb_df = job_df[600:900][["id","desc_mota", "desc_yeucau"]]


    # job_jb_df = job_df[["id","desc_mota", "desc_yeucau"]]
    #tat
    write_request_queue = asyncio.Queue()
    writer_task = asyncio.create_task(file_writer(write_request_queue, OUTPUT_FILE, BATCH_WRITE_SIZE))

    # Record the start time of the program execution.
    start = datetime.now()
    # Define the number of coroutines and the number of tasks.
    worker_num, task_num = 3, len(job_jb_df)
    # Create an asynchronous queue for storing requests, which supports asynchronous operations.
    requests = asyncio.Queue()
    # Initialize the asynchronous ModelArk client.
    client = AsyncArk(
        # Get the API key from the environment variable to ensure the security of the key.
        api_key=os.environ.get("ARK_API_KEY"),
        # Set the timeout to 24 hours. It is recommended to set the timeout as large as possible, preferably 24 hours to 72 hours, to avoid request timeouts due to network or other reasons.
        timeout=24 * 3600,
    )
    # Simulate `task_num` tasks and add the request information to the queue.
    for index, row in job_jb_df.iterrows():
        await requests.put(
            {
            "model_request":
                {
                    # Replace it with your batch inference endpoint ID, specifying the service endpoint to be called.
                    "model": "seed-2-0-lite-260228",
                    "messages": [
                        {
                            "role": "user", 
                            "content": "Extract all IT skills in the following text"
                                "Rule:"
                                " 1.keep raw text, do not translate:"
                                "2.Format output: Skill, Skill, Skill"
                                "3. If there is no skill in the text, output: None"
                                f"Text:'{row['desc_mota']} {row['desc_yeucau']}'"
                        },
                    ]
                },
            "id" : row['id']
            }
        )
    # Create `worker_num` asyncio task coroutines and start them. Each coroutine is responsible for processing the requests in the queue.
    # These coroutines will execute concurrently in a single thread, and the efficiency is improved through the switching of coroutines.
    tasks = [
        asyncio.create_task(worker(i, client, requests, write_request_queue))
        for i in range(worker_num)
    ]
    # Wait for all requests to be processed, that is, all tasks in the queue are marked as completed.
    await requests.join()
    # Stop all coroutines and cancel all running tasks.
    for task in tasks:
        task.cancel()
    # Wait for all coroutines to be cancelled, ensuring that all tasks have been stopped.
    await asyncio.gather(*tasks, return_exceptions=True)
    # Close the client connection and release resources.
    await client.close()
    # Record the end time of the program execution.
    end = datetime.now()
    # Print the total execution time of the program and the total number of tasks processed.
    print(f"Total time: {end - start}, Total task: {task_num}")

if __name__ == "__main__":
    # Run the asynchronous main function to start the entire program.
    # asyncio.run() will create an event loop and run the main coroutine in this event loop.
    dotenv.load_dotenv("./.env")
    asyncio.run(main()) 