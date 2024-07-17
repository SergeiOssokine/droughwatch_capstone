# droughwatch_capstone
Use ML to predict the quality of soil from satellite images


## Initial setup
This project assumes that one is using Linux/MacOS locally. If on Windows, please run inside WSL2.

In order to be able to execute this project you will need:
- Python >=3.10
- docker with docker-compose 
- terraform
- aws cli


To manage python dependencies we use [uv](https://github.com/astral-sh/uv) as it is extremely fast and robust. Install it following the [official guidelines](https://github.com/astral-sh/uv?tab=readme-ov-file#getting-started).

Now you can setup the dev environment by running

```bash
make setup_env
```

Now let's build the docker images we need for training and deployment

```bash
make build_training
```


Note that since we will be training CNNs it is highly desirable to run on a machine with CUDA-capable GPU or the training might take a very long time. For reference, the baseline model took 1 hour to train on NVidia GTX 1060 6GB



## Training the model

### Part I: Get the data
The training data is large and thus we only want to download it once. You can do this by running

```bash
source .mlops/bin/activate
make download_data
```

### Part II: Run the training pipeline
The training is managed by `Airflow` DAGs, which take care of data preparation and actual training using `Keras`. The experimentation tracking can either be done:
- locally with  `MLFlow` or
- on the Weights and Biases cloud. The latter requires one to have a WandB account (the free tier is more than sufficient)

To run the training do 
