import json
import os
import boto3
import botocore

# ==================
# Override AWS Region below, otherwise will use Lambda function's region

# REGION_NAME = 'us-east-1'
# ==================

try:
    REGION_NAME
except NameError:
    REGION_NAME = os.environ['AWS_REGION']

LAMBDA_CLIENT = boto3.client('lambda', region_name=REGION_NAME)


# Paginator to loop over paginated API calls
LIST_FUNCTIONS_PAGINATOR = LAMBDA_CLIENT.get_paginator('list_functions')
LIST_FUNCTIONS_PAGE_ITERATOR = LIST_FUNCTIONS_PAGINATOR.paginate()

LIST_ESM_PAGINATOR = LAMBDA_CLIENT.get_paginator('list_event_source_mappings')
LIST_ESM_PAGE_ITERATOR = LIST_ESM_PAGINATOR.paginate()

# Create set to keep track
LIST_FUNTIONS = set()
DELETED_ESM = set()


def find_orphaned_esm():
    """Return all ESM and FunctionArn in this region"""
    functions = LIST_FUNCTIONS_PAGE_ITERATOR.search("Functions[*].FunctionArn")
    for function in functions:
        LIST_FUNTIONS.add(function)

    esms = LIST_ESM_PAGE_ITERATOR.search("EventSourceMappings[*].[FunctionArn,UUID]")
    for esm in esms:
        # if this function valid?
        if esm[0] not in LIST_FUNTIONS:
            delete_orphaned_esm(esm[0], esm[1])
    return True


def delete_orphaned_esm(lambda_arn, esm_id):
    """Delete the event source mapping using the UUID (esm_id)"""
    try:
        response = LAMBDA_CLIENT.delete_event_source_mapping(UUID=esm_id)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"Deleted ESM for UUID: {esm_id} associated with {lambda_arn}")
            DELETED_ESM.add(esm_id)
    except botocore.exceptions.ClientError as error:
        print(f'ClientError: {error}')
    except botocore.exceptions.ParamValidationError as error:
        print('ValueError: The parameters you provided are incorrect: {error}')
    except Exception as exp:
        print(exp)
    return True


def lambda_handler(event, context):
    """Main Lambda function"""

    find_orphaned_esm()
    if DELETED_ESM:
        body = "See logs for deleted Event Source Mappings"
    else:
        body = f"No orphaned Event Source mappings found in {REGION_NAME}"
    return {
        'statusCode': 200,
        'body': json.dumps(body)
    }
