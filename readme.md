##Тестирование faust приложения с использованием семантики EXACTLY_ONCE

Команды для тестирования:

- Агенты в одном приложении:


    ``sh
    sudo docker exec -it producer_consumer_service faust -A app send @<producer_name> "Hello Faust"
    ``

- Агенты в разных приложениях:


    ``sh
    sudo docker exec -it producer_service faust -A app send @<producer_name> "Hello Faust"
    ``

Где producer_name - имя агента продюсера из следующего списка:

1. producer_agent - автоматический ack
2. producer_agent_manual - ручной ack с stream.noack().events()
3. producer_agent_manual_noack - ручной ack с stream.noack().noack_take(1, 1)


### Сценарий успешной обработки сообщения

Агент продюсер принимает сообщение, отсылает агенту консьюмеру, 
консьюмер обрабатывает сообщение (в данном случае записывает в фауст таблицу)
только после подтверждения от продюсера.


**Поведение producer_agent**:

Консьюмер обрабатывает сообщения после обработки продюсером

```sh
[2023-03-10 13:34:30,721] [22] [INFO] [producer] Got message Hello Faust
[2023-03-10 13:34:30,721] [22] [INFO] [producer] App in_transaction: True 
[2023-03-10 13:34:30,722] [22] [INFO] [producer] Send to consumer, sleeping 10 seconds 
[2023-03-10 13:34:40,724] [22] [INFO] [producer] Consumer didnt process message before ack 
[2023-03-10 13:34:43,415] [22] [INFO] [consumer] Got message Hello Faust
[2023-03-10 13:34:43,416] [22] [INFO] [consumer] App in_transaction: True 
[2023-03-10 13:34:43,416] [22] [INFO] [consumer] Message Hello Faust is written in consumer_result 
```

**Поведение producer_agent_manual или producer_agent_manual_noack**:

Консьюмер обрабатывает сообщения после отправки ack продюсером

```sh
[2023-03-10 12:44:49,920] [22] [INFO] [producer] Got message Hello Faust
[2023-03-10 12:44:49,920] [22] [INFO] [producer] App in_transaction: True 
[2023-03-10 12:44:49,920] [22] [INFO] [producer] Send to consumer, sleeping 10 seconds 
[2023-03-10 12:44:59,921] [22] [INFO] [producer] Consumer didnt process message before ack 
[2023-03-10 12:44:59,922] [22] [INFO] [producer] Acked message, sleeping 10 seconds 
[2023-03-10 12:45:02,444] [22] [INFO] [consumer] Got message Hello Faust
[2023-03-10 12:45:02,445] [22] [INFO] [consumer] App in_transaction: True 
[2023-03-10 12:45:02,445] [22] [INFO] [consumer] Message Hello Faust is written in consumer_result 
[2023-03-10 12:45:09,930] [22] [INFO] [producer] Consumer processed message after ack: Hello Faust 

```


**Особенности**:

Метод send топика не работает в транзакции, приходится использовать внешние агенты
с методом cast. При использовании send консьюмер обрабатывает сообщение не дожидаясь ответа от продюсера.
Нашел тикет с подобной проблемой: https://github.com/faust-streaming/faust/issues/177

При использовании внешнего консьюмера с методом cast в логах выдает такое 
(что логично, внешний агент ничего не обрабатывает), 
но сообщения корректно обрабатываются:

```sh
[2023-03-12 16:55:50,452] [23] [ERROR] [^---AIOKafkaConsumerThread]: Stream has not started processing TP(topic='consumer_input_1', partition=0) (started 7.47 minutes ago). 
There are multiple possible explanations for this:
1) The processing of a single event in the stream
   is taking too long.
    The timeout for this is defined by the stream_processing_timeout setting,
    currently set to 300.0.  If you expect the time
    required to process an event, to be greater than this then please
    increase the timeout.
 2) The stream has stopped processing events for some reason.
3) The agent processing the stream is hanging (waiting for network, I/O or infinite loop).
```


### Сценарий работы с возникновением ошибки при обработке сообщения

При отправке сообщения содержащего raise возникает Exception. 


**Поведение producer_agent**:

При возникновении Exception продюсер подтверждает обработку, 
консьюмер обрабатывает сообщение несмотря на ошибку в продюсере.

```sh
[2023-03-10 13:47:35,022] [23] [INFO] [producer] Got message raise_message_1 
[2023-03-10 13:47:35,022] [23] [INFO] [producer] App in_transaction: True 
[2023-03-10 13:47:35,023] [23] [INFO] [producer] Send to consumer, sleeping 10 seconds 
[2023-03-10 13:47:45,027] [23] [INFO] [producer] Consumer didnt process message before ack 
[2023-03-10 13:47:45,027] [23] [ERROR] [^----Agent*: app.producer_agent]: Crashed reason=Exception('[producer] ERROR while  processing message') 
Traceback (most recent call last):
  File "/opt/app-root/lib64/python3.8/site-packages/faust/agents/agent.py", line 674, in _execute_actor
    await coro
  File "/opt/app/app.py", line 58, in producer_agent
    raise Exception('[producer] ERROR while  processing message')
Exception: [producer] ERROR while  processing message
[2023-03-10 13:47:45,028] [23] [INFO] [^----OneForOneSupervisor: (1@0x7fc2404e6be0)]: Restarting dead <Agent*: app.producer_agent>! Last crash reason: Exception('[producer] ERROR while  processing message') 
NoneType: None
[2023-03-10 13:47:47,058] [23] [INFO] [consumer] Got message raise_message_1 
[2023-03-10 13:47:47,059] [23] [INFO] [consumer] App in_transaction: True 
[2023-03-10 13:47:47,060] [23] [INFO] [consumer] Message raise_message_1 is written in consumer_result 
```

