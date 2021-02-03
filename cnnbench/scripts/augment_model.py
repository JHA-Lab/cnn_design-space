# Copyright 2019 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Augments one model with longer training and evaluates on test set."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
if '../../' not in sys.path:
	sys.path.append('../../')

from cnnbench.lib import config as _config
from cnnbench.lib import evaluate
from cnnbench.lib import module_spec
import numpy as np
import tensorflow as tf     # Used for app, flags, logging

from absl import flags

flags.DEFINE_string('model_dir', '', 'model directory')
flags.DEFINE_integer('worker_id', 0,
                     'Worker ID within this flock, starting at 0.')
flags.DEFINE_integer('worker_id_offset', 0,
                     'Worker ID offset added.')
flags.DEFINE_integer('total_workers', 1,
                     'Total number of workers, across all flocks.')
FLAGS = flags.FLAGS


def create_resnet20_spec(config):
  """Construct a ResNet-20-like spec.

  The main difference is that there is an extra projection layer before the
  conv3x3 whereas the original ResNet doesn't have this. This increases the
  parameter count of this version slightly.

  Args:
    config: config dict created by config.py.

  Returns:
    ModuleSpec object.
  """
  spec = module_spec.ModuleSpec(
      np.array([[0, 1, 0, 1],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
                [0, 0, 0, 0]]),
      ['input', 'conv3x3-bn-relu', 'conv3x3-bn-relu', 'output'],
      config['hash_algo'])
  config['num_stacks'] = 3
  config['num_modules_per_stack'] = 3
  config['stem_filter_size'] = 16

  spec_list = []
  for s in range(config['num_stacks']):
  	for m in range(config['num_modules_per_stack']):
  		spec_list.append(spec)

  return spec_list


def create_resnet50_spec(config):
  """Construct a ResNet-50-like spec.

  The main difference is that there is an extra projection layer before the
  conv1x1 whereas the original ResNet doesn't have this. This increases the
  parameter count of this version slightly.

  Args:
    config: config dict created by config.py.

  Returns:
    ModuleSpec object.
  """
  spec = module_spec.ModuleSpec(
      np.array([[0, 1, 1],
                [0, 0, 1],
                [0, 0, 0]]),
      ['input', 'bottleneck3x3', 'output'],
      config['hash_algo'])
  config['num_stacks'] = 3
  config['num_modules_per_stack'] = 6
  config['stem_filter_size'] = 128
  
  spec_list = []
  for s in range(config['num_stacks']):
  	for m in range(config['num_modules_per_stack']):
  		spec_list.append(spec)

  return spec_list


def create_inception_resnet_spec(config):
  """Construct an Inception-ResNet like spec.

  This spec is very similar to the InceptionV2 module with an added
  residual connection except that there is an extra projection in front of the
  max pool. The overall network filter counts and module counts do not match
  the actual source model.

  Args:
    config: config dict created by config.py.

  Returns:
    ModuleSpec object.
  """
  spec = module_spec.ModuleSpec(
      np.array([[0, 1, 1, 1, 0, 1, 1],
                [0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 0]]),
      ['input', 'conv1x1-bn-relu', 'conv3x3-bn-relu', 'conv3x3-bn-relu',
       'conv3x3-bn-relu', 'maxpool3x3', 'output'],
       config['hash_algo'])
  config['num_stacks'] = 3
  config['num_modules_per_stack'] = 3
  config['stem_filter_size'] = 128
  
  spec_list = []
  for s in range(config['num_stacks']):
  	for m in range(config['num_modules_per_stack']):
  		spec_list.append(spec)

  return spec_list


def create_best_nasbench_spec(config):
  """Construct the best spec in the cnnbench dataset w.r.t. mean test accuracy.

  Args:
    config: config dict created by config.py.

  Returns:
    ModuleSpec object.
  """
  spec = module_spec.ModuleSpec(
      np.array([[0, 1, 1, 0, 0, 1, 1],
                [0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 0]]),
      ['input', 'conv1x1-bn-relu', 'conv3x3-bn-relu', 'maxpool3x3',
       'conv3x3-bn-relu', 'conv3x3-bn-relu', 'output'],
       config['hash_algo'])
  config['num_stacks'] = 3
  config['num_modules_per_stack'] = 3
  config['stem_filter_size'] = 128
  
  spec_list = []
  for s in range(config['num_stacks']):
  	for m in range(config['num_modules_per_stack']):
  		spec_list.append(spec)

  return spec_list


def main(_):
  config = _config.build_config()

  # The default settings in config are exactly what was used to generate the
  # dataset of models. However, given more epochs and a different learning rate
  # schedule, it is possible to get higher accuracy.
  config['train_epochs'] = 200
  config['lr_decay_method'] = 'STEPWISE'
  config['train_seconds'] = -1      # Disable training time limit
  spec_list = create_resnet20_spec(config)

  data = evaluate.augment_and_evaluate(spec_list, config, FLAGS.model_dir)
  tf.compat.v1.logging.info(data)


if __name__ == '__main__':
  tf.compat.v1.app.run(main)
