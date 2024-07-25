# droughwatch_capstone
Use ML to predict the quality of soil from satellite images


## Initial setup
This project assumes that one is using Linux/MacOS locally. If on Windows, please run inside WSL2.

In order to be able to execute this project you will need:
- Python >=3.10
- docker with docker-compose 
- terraform
- aws cli

You will also need an AWS account with sufficient priveleges. 

To manage python dependencies we use [uv](https://github.com/astral-sh/uv) as it is extremely fast and robust. Install it following the [official guidelines](https://github.com/astral-sh/uv?tab=readme-ov-file#getting-started).

Now you can setup the dev environment by running

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

### Part II: Prepare the infrastructure

The training pipeline is managed by `Airflow` DAGs, which takes care of data preparation and actual training using `Keras`. The experimentation tracking can either be done:
- locally with  `MLFlow` or
- on the Weights and Biases cloud. The latter requires one to have a WandB account (the free tier is more than sufficient). In particular, you will need your `WANDB_API_KEY` (see below)

To do this, we run a docker compose stack that contains all the necessary services. In order for everything to work, one needs to configure a few things first. The configuration for this project is managed via Hydra, that uses nested, composable yaml files. The configuration files are in `./setup/conf`.


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
- `infra.aws_region`. The region in which all AWS services will be deployed.
- `infra.terraform_ml_inference_state_bucket`. Name of the S3 bucket that will be created to store the terraform state. This will be used to deploy the inference infrastructure.

Once all done, deploy the training infrastructure docker by doing

```bash
make setup_training_infra
```
This will produce a lot of output, including a yaml representation of the project configuration. It will also
setup the s3 bucket needed to hold models that will be promoted to the model registry.

If everything looks right and no errors are returned deploy everything by running

```bash
make deploy_training_infra`
```
This will take a while the first time you run it, as it will be necessary to pull and build the images.
Check that you can access the `Airflow` server at `http://localhost:8080`. You can log in with
the default password. You should see several DAGs.

You are now all set to do the training!

### Part III: Training
To train the most basic model, simply do

```bash
make train_baseline
```
This will trigger the `baseline` dag (you may have to reload the Airflow UI webpage to see the progress).
Note that the first time you trigger this, it will start by pre-processing the image data (filtering and feature engineering). Since there is a lot of data (>100l images) this may take a few minutes (~10). Once the `data_processing` task is done, you should be able to see the training progress either on `MLFlow`(point your browser to `localhost:5012`) or `wandb`.
If using `wandb` you should also see the run appear under `USENAME/droughtwatch_capstone` project. It should take 10 minutes to train on the GPU.  You should see the standard metrics like training and validation accuracy and loss, as well as others.

The DAG is configured to run every 24 hours to retrain the model in case new data is added.

At the end of this training the model and all parameters and metrics are logged, and:
- the model is uploaded to s3
- the model is promoted to the model registry


This is in principle all one needs to do in order to proceed with model deployment. However, you can also train a few more interesting models if you wish
- `useful`- just like baseline but with 100 epochs and thus much better accuracy
- `ndvi` - uses NDVI as the feature instead of the RGB+NIR bands
- `nd` - uses NDVI + NDMI as features instead of RGB+NIR
You can easily add your own by adding to the file `./training/airflow/dags/pipeline.py`



