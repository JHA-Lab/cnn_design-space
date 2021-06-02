# Builds PyTorch model for the given Graph Object

# Author : Shikhar Tuli


import os
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

import re
from inspect import getmembers
import numpy as np

from library import GraphLib, Graph
from utils import print_util as pu


CHANNEL_AXIS = 1


class CNNBenchModel(nn.Module):
	def __init__(self, config: dict, graphObject: 'Graph'):
		"""Initialize the model
		
		Args:
		    config (dict): dict of configuration
		    graphObject (Graph): Graph object 
		"""
		super().__init__()
		self.config = config
		self.graphObject = graphObject

		for i in range(len(self.graphObject.graph)):
			if i == 0:
				input_channels = self.config['input_channels']
			else:
				input_channels = vertex_channels[-1]

			matrix, labels = self.graphObject.graph[i]
			num_vertices = np.shape(matrix)[0]

			if i != len(self.graphObject.graph) - 1:
				vertex_channels = self.compute_vertex_channels(input_channels, matrix, labels)

				for v in range(1, num_vertices - 1):
					source_channels = 0
					for src in range(1, v):
						if matrix[src, v]:
							source_channels = vertex_channels[src]
							break
					if source_channels == 0 and matrix[0, v]: source_channels = input_channels
					assert source_channels > 0

					layer = f'op_m{i}_v{v}'
					setattr(self, layer, self.get_op_layer(source_channels, labels[v], vertex_channels[v]))
					setattr(self, f'proj_m{i}_v{v}', self.projection(input_channels, vertex_channels[v]))

				setattr(self, f'proj_m{i}', self.projection(input_channels, vertex_channels[-1]))

			else:
				if labels[1] == 'flatten':
					x = torch.rand(1, self.config['input_channels'], self.config['image_size'], self.config['image_size'])
					for conv_layer in range(len(self.graphObject.graph) - 1):
						matrix_conv, labels_conv = self.graphObject.graph[conv_layer]
						x = self.run_module(input=x, module_idx=conv_layer, matrix=matrix_conv, labels=labels_conv)
					input_to_head = torch.flatten(x, start_dim=1)
					input_channels = input_to_head.shape[1]
				for v in range(2, num_vertices - 1):
					# vertex starts with 2 since 1 has a flatten_op which is not a torch.nn function
					layer = f'op_m{i}_v{v}'
					setattr(self, layer, self.get_op_layer(input_channels, labels[v]))
					if layer[v].startswith('dense'): input_channels = int(layer[v].split('-')[1])

	def forward(self, x):
		"""Forward computation of the current CNNBenchModel
		
		Args:
		    x (torch.Tensor): batched input
		"""
		for i in range(len(self.graphObject.graph)):
			matrix, labels = self.graphObject.graph[i]
			if i != len(self.graphObject.graph) - 1:
				x = self.run_module(input=x, module_idx=i, matrix=matrix, labels=labels)
			else:
				x = self.run_head(input=x, module_idx=i, matrix=matrix, labels=labels)

		return x

	def run_module(self, input, module_idx, matrix, labels):
		"""Run a custom module using a proposed model spec.

		Runs the module using the adjacency matrix and op labels specified. Channels
		controls the module output channel count but the interior channels are
		determined via equally splitting the channel count whenever there is a
		concatenation of tensors.

		Args:
			input: input tensor to this module.
			matrix: adjacency matrix of the given module
			labels: base_ops for the given module

		Returns:
			output tensor from built module.
		"""
		num_vertices = np.shape(matrix)[0]
		tensors = [input]
	 
		final_concat_in = []
		for v in range(1, num_vertices - 1):
			# Create interior connections; since channels have been corrected for,
			# they should be able to add up
			add_in = [tensors[src] for src in range(1, v) if matrix[src, v]]

			if len(add_in) == 0 and matrix[0, v]:
				vertex_input = tensors[0]
			elif len(add_in) > 0 and matrix[0, v]:
				add_in.append(getattr(self, f'proj_m{module_idx}_v{v}')(tensors[0]))
				max_size = max([tensor.shape[2] for tensor in add_in])
				for i in range(len(add_in)):
					add_in[i] = F.interpolate(add_in[i], size=(max_size, max_size))
				vertex_input = torch.sum(torch.stack(add_in, dim=0), dim=0)
			elif len(add_in) > 0:
				max_size = max([tensor.shape[2] for tensor in add_in])
				for i in range(len(add_in)):
					add_in[i] = F.interpolate(add_in[i], size=(max_size, max_size))
				vertex_input = torch.sum(torch.stack(add_in, dim=0), dim=0)
			else:
				raise ValueError(f'Node: {v} has no connected inputs')

			vertex_value = getattr(self, f'op_m{module_idx}_v{v}')(vertex_input)

			tensors.append(vertex_value)

			if matrix[v, num_vertices - 1]:
				final_concat_in.append(tensors[v])

		# Construct final output tensor by concating all fan-in and adding input.
		if not final_concat_in:
			# No interior vertices, input directly connected to output
			assert matrix[0, num_vertices - 1]
			output = getattr(self, f'proj_m{module_idx}')(tensors[0])
		else:
			if len(final_concat_in) == 1:
				output = final_concat_in[0]
			else:
				max_size = max([tensor.shape[2] for tensor in final_concat_in])
				for i in range(len(final_concat_in)):
					final_concat_in[i] = F.interpolate(final_concat_in[i], size=(max_size, max_size))
				output = torch.cat(final_concat_in, dim=CHANNEL_AXIS)

			if matrix[0, num_vertices - 1]:
				output += F.interpolate(getattr(self, f'proj_m{module_idx}')(tensors[0]),
							size=(output.shape[2], output.shape[3]))

		return output

	def run_head(self, input, module_idx, matrix, labels):
		"""Build the final head."""
		num_vertices = np.shape(matrix)[0]

		for v in range(1, num_vertices - 1):
			if v == 1:
				op = labels[v]
				if op in self.config['flatten_ops']:
					if op.startswith('global-avg-pool'):
						input = torch.mean(input, dim=[2, 3])
					elif op.startswith('flatten'):
						input = torch.flatten(input, start_dim=1)
					else:
						raise ValueError(f'Operation {op} in "flatten_ops" not supported')
			else:
				input = getattr(self, f'op_m{module_idx}_v{v}')(input)

		return input

	def get_op_layer(self, input_channels, op, channels: int = None):
		"""Get the torch.nn output corresponding to the given operation."""
		if op in self.config['base_ops']:
			if op.startswith('conv'):
				assert channels is not None

				channels_conv = re.search('-c([0-9]+)', op)
				channels_conv = self.config['default_channels'] if channels_conv is None \
					else channels_conv.group(0)[2:] 

				assert channels >= channels_conv

				kernel_size = re.search('([0-9]+)x([0-9]+)', op)
				assert kernel_size is not None
				kernel_size = kernel_size.group(0).split('x')

				stride = re.search('-s([0-9]+)', op)
				stride = self.config['default_stride'] if stride is None \
					else stride.group(0)[2:] 

				non_linearity = op.split('-')[-1]

				activations = [act[0] for act in getmembers(nn.modules.activation)]
				activations_lower = [act.lower() for act in activations]

				try:
					index = activations_lower.index(non_linearity)
				except:
					raise ValueError('Non linearity not supported in PyTorch')

				layer = nn.Sequential(
							nn.Conv2d(input_channels, 
									channels, 
									kernel_size=(int(kernel_size[0]), int(kernel_size[1])),
									stride=int(stride)),
							nn.BatchNorm2d(channels),
							eval(f'nn.{activations[index]}()')
							)

				return layer

			elif op.startswith('maxpool'):
				kernel_size = re.search('([0-9]+)x([0-9]+)', op)
				assert kernel_size is not None
				kernel_size = kernel_size.group(0).split('x')

				stride = re.search('-s([0-9]+)', op)
				stride = self.config['default_stride'] if stride is None \
					else stride.group(0)[2:] 

				return nn.MaxPool2d(kernel_size=(int(kernel_size[0]), int(kernel_size[1])),
									stride=int(stride))

			elif op.startswith('avgpool'):
				kernel_size = re.search('([0-9]+)x([0-9]+)', op)
				assert kernel_size is not None
				kernel_size = kernel_size.group(0).split('x')

				stride = re.search('-s([0-9]+)', op)
				stride = self.config['default_stride'] if stride is None \
					else stride.group(0)[2:] 

				return nn.AvgPool2d(kernel_size=(int(kernel_size[0]), int(kernel_size[1])),
									stride=int(stride))

			else:
				raise ValueError(f'Operation {op} in "base_ops" not supported')

		elif op in self.config['dense_ops']:
			if op.startswith('dense-'):
				size = re.search('([0-9]+)', op)
				return nn.Linear(input_channels, int(size))

			elif op.startswith('dropout'):
				prob = re.search('([0-9]+)', op)
				assert prob is not None
				return nn.Dropout(p=float('0.' + prob.group(0)))

			else:
				raise ValueError(f'Operation {op} in "dense_ops" not supported')

		elif op.startswith('dense_classes'):
				return nn.Linear(input_channels, int(self.config['classes']))

		else:
			raise ValueError(f'Operation {op} in not found in the configuration')

	def projection(self, input_channels, output_channels):
		"""1x1 projection (as in ResNet) followed by batch normalization and ReLU."""
		net = nn.Conv2d(input_channels, output_channels, (1, 1))

		return net

	def compute_vertex_channels(self, input_channels, matrix, labels):
		"""Computes the number of channels at every vertex.

		Given the input channels, this calculates the number of channels at each interior 
		vertex. Interior vertices have the same number of channels as the max of the channels 
		of the vertices it feeds into (so that adding is not an issue).

		Args:
			input_channels: input channel count
			matrix: adjacency matrix of the given module
			labels: list of of operations in the given module

		Returns:
			list of "corrected" channel counts, in order of the vertices
		"""
		num_vertices = np.shape(matrix)[0]
		vertex_channels = [0] * num_vertices

		# Desired vertex channels are based on the operation
		for v in range(num_vertices):
			if v == 0:
				vertex_channels[v] = input_channels
			elif labels[v].startswith('conv'):
				# Output channels for this vertex are based on the number of filters
				channels = re.search('-c([0-9]+)', labels[v])
				vertex_channels[v] = int(channels.group(0)[2:]) if channels is not None else self.config['default_channels']
			elif v != num_vertices - 1:
				# For pooling layers, output channels are based on maximum channels
				# from the inputs it is connected to
				max_input_channels = 0
				for src in range(v):
					if matrix[src, v]: 
						max_input_channels = max(vertex_channels[src], max_input_channels)
				vertex_channels[v] = max_input_channels
			else:
				# For the output, the number of channels is the sum since the
				# inputs are concatenated together, excluding the input, which is projected
				# to the output number of channels
				assert v == num_vertices - 1 and labels[v] == 'output'
				for src in range(1, v):
					if matrix[src, v]: 
						vertex_channels[v] += vertex_channels[src]
				if vertex_channels[v] == 0:
					# This means only input is connected to the output
					vertex_channels[v] = input_channels
					if num_vertices > 2:
						raise ValueError('Only input and output are connected '\
							+ 'despite the number of vertices > 2')
			assert vertex_channels[v] > 0

		desired_vertex_channels = vertex_channels[:]

		if num_vertices == 2:
			# Edge case where module only has input and output vertices
			return vertex_channels

		# Correct channels for all other vertices to the max of the out edges, going
		# backwards
		for v in range(num_vertices - 2, 0, -1):
			# Check nodes not connected to output since those connected to the output
			# are either projected or concatenated together
			max_source_channels = 0
			for src in range(1, v):
				if matrix[src, v]: 
					max_source_channels = max(max_source_channels, vertex_channels[src])
			for src in range(1, v):
				if matrix[src, v]:
					vertex_channels[src] = max_source_channels

		output_channels = vertex_channels[-1]

		# Sanity checks
		final_fan_in = 0
		for v in range(1, num_vertices - 1):
			if matrix[v, num_vertices - 1]:
				final_fan_in += vertex_channels[v]
		assert final_fan_in == output_channels

		for v in range(1, num_vertices - 1):
			source_channels = []
			for src in range(1, v):
				if matrix[src, v]:
					source_channels.append(vertex_channels[src])
			if not source_channels and matrix[0, v]: source_channels.append(input_channels)
			assert all(channel == source_channels[0] for channel in source_channels)

		assert all([vertex_channels[v] >= desired_vertex_channels[v] for v in range(num_vertices)])

		return vertex_channels