import asyncio
import os

from faust.types import ProcessingGuarantee
import logging
import faust

SLEEP_INTERVAL = 10
EXCEPTION_ON_RAISE_MESSAGE = eval(os.getenv('EXCEPTION_ON_RAISE_MESSAGE'))

app = faust.App(
    'PoC_producer_consumer',
    broker=f'kafka://kafka:9092',
    value_serializer='raw',
    broker_commit_livelock_soft_timeout=300,
    processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
)

input_topic = app.topic('producer_input')
input_topic_manual = app.topic('producer_input_topic_manual')
input_topic_manual_no_ack = app.topic('producer_input_topic_manual_no_ack')
consumer_input_topic = app.topic('consumer_input')
output_table = app.Table(
    f'consumer_result',
    key_type=str,
    partitions=1,
    value_type=str
)


@app.agent(consumer_input_topic)
async def consumer_agent(messages):
    async for message in messages:
        logging.info(f"[consumer] Got message {message.decode('utf-8')}")
        logging.info(f'[consumer] App in_transaction: {app.in_transaction}')
        output_table[message.decode('utf-8')] = message.decode('utf-8')
        logging.info(f"[consumer] Message {message.decode('utf-8')} is written in consumer_result")
        yield message + b' processed'


@app.agent(input_topic)
async def producer_agent(messages):
    async for message in messages:
        logging.info(f"[producer] Got message {message.decode('utf-8')}")
        logging.info(f'[producer] App in_transaction: {app.in_transaction}')
        await consumer_agent.cast(value=message)
        logging.info(
            f'[producer] Send to consumer, sleeping {SLEEP_INTERVAL} seconds')
        await asyncio.sleep(SLEEP_INTERVAL)

        consumer_result = output_table.get(message.decode('utf-8'))
        if consumer_result:
            logging.info(f'[producer] Consumer processed message before ack: {consumer_result}')
        else:
            logging.info(f'[producer] Consumer didnt process message before ack')

        if 'raise' in message.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
            raise Exception('[producer] ERROR while  processing message')

        if 'exit' in message.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
            os._exit(2)


@app.agent(input_topic_manual)
async def producer_agent_manual(stream):
    async for event in stream.noack().events():
        logging.info(f"[producer] Got message {event.value.decode('utf-8')}")
        logging.info(f'[producer] App in_transaction: {app.in_transaction}')
        await consumer_agent.cast(value=event.value)
        logging.info(
            f'[producer] Send to consumer, sleeping {SLEEP_INTERVAL} seconds')
        await asyncio.sleep(SLEEP_INTERVAL)

        consumer_result = output_table.get(event.value.decode('utf-8'))
        if consumer_result:
            logging.info(f'[producer] Consumer processed message before ack: {consumer_result}')
        else:
            logging.info(f'[producer] Consumer didnt process message before ack')

        if 'raise' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
            raise Exception('[producer] ERROR while  processing message')

        if 'exit' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
            os._exit(2)

        if 'skip' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
            logging.info('Skipping message')
        else:
            event.ack()
            logging.info(f'[producer] Acked message, sleeping {SLEEP_INTERVAL} seconds')
            await asyncio.sleep(SLEEP_INTERVAL)

            consumer_result = output_table.get(event.value.decode('utf-8'))
            if consumer_result:
                logging.info(f'[producer] Consumer processed message after ack: {consumer_result}')
            else:
                logging.info(f'[producer] Consumer didnt process message after ack:')


@app.agent(input_topic_manual_no_ack)
async def producer_agent_manual_noack(stream):
    async for events in stream.noack().noack_take(1, 1):
        for event in events:
            logging.info(f"[producer] Got message {event.value.decode('utf-8')}")
            logging.info(f'[producer] App in_transaction: {app.in_transaction}')
            await consumer_agent.cast(value=event.value)
            logging.info(f'[producer] Send to consumer, sleeping {SLEEP_INTERVAL} seconds')
            await asyncio.sleep(SLEEP_INTERVAL)

            consumer_result = output_table.get(event.value.decode('utf-8'))
            if consumer_result:
                logging.info(f'[producer] Consumer processed message before ack: {consumer_result}')
            else:
                logging.info(f'[producer] Consumer didnt process message before ack')

            if 'raise' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
                raise Exception('[producer] ERROR while  processing message')

            if 'exit' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
                os._exit(2)

            if 'skip' in event.value.decode('utf-8') and EXCEPTION_ON_RAISE_MESSAGE:
                logging.info('Skipping message')
            else:
                event.ack()
                logging.info(f'[producer] Acked message, sleeping {SLEEP_INTERVAL} seconds')
                await asyncio.sleep(SLEEP_INTERVAL)

                consumer_result = output_table.get(event.value.decode('utf-8'))
                if consumer_result:
                    logging.info(f'[producer] Consumer processed message after ack: {consumer_result}')
                else:
                    logging.info(f'[producer] Consumer didnt process message after ack:')
