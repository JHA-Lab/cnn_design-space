# CNNBench: A CNN Design-Space generation tool and benchmark

![Python Version](https://img.shields.io/badge/python-v3.8-blue)
![Conda](https://img.shields.io/badge/conda%7Cconda--forge-v4.8.3-blue)
![Tensorflow](https://img.shields.io/badge/tensorflow--gpu-v2.2-orange)
![Commits Since Last Release](https://img.shields.io/github/commits-since/JHA-Lab/cnn_design-space/v0.1/main)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2FJHA-Lab%2Fcnn_design-space&count_bg=%23FFC401&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)

This directory contains the tool **CNNBench** which can be used to generate and evaluate different Convolutional Neural Network (CNN) architectures pertinent to the domain of Machine-Learning Accelerators. 
The code has been forked from [nasbench](https://github.com/google-research/nasbench) repository and then expanded to cover a larger set of CNN architectures.

## Environment setup

1. Clone this repository
```
git clone https://github.com/JHA-Lab/cnn_design-space.git
cd cnn_design-space
```
2. Setup python environment  
* **PIP**
```
virtualenv cnnbench
source cnnbench/bin/activate
pip install -r requirements.txt
```  
* **CONDA**
```
source env_setup.sh
```
This installs a GPU version of Tensorflow. To run on CPU, `tensorflow-cpu` can be used instead.

## Basic run of the tool

Running a basic version of the tool comprises of the following:
* CNNs with modules comprising of upto two vertices, each is one of the operations in `[MAXPOOL3X3, CONV1X1, CONV3X3]`
* Each module is stacked three times. A base stem of 3x3 convolution with 128 output channels is used. 
The stack of modules is followed by global average pooling and a final dense softmax layer.
* Training on the CIFAR-10 dataset.

1. Download and prepare the CIFAR-10 dataset
```
cd cnnbenchs/scripts
python generate_tfrecords.py
```

_To use another dataset (among CIFAR-10, CIFAR-100, MNIST, or ImageNet) use input arguments. Check:_ `python generate_tfrecords.py --help`.

2. Generate computational graphs
```
cd ../../job_scripts
python generate_graphs_script.py
```
This will create a `.json` file of all graphs at: `../results/vertices_2/generate_graphs.json`.

_To generate graphs of upto 'n' vertices use:_ `python generate_graphs_script.py --max_vertices n`.

3. Run evaluation over all the generated graphs
```
python run_evaluation_script.py
```
This will save all the evaluated results and model checkpoints to `../results/vertices_2/evaluation`.

_To run evaluation over graphs generate with 'n' vertices, use:_ `python run_evaluation_script.py --module_vertices n`. _For more input arguments, check:_ `python run_evaluation_script.py -helpful`.

## Job Scripts

To automate the above process, a slurm script is provided at: `job_scripts/job_test.slurm`. To run the tool on multiple nodes and utilize multiple GPUs, use `job_scripts/job_creator_script.sh`. 
For more details on how to use this script, check: `source job_scripts/job_creator_script.sh -help`. Currently, these scripts only support running on **Adroit/Tiger clusters** at Princeton University. 
More information can be found at the [Princeton Research Computing website](https://researchcomputing.princeton.edu/systems-and-services/available-systems).

## Todo

1. Save keras checkpoints.
2. Generate `cnnbench.tfrecord` with evaluation metrics for all computational graphs.
3. Add more basic operations into `base_ops.py`.
4. Define popular networks in CNNBench framework.
5. Graph generation in the expanded design space starting from clusters around popular networks.
