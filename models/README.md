# Models directory

This directory is mounted read-only into the `ros2-nodes` container at `/app/models`. Place AI model files here.

## Apnea detection model

The Keras apnea model (`.h5`) is **not shipped** with the repository. The `apnea_ai` node is not part of the default launch; when it is started and the model file is missing, it logs a warning and disables itself instead of crashing.

To use it:

1. Copy your model into this directory, for example `models/apenaDetection_AIMS_model1.h5`.
2. Set `KERAS_APNEA_MODEL` (shell or `.env`) to its path inside the container. The default is `/app/models/apenaDetection_AIMS_model1.h5`.

The spelling "apena" in the default file name is intentional and kept for compatibility with existing model files.

This file also keeps the directory tracked by git.
