"""Lambda processadora (SQS -> DynamoDB). Placeholder — consome o batch."""


def handler(event, context):
    records = event.get("Records", [])
    print(f"placeholder: recebidas {len(records)} mensagens")
    return {"batchItemFailures": []}
