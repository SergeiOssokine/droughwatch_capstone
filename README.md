# Droughtwatch capstone project
## Background and problem statement
With the ever-increasing rate of extreme weather events cause by climate change it is become more and more urgent to be able to predict the impact of such events on agriculture. Severe droughts in particular are one of the most pressing dangers to farmers, bringing the the threat of lost crops and food insecurity. Agricultural insuarance provides a means to offset some of that risk by offering farmers and pastoralists by compensating them for lost crops and livestock. In order to assess the losses and the compensation one requires data from the affected region. Traditionally, this was done with on the ground measurements, such as moisture detectors and crop cuttings. However, such operations are hard to conduct at scale and remote sensing techniques using satellite imagery have become more prevalent.

In this project, we take inspiration and a great dataset from the communal [`droughtwatch` benchmark](https://wandb.ai/wandb/droughtwatch/benchmark) hosted by Weights and Biases. **We seek to construct a deep learning model that can predict the forage quality of land based on satellite imagary, without the need for expensive ground-based survey campaigns**. This model takes in as input image data in several different bands and outputs the number of goats that could be supported at the area _in the center of the image_. For more background and information on the dataset see [here](https://arxiv.org/abs/2004.04081).

We create an entire end-to-end pipeline to train, test, deploy and monitor such as model. The tech stack is briefly summarized below

- Docker for containerization
- Airflow for training orchestration
- Keras/ONNX for training and building the model
- Weights and Biases/MLFlow for experimentation tracking and model registry.
- AWS StepFunctions/Lambda/RDS/ECR/S3/EventBridge for the batch inference pipeline
- Evidently.ai/Grafana for model observability
- Terraform for deploying AWS resources
- Hydra/OmegaConf for project configuration
- mkdocs for documentation
- pytest for unit tests


For the documentation please head over to [here](https://sergeiossokine.github.io/droughtwatch_capstone/).

Alternatively, you can navigate the entire documentation in the Github repository, starting [here](https://github.com/SergeiOssokine/droughtwatch_capstone/blob/main/docs/user_guide/user_guide.md)