from faust.types import ProcessingGuarantee
import logging
import faust

app = faust.App(
    'PoC_consumer_2',
    broker=f'kafka://kafka:9092',
    value_serializer='raw',
    processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
)

input_topic = app.topic('consumer_input_1')
output_topic = app.topic('consumer_output_1')


@app.agent(input_topic)
async def consumer_agent(messages):
    async for message in messages:
        logging.info(f"[consumer] Got message {message.decode('utf-8')}")
        logging.info(f'[consumer] App in_transaction: {app.in_transaction}')
        await output_topic.send(value=message)
        logging.info(f"[consumer] Message {message.decode('utf-8')} is sent to consumer_output")
