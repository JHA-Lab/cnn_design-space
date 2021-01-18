# Script to test graph generation
# Author :  Shikhar Tuli

import sys
import os

from absl import flags

import warnings

warnings.filterwarnings("ignore")

if os.path.abspath(os.path.join(sys.path[0], '../..')) not in sys.path:
  sys.path.append(os.path.abspath(os.path.join(sys.path[0], '../..')))


from cnnbench.scripts import generate_graphs_new as graph_generator

FLAGS = flags.FLAGS

FLAGS(sys.argv)


def test_graph_generation():

    FLAGS.output_file = 'g_test.json'
    FLAGS.max_vertices = 3
    FLAGS.max_modules = 3

    graphs = graph_generator.main(1)

    os.remove(FLAGS.output_file)

    assert graphs == 399