При попытке послать новое сообщение без ошибки продюсер его успешно обрабатывает

**Поведение producer_agent_manual или producer_agent_manual_noack**:

При возникновении Exception продюсер не подтверждает обработку, 
консьюмер не обрабатывает сообщение, само сообщение не доходит в топик консьюмеру.


```sh
producer_consumer_service    | [2023-03-10 14:29:39,552] [23] [INFO] [producer] Got message raise_message_3 
producer_consumer_service    | [2023-03-10 14:29:39,553] [23] [INFO] [producer] App in_transaction: True 
producer_consumer_service    | [2023-03-10 14:29:39,555] [23] [INFO] [producer] Send to consumer, sleeping 10 seconds 
producer_consumer_service    | [2023-03-10 14:29:49,557] [23] [INFO] [producer] Consumer didnt process message before ack 
producer_consumer_service    | [2023-03-10 14:29:49,558] [23] [ERROR] [^----Agent*: app.producer_agent_manual]: Crashed reason=Exception('[producer] ERROR while  processing message') 
producer_consumer_service    | Traceback (most recent call last):
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/faust/agents/agent.py", line 674, in _execute_actor
producer_consumer_service    |     await coro
producer_consumer_service    |   File "/opt/app/app.py", line 78, in producer_agent_manual
producer_consumer_service    |     raise Exception('[producer] ERROR while  processing message')
producer_consumer_service    | Exception: [producer] ERROR while  processing message
producer_consumer_service    | [2023-03-10 14:29:49,573] [23] [INFO] [^----OneForOneSupervisor: (1@0x7f445283f280)]: Restarting dead <Agent*: app.producer_agent_manual>! Last crash reason: Exception('[producer] ERROR while  processing message') 
producer_consumer_service    | NoneType: None
```

При попытке послать новое сообщение без ошибки в тот же агент происходит краш приложения:

```sh
producer_consumer_service    | [2023-03-10 14:32:01,397] [23] [INFO] [producer] Got message Hello Faust 15 
producer_consumer_service    | [2023-03-10 14:32:01,397] [23] [INFO] [producer] App in_transaction: True 
producer_consumer_service    | [2023-03-10 14:32:01,398] [23] [INFO] [producer] Send to consumer, sleeping 10 seconds 
producer_consumer_service    | [2023-03-10 14:32:01,408] [23] [WARNING] _on_published error for message topic consumer_input error ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms) message <FutureMessage finished exception=ProducerFenced('There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)')> 
producer_consumer_service    | [2023-03-10 14:32:11,403] [23] [INFO] [producer] Consumer didnt process message before ack 
producer_consumer_service    | [2023-03-10 14:32:11,410] [23] [INFO] [producer] Acked message, sleeping 10 seconds 
producer_consumer_service    | [2023-03-10 14:32:13,311] [23] [WARNING] ProducerFenced ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms) 
producer_consumer_service    | [2023-03-10 14:32:13,312] [23] [ERROR] [^-App]: Crashed reason=ProducerFenced('There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)') 
producer_consumer_service    | Traceback (most recent call last):
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 340, in commit
producer_consumer_service    |     await producer.commit_transactions(
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/drivers/aiokafka.py", line 1216, in commit_transactions
producer_consumer_service    |     await transaction_producer.send_offsets_to_transaction(
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/producer.py", line 579, in send_offsets_to_transaction
producer_consumer_service    |     await asyncio.shield(fut)
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 155, in _sender_routine
producer_consumer_service    |     task.result()
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 316, in _do_add_offsets_to_txn
producer_consumer_service    |     return (await handler.do(node_id))
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 380, in do
producer_consumer_service    |     retry_backoff = self.handle_response(resp)
producer_consumer_service    |   File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 539, in handle_response
producer_consumer_service    |     raise ProducerFenced()
producer_consumer_service    | aiokafka.errors.ProducerFenced: ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)
```

При попытке послать сообщение без ошибки в другой агент происходит краш приложения:

