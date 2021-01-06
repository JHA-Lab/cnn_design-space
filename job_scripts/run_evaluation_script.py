# Generates graphs and trains on multiple workers
# Author :  Shikhar Tuli

import sys

if '../' not in sys.path:
	sys.path.append('../')

# Do not show warnings of deprecated functions
import os
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)  # or any {DEBUG, INFO, WARN, ERROR, FATAL} 

from absl import flags
from absl import app

from cnnbench.scripts import run_evaluation

FLAGS = flags.FLAGS

# Change default flag values
# Those flag values define in command line take precedence
FLAGS.module_vertices = 2
FLAGS.use_tpu = False # For training on single CPU/GPU per worker
FLAGS.train_epochs = 4

# Parse flags before access
FLAGS(sys.argv)

FLAGS.models_file = f'../results/vertices_{FLAGS.module_vertices}/generated_graphs.json'
FLAGS.output_dir = f'../results/vertices_{FLAGS.module_vertices}/evaluation'

FLAGS.data_dir = '../datasets/'

# Run single worker evaluation
worker_id = FLAGS.worker_id + FLAGS.worker_id_offset

# Forcing evaluation on specified GPU (if GPU is available)
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
	tf.config.experimental.set_visible_devices(gpus[worker_id % len(gpus)], 'GPU')

evaluator = run_evaluation.Evaluator(
  models_file=FLAGS.models_file,
  output_dir=FLAGS.output_dir,
  worker_id=worker_id,
  total_workers=FLAGS.total_workers,
  model_id_regex=FLAGS.model_id_regex)

evaluator.run_evaluation()
