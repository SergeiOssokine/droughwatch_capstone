# droughwatch_capstone
Use ML to predict the quality of soil from satellite images


## Initial setup
This project assumes that one is using Linux/MacOS locally. If on Windows, please run inside WSL2.

In order to be able to execute this project you will need:
- Python 3.10
- Docker (v27.0 or later) with docker compose
- Terraform (v1.9.3 or later)
- aws cli==2.17.5
- jq-1.6
- GNU make

You will also need an AWS account with sufficient priveleges.

To manage python dependencies we use [uv](https://github.com/astral-sh/uv) as it is extremely fast and robust. Install it following the [official guidelines](https://github.com/astral-sh/uv?tab=readme-ov-file#getting-started).

Throughout the project, `make` is used a lot. Note that whenever a `make` command is mentioned, it should be invoked at the top-level of the repo. To see the full list of possible commands simply run
```bash
make
```

Setup the dev environment by running (this will use `uv` to create a new virtualenv and install all the necessary dependencies)

```bash
make setup_env
```

Note that since we will be training CNNs it is highly desirable to run on a machine with CUDA-capable GPU or the training might take a very long time. For reference, the baseline model took 1 hour to train on NVidia GTX 1060 6GB



## Training the model

### Part I: Get the data
The training data is large and thus we only want to download it once. You can do this by running

```bash
source .mlops/bin/activate
make download_data
```
Note that this will take a few minutes.

### Part II: Prepare the infrastructure

The training pipeline is managed by `Airflow` DAGs, which takes care of data preparation and actual training using `Keras`. The experimentation tracking can either be done:
- locally with  `MLFlow` or
- on the Weights and Biases cloud. The latter requires one to have a WandB account (the free tier is more than sufficient). In particular, you will need your `WANDB_API_KEY` (see below)

To do this, we run a docker compose stack that contains all the necessary services. In order for everything to work, one needs to configure a few things first. The configuration for this project is managed via Hydra, that uses nested, composable yaml files. The configuration files are in `./setup/conf`. For more details on training pipeline, see [here]().


First the user _must_ set up a secrets file, which will contain the AWS (and optionally WANDB credentials). This should be a file in standard `.env` format. Here is one example of how it can be created (assuming one is using WandB):

```bash
cd setup
export WANDB_API_KEY=XXXX
echo "WANDB_API_KEY=${WANDB_API_KEY}" > .secrets

aws configure sso # If using SSO credentials
aws configure export-credentials --format env-no-export >> .secrets
```

You should have something like this in `.secrets`

```bash
WANDB_API_KEY=XXXX
AWS_ACCESS_KEY_ID=YYYYYYYYY
AWS_SECRET_ACCESS_KEY=ZZZZZZZZZZZZZZZZ
AWS_SESSION_TOKEN=REALLY_LONG_STRING
AWS_CREDENTIAL_EXPIRATION=2024-07-24T13:36:28+00:00
```

Then, the user could change the values in `./setup/conf/config.yaml`.  Most importantly:
- `training.model_registry_s3_bucket` Name of the S3 bucket that will be created to store models that are promoted to the model registry. **Make sure to pick a globally unique name** (using `uuidgen` may be helpful here)
- `training.logging.style`. This determines whether the experiment tracking is done using WandB in the cloud  or locally using MLFlow (note that this means the tracking and backend server are local, i.e. inside the docker stack, while models in the registry will still be written to S3). Can either be `wandb` or `mlflow`.
- `training.logging.wandb_org_name`. Name of the org created when setting up wandb. Only need to change this if wandb is used, otherwise leave the default.
- `infra.aws_region`. The region in which all AWS services will be deployed.
- `infra.training.use_gpu_training`. Whether a GPU will be used (0 means no, 1 means yes). Note that only nVidia GPUs with compute capabilities > 6 are supported. You will also need to set up the nvidia Docker toolkit, as described [here]().
- `infra.inference.data_bucket`. The name of the bucket where new data will be added to run batch inference.
- `model_path`: Which model in the `model_registry_s3_bucket` to use. WARNING: only change this if you intend to train more than just the default baseline model.


Once all done, deploy the training infrastructure docker by doing

```bash
make setup_training_infra
```
This will produce a lot of output, including a yaml representation of the project configuration. It will also
setup the s3 bucket needed to hold models that will be promoted to the model registry.

If everything looks right and no errors are returned deploy everything by running

```bash
make launch_training_infra`
```
This will take a while the first time you run it, as it will be necessary to pull and build the images. This may take a while (5-10 minutes depending on the internet connection). Check that you can access the `Airflow` server at `http://localhost:8080` (it might take 2 minutes or so for the webserver to spin up). You can log in with the default password (`admin:admin`). You should see several DAGs.

You are now all set to do the training!

### Part III: Training
To train the most basic model, simply do

```bash
make train_baseline
```
This will trigger the `baseline` dag (you may have to reload the Airflow UI webpage to see the progress).
Note that the first time you trigger this, it will start by pre-processing the image data (filtering and feature engineering). Since there is a lot of data (>100l images) this may take a few minutes (~10). Once the `data_processing` task is done, you should be able to see the training progress either on `MLFlow`(point your browser to `localhost:5012`) or `wandb`.
If using `wandb` you should also see the run appear under `USENRAME/droughtwatch_capstone` project. It should take 10 minutes to train on the GPU.  You should see the standard metrics like training and validation accuracy and loss, as well as others.

The DAG is configured to run every 24 hours to retrain the model in case new data is added.

At the end of this training the model and all parameters and metrics are logged, and:
- the model is uploaded to s3
- the model is promoted to the model registry


This is in principle all one needs to do in order to proceed with model deployment. However, you can also train a few more interesting models if you wish
- `useful`- just like baseline but with 100 epochs and thus much better accuracy
- `ndvi` - uses NDVI as the feature instead of the RGB+NIR bands
- `nd` - uses NDVI + NDMI as features instead of RGB+NIR
You can easily add your own by adding to the file `./training/airflow/dags/pipeline.py`

When you are done with training, clean up by running:

```bash
make clean_up_training
```
This will bring down all the docker containers we have deployed.

## Inference

### Setting up the infrastructure
The inference pipeline (shown below) is hosted on AWS and is provisioned using terraform. In brief, the pipeline is orchestrated using AWS StepFunctions, which in this case just means it executes 3 AWS Lamba functions which correspond to processing the data, running the model on the processed data, and finally computing some metrics on the predictions.  To trigger the pipeline we use an EventBridge scheduler that simply runs the StepFunctions every 24 hours (or w/e cadence we configure). For a more detailed description, see [here]().

First thing to do is to configure the infrastructure for inference. To do so, run

```bash
make setup_inference_infra
```

This will perform the following actions:
1. Read the overall configuration (from `setup/conf`)
2. Populate the terraform varibales based on this config (in `inference/setup/tf/vars/droughtwatch.tfvars`)
3. Build the image for the lambda functions that will do all the work, and push to a private ECR repo. Note that this step may take a while (~5-10 minutes) depending on the internet connection. (Note: sometimes it may complain and give a timeout error; just rerun the make command)

Next, one requires to set up a new ssh keypair which will allow local access to the RDS database on AWS while being secure.

```
cd inference/setup/tf/modules/ec2
ssh-keygen  -t ed25519
```
Select `./id_ed25519` to be the path and you can leave the passphrase blank.

Now we are ready to provision the infrastructure. Navigate to the top-level of the repo and run

```bash
make provision_inference_infra
```
This will launch the terraform process which will ask you to enter the username and password for the database. **Make sure the password you enter is at least 8 characters long!** Don't forget these! You will then need to answer "yes" and the provisioning will begin. It should take about 5 minutes to provision everything.

To be able to visualize metrics in a nice grafana dashboard, two more short steps are needed: first connect to the bastion host, to generate an ssh tunnel that allows our local machine to access the database. This can be done by running (replace with the actual path!)

```bash
bash inference/observability/create_rds_tunnel.sh /path/to/your/private/key
```
This will produce a command that looks like the following
```
ssh -i /home/sergei/.ssh/id_ed25519 ubuntu@i-0be7a30f923f2d693 -o ServerAliveInterval=30 -o ProxyCommand='aws ec2-instance-connect open-tunnel --instance-id i-0be7a30f923f2d693' -L 5432:droughtwatch.cbesic40wlrm.us-east-1.rds.amazonaws.com:5432
```
Simply execute it in another terminal window and the right ssh tunnel is created.
Finally run:

```bash
make setup_inference_observability
```
This will do the following:
1. Launch a docker container running grafana
2. Use terraform to provision a dashboard on this grafana instance. Terraform will ask for the same username and password again.

That's it!


### Running inference on new data
First we need to upload some data to s3 for our model to ingest. While 24 hours is a reasonable cadence for real-world scenarios with satellite data, for demonstration purposes we don't want to wait that long. Thus we provide a script that:
- Upload a new set of data every 20 seconds for a total of 15 datasets
- Runs the inference pipeline on it (and blocks until each run is finished)

You can launch the script by running

```bash
make upload_and_run_inference
```
Then you can monitor the progress in a variety of ways:
1. On AWS CloudConsole, in StepFunctions
2. Navigating to `localhost:3000` and login in with the default credentials `admin:admin`. Then go to `Dashboards` and you will see live metrics being updated.

You can of course upload more data to the data bucket and trigger the StepFunction with the AWS UI or from the cli.

Once you are done experimenting, clean up the infrastructure by running
**WARNING: this will delete all provisioned resources, including the S3 bucket which has the model and the ECR repository**

```bash
make clean_up_infra
```

At a couple of points you will have to enter the same info you did when you created the terraform resources. Note that the last step involves destroying things provisioned on AWS and it may take up to 25 minutes (!). More explanation on why can be found [here]().


## Testing
### Unit tests
The unit tests perform some minor checks and can be run with

```bash
make unit_tests
```

### Integration test
The integration test will test the 3 most important components of the inference pipeline, namely the 3 lambda functions. For a detailed description, see [here](). This is done by spinning up `localstack` to emulate `S3` and `secretsmanager` as well as:
- 3 containers representing the 3 lambdas
- a postgres database container

The test then runs the lambdas inside the container and checks that they perform as expected. In particular, for the `processing` and `inference` lambdas, it checks that the functions create the appropriate result files with expected sizes. For the `observe` lambda, it checks that the database contains a metrics table with the expected metrics.

To run the integration test, do

```bash
make integration_tests
```

### CI/CD
Github Actions are set up to run the unit and integration tests on every merge requests to the main branch.



- `lambda_processing`: processes data from raw to for ready for the model, also creates and checks a ledger to keep track of what has been processed, in a SQL database
- `lambda_inference`: runs the actual model on the processed data and generates the predictions. Also records this in the ledger DB
- `lambda_observe`: