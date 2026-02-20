import os
import boto3
import time
import random
import string
import json
from decimal import Decimal
from typing import List, Annotated
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.bedrock_agent import BedrockAgentResolver 
from aws_lambda_powertools.event_handler.openapi.params import Query, Body
from aws_lambda_powertools import Metrics, Logger
from aws_lambda_powertools.metrics import MetricUnit

"""_
_@note: See how we don't need to create all the Response (e.g. actionGroup, apiPath, etc.), as stated here:
        - docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
        - docs.aws.amazon.com/bedrock/latest/userguide/agents-api-schema.html
        but we can just return the response directly. This is because the BedrockAgentResolver class takes care of that for us.
"""

# Initialize Agents, Metrics, Loggers
app = BedrockAgentResolver()
metrics = Metrics(namespace="virtual-assistant-api-logs", service="virtual-assistance")
logger = Logger(level='INFO')


def put_items(ddb_table, product_id, product_name, price_gbp, quantity, order_notes=None):
    """_summary_

    Args:
        ddb_table (_type_): _description_
        product_id (_type_): _description_
        product_name (_type_): _description_
        price_gbp (_type_): _description_
        quantity (_type_): _description_
        order_notes (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    # Table init
    table = dynamodb.Table(ddb_table)
    
    # Print for terminal
    print(f"Inserting product ID: {product_id}")

    # Get current time in unix timestamp. 
    # - Primary Key in DDB is Partition Key (pk) and Sort Key (sk). This is our Order ID.
    current_time = int(time.time())

    # Generate a fake session id
    session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Append key and value to item
    item = {}
    item['pk'] = f'product_id#{product_id}#session_id#{session_id}'
    item['sk'] = str(current_time)
    item['product_id'] = product_id
    item['product_name'] = product_name
    item['price_gbp'] = price_gbp
    item['quantity'] = quantity
    
    if order_notes:
        # Add any potential notes, written by the LLM
        item['order_notes'] = order_notes

    # Cast Float to Decimals, for DDB support.
    ddb_data = json.loads(json.dumps(item), parse_float=Decimal)

    # Logging and metrics
    logger.info(f"Storing product sale with details (DDB Item to insert): {item}")

    try:
        # Insert item in DynamoDB table
        response = table.put_item(Item=ddb_data)
        print(response)

        return {
            'statusCode': 200,
            'body': f'Sale recorded for product ID {product_id}'
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error inserting item: {e}'
        }


@app.post("/upsertOrder", description='Inserts or updates the Products purchased, in the Sales Table.')
def upsert_order(
    product_id: Annotated[str, Query(description='Product ID from the order placed')],
    product_name: Annotated[str, Query(description='Product Name from the order placed')],
    price_gbp: Annotated[float, Query(description='Price with decimals for the purchased product.')],
    quantity: Annotated[int, Query(description='Quantity of the purchased product')],
    order_notes: Annotated[str, Query(description='Any notes from the order placed')],
    ) -> Annotated[bool, Body(description='Return True if order has been placed correctly')]:
    
    # Get DynamoDB table name
    table_name = os.environ['DDB_TABLE_NAME']

    # Logging and metrics
    logger.info(f"Storing product sale...")
    
    try:
        # Upsert data in DynamoDB Sales table
        response = put_items(ddb_table=table_name,
                            product_id=product_id,
                            product_name=product_name,
                            price_gbp=price_gbp,
                            quantity=quantity,
                            order_notes=order_notes
                            )
        
        # Logging and metrics
        logger.info(f"Storing product sale response: {response}")
        
        # Keep metrics
        metrics.add_metric(name="upsertOrders", unit=MetricUnit.Count, value=1)

        return True

    except Exception:
        logger.exception("Error creating Order in the Database")
        return False


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event, context):
    logger.info(f"Event: {event}")
    return app.resolve(event, context)


if __name__ == "__main__":  
    print(app.get_openapi_json_schema())