# The inference pipeline
## Overview
Since in this project we are focusing on satellite data, we choose the batch model of inference, where new data will be placed in a particular location (concretely on AWS S3) and the pipeline is run on a certain cadence to process new images.
The inference pipeline is run on the AWS cloud and is orchestrated via [AWS StepFunctions](https://aws.amazon.com/step-functions/). StepFunctions are a robust and easy-to-use tool to build workflows. They feature a graphical editor that can be used to construct workflows, as well as a custom, json-like DSL for more programmatic approach. The workflow is represented in terms of a state-machine where every node represents a state (e.g. task or choice) and every edge a transformation from one state to another. The schematic of the pipeline can be seen below:

![](./imgs/state_machine.png)

The 3 tasks here are of course:

- Processing: turn raw data to processed data ready to be used for the model. This reuses the [same code]() that was used for this purpose in the training pipeline.
- Inference: the model is loaded and is run on the data to produce predictions for the label of every image
- Observe: a set of metrics looking at the behaviour of the model is computed using `Evidently`:
    1. The class distribution (i.e. what share of all the predictions fall in each class)
    2. The prediction drift: a measure of the difference between the distribution of predictions classes on the new data vs the distribution on the training data (note: for simplicity we used syntehtic reference data in this project that simply reflects the true underlying class distribution of the data)


Each task is followed by a choice node which checks the output of the task and depending on whether it succeeds or fails continues along the graph. In the above, all successful executions take the _right_ branch.

## Implementation
On a more concrete implementation level, the 3 tasks above are done by 3 AWS Lambda functions:

![](./imgs/state_machine_impl.png)

The [code]() for the 3 functions are all packaged in a single Docker image and the correct handler is chosen as appropriate.

The Lambda functions need access to several other AWS services:

- AWS Elastic Container Registry (ECR):  to store the actual image used by the Lamdba  functions
- AWS S3:

    1. To access the model that we uploaded to S3 at the end of the training pipeline
    2. To access new data and write the results

- AWS Remote Database Service (RDS) where a PostgresSQL database is used for 2 tasks:

    1. Keep track which tasks have been completed on which files in a `ledger` database
    2. Record a set of metrics computed with `Evidently` which will be subsequently visualized in a dashboard. See [below]()

- AWS Secrets Manager: Since we are connecting to RDS we need to securely store credentials.

In order to schedule the execution of the  AWS StepFunction state machine, we use AWS EventBridge scheduler which is basically just a CRON job that runs on a given cadence, which by default is 24 hours.

Finally, for observability dashboard, we opted to run a local `Grafana` server in `Docker`. In order for this server to be able to access the data in the AWS RDS database we set up and EC2 instance in the same network as RDS and create an ssh tunnel to forward the information.

Thus the complete system looks as follows:

![](./imgs/architecture.svg)


### Observability
Using the ssh tunnel, the RDS database can be accessed on local host at the usual port 5432. We construct an additional