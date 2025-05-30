from unittest.mock import patch

import pytest
from asyncmock import AsyncMock

from extensions.eda.plugins.event_source.aws_sqs_queue import main as sqs_main
from tests.conftest import ListQueue


@pytest.mark.asyncio
async def test_receive_from_sqs(eda_queue: ListQueue) -> None:
    session = AsyncMock()
    with patch(
        "extensions.eda.plugins.event_source.aws_sqs_queue.get_session",  # noqa: E501
        return_value=session,
    ):
        client = AsyncMock()
        client.get_queue_url.return_value = {"QueueUrl": "sqs_url"}

        message1 = {
            "MessageId": "1",
            "Body": "Hello World",
            "ReceiptHandle": "abcdef",
        }
        message2 = {
            "MessageId": "2",
            "Body": '{"Say":"Hello World"}',
            "ReceiptHandle": "xyz123",
        }
        delete_response1 = {
            "Id": "1",
            "ReceiptHandle": "abcdef",
        }
        delete_response2 = {
            "Id": "2",
            "ReceiptHandle": "xyz123",
            "Code": "405",
            "Message": "Failed to delete Message",
            "SenderFault": True,
        }

        response = {"Messages": [message1, message2]}
        delete_response = {
            "Successful": [delete_response1],
            "Failed": [delete_response2],
        }
        client.receive_message = AsyncMock(side_effect=[response, ValueError()])
        client.delete_message_batch = AsyncMock(
            side_effect=[delete_response, ValueError()]
        )

        session.create_client.return_value = client
        session.create_client.not_async = True

        with pytest.raises(ValueError):
            await sqs_main(
                eda_queue,
                {
                    "region": "us-east-1",
                    "name": "eda",
                    "delay_seconds": 1,
                    "max_number_of_messages": 3,
                    "queue_owner_aws_account_id": "123456",
                },
            )
        assert eda_queue.queue[0] == {"body": "Hello World", "meta": {"MessageId": "1"}}
        assert eda_queue.queue[1] == {
            "body": {"Say": "Hello World"},
            "meta": {"MessageId": "2"},
        }
        assert len(eda_queue.queue) == 2
