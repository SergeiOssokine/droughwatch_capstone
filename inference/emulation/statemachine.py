import logging
import time

from botocore.exceptions import ClientError
from rich.logging import RichHandler
from rich.traceback import install

logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


class StateMachine:
    """Encapsulates Step Functions state machine actions."""

    def __init__(self, stepfunctions_client, name, input):
        """
        :param stepfunctions_client: A Boto3 Step Functions client.
        """
        self.stepfunctions_client = stepfunctions_client
        self.state_machine_arn = self.find(name)
        self.run_input = input

    def find(self, name):
        """
        Find a state machine by name. This requires listing the state machines until
        one is found with a matching name.

        :param name: The name of the state machine to search for.
        :return: The ARN of the state machine if found; otherwise, None.
        """
        try:
            paginator = self.stepfunctions_client.get_paginator("list_state_machines")
            for page in paginator.paginate():
                for state_machine in page.get("stateMachines", []):
                    if state_machine["name"] == name:
                        return state_machine["stateMachineArn"]
        except ClientError as err:
            logger.error(
                "Couldn't list state machines. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise

    def blocking_execution(self):
        logger.info("Launching the pipeline execution")
        response = self.stepfunctions_client.start_execution(
            stateMachineArn=self.state_machine_arn, input=self.run_input
        )
        run_arn = response["executionArn"]
        status = "RUNNING"
        while status == "RUNNING":
            response = self.stepfunctions_client.describe_execution(
                executionArn=run_arn
            )
            status = response["status"]
            print(f"\r Current status: {status}")
            time.sleep(2)
        return response