```sh
[2023-03-10 15:25:08,975] [23] [INFO] [producer] Got message Hello World 1 
[2023-03-10 15:25:08,975] [23] [INFO] [producer] App in_transaction: True 
[2023-03-10 15:25:08,977] [23] [INFO] [producer] Send to consumer, sleeping 10 seconds 
[2023-03-10 15:25:08,982] [23] [WARNING] _on_published error for message topic consumer_input_1 error ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms) message <FutureMessage finished exception=ProducerFenced('There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)')> 
[2023-03-10 15:25:18,981] [23] [INFO] [producer] Consumer didnt process message before ack 
[2023-03-10 15:25:18,981] [23] [INFO] [producer] Acked message, sleeping 10 seconds 
[2023-03-10 15:25:21,536] [23] [ERROR] [^--Consumer]: Crashed reason=IllegalOperation('Not in the middle of a transaction') 
Traceback (most recent call last):
  File "/opt/app-root/lib64/python3.8/site-packages/mode/services.py", line 843, in _execute_task
    await task
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 894, in _commit_handler
    await self.commit()
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 934, in commit
    return await self.force_commit(
  File "/opt/app-root/lib64/python3.8/site-packages/mode/services.py", line 498, in _and_transition
    return await fun(self, *args, **kwargs)
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 969, in force_commit
    did_commit = await self._commit_tps(
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 985, in _commit_tps
    return await self._commit_offsets(
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 1049, in _commit_offsets
    did_commit = await self.transactions.commit(
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 340, in commit
    await producer.commit_transactions(
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/drivers/aiokafka.py", line 1216, in commit_transactions
    await transaction_producer.send_offsets_to_transaction(
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/producer.py", line 567, in send_offsets_to_transaction
    raise IllegalOperation("Not in the middle of a transaction")
aiokafka.errors.IllegalOperation: Not in the middle of a transaction
```

При рестарте обрабатываются все соообщения, по которым не было подтверждения. 

**Особенности**:

Было ожидание, что подходы stream.noack().events() и stream.noack().noack_take(1, 1) 
будут отличаться в том плане, что первый будет пропускать не подтвержденные сообщения после рестарта, а второй нет.

Как описано в следующих issue:

- https://github.com/faust-streaming/faust/issues/312
- https://github.com/faust-streaming/faust/issues/315
- https://github.com/faust-streaming/faust/issues/189

Однако в последней версии видимо баг с stream.noack().events() был исправлен и оба подхода работают одинаково.

### Сценарий работы с возникновением сбоя при обработке сообщения

При отправке сообщения содержащего exit работа приложения аварийноо завершается.

Поведение агентов как при ручном, 
так и при автоматическом подтверждении идентично.
Сообщение не обрабатывается консьюмером после сбоя, после восстановления работы 
обработка начинается с того сообщения на котором произошел сбой.

### Сценарий пропуска сообщения 

При отправке сообщения содержащего skip в агенты с ручным подтверждением, продюсер не отправляет ack.

Консьюмер соответственно не обрабатывает сообщение, при отправке нового сообщения в любой агент 
происходит краш приложения:

```sh
[2023-03-12 17:21:29,531] [23] [ERROR] FutureMessage exception was never retrieved
future: <FutureMessage finished exception=ProducerFenced('There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)')> 
Traceback (most recent call last):
  File "/opt/app-root/lib64/python3.8/site-packages/faust/topics.py", line 463, in _on_published
    res: RecordMetadata = fut.result()
aiokafka.errors.ProducerFenced: ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)
[2023-03-12 17:21:29,544] [23] [CRITICAL] [^Worker]: We experienced a crash! Reraising original exception... 
[2023-03-12 17:21:29,581] [23] [ERROR] Future exception was never retrieved
future: <Future finished exception=ProducerFenced('There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)')> 
Traceback (most recent call last):
  File "/opt/app-root/lib64/python3.8/site-packages/mode/worker.py", line 69, in exiting
    yield
  File "/opt/app-root/lib64/python3.8/site-packages/mode/worker.py", line 290, in execute_from_commandline
    self.stop_and_shutdown()
  File "/opt/app-root/lib64/python3.8/site-packages/mode/worker.py", line 302, in stop_and_shutdown
    self._shutdown_loop()
  File "/opt/app-root/lib64/python3.8/site-packages/mode/worker.py", line 331, in _shutdown_loop
    raise self.crash_reason from self.crash_reason
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/consumer.py", line 340, in commit
    await producer.commit_transactions(
  File "/opt/app-root/lib64/python3.8/site-packages/faust/transport/drivers/aiokafka.py", line 1216, in commit_transactions
    await transaction_producer.send_offsets_to_transaction(
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/producer.py", line 579, in send_offsets_to_transaction
    await asyncio.shield(fut)
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 155, in _sender_routine
    task.result()
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 316, in _do_add_offsets_to_txn
    return (await handler.do(node_id))
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 380, in do
    retry_backoff = self.handle_response(resp)
  File "/opt/app-root/lib64/python3.8/site-packages/aiokafka/producer/sender.py", line 539, in handle_response
    raise ProducerFenced()
aiokafka.errors.ProducerFenced: ProducerFenced: There is a newer producer using the same transactional_id ortransaction timeout occurred (check that processing time is below transaction_timeout_ms)
```

После восстановления работы обработка начинается с того сообщения, которое было пропущено.


Возможности нормального отклонения транзакции я так понял нет, 
можно не сделать ack, но при получении следующего сообщения приложение упадет.

