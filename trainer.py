import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import tensorflow.contrib.slim as slim

from posenet.core.image_reader import ImageReader
from posenet.core.posenet import Posenet
from posenet.utils import progress_bar


parser = argparse.ArgumentParser(description='''
    Train the PoseNet network''')
parser.add_argument('-d', '--dataset', action='store', required=True,
    help='''Path to the definition file used for training''')
parser.add_argument('-v', '--validate', action='store', required=False,
    help='''Path to the definition file used for validation''')
parser.add_argument('--logdir', action='store', default='runs',
    help='''Path the the directory to which logs will be saved''')
parser.add_argument('-N', '--name', action='store', required=True,
    help='''Name for the model''')
parser.add_argument('--save_dir', action='store', default='models',
    help='''Directory in which the model will be saved''')
parser.add_argument('-r', '--restore', action='store',
    help='''Path to a model which will be restored''')
parser.add_argument('-b', '--batch_size', action='store', type=int, default=32,
    help='''Batch size for training and validation''')
parser.add_argument('-n', '--n_iters', action='store', type=int, default=5000,
    help='''Number of iterations for which training will be performed''')
parser.add_argument('-V', '--verbose', action='store_true')
args = parser.parse_args()


n_input = 224
learning_rate = 0.001
beta = 4
n_disp = 5
n_disp_validation = 20

log_dir = os.path.join(args.logdir, args.name)
if not tf.gfile.Exists(log_dir):
    tf.gfile.MakeDirs(log_dir)
if not tf.gfile.Exists(args.save_dir):
    tf.gfile.MakeDirs(args.save_dir)

# Prepare input queues
train_reader = ImageReader(args.dataset, batch_size=args.batch_size, 
                           image_size=[n_input, n_input],
                           random_crop=False, randomise=True,
                           augment=True)
if args.validate:
    validation_reader = ImageReader(args.validate, batch_size=args.batch_size, 
                                   image_size=[n_input, n_input],
                                   random_crop=False, randomise=True)

# tf Graph input
x = tf.placeholder(tf.float32, [None, n_input, n_input, 3], name="InputData")
y = tf.placeholder(tf.float32, [None, 7], name="LabelData")

# Define the network
poseNet = Posenet(endpoint='Mixed_5b', n_fc=256)
train_output, train_loss, train_summaries = poseNet.create_trainable(x, y, beta=beta, learn_beta=True)
if args.validate:
    validation_output, validation_loss, validation_summaries = poseNet.create_validation(x, y)

# Define the optimiser
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(train_loss)

# Initializing the variables
init = tf.global_variables_initializer()

# For saving the model
saver = tf.train.Saver()

# Launch the graph
with tf.Session() as sess:
    sess.run(init)

    if args.restore:
        print("Restoring the model...")
        saver.restore(sess, os.path.abspath(args.restore))
        print("Model restored from {}".format(args.restore))

    # op to write logs to Tensorboard
    summary_writer = tf.train.SummaryWriter(log_dir, graph=tf.get_default_graph())

    for i in range(args.n_iters):
        train_images_feed, train_labels_feed = train_reader.next_batch()

        # Run optimization op (backprop)
        sess.run([optimizer], feed_dict={x: train_images_feed, y: train_labels_feed})

        if args.verbose and (i % n_disp == 0):
            results = sess.run(
                [train_loss]+train_summaries, feed_dict={x: train_images_feed, y: train_labels_feed})
            for res in results[1:]:
                summary_writer.add_summary(res, i)
            print("i (training): Loss = " + "{:.6f}".format(results[0]))

        if args.verbose and args.validate and (i % n_disp_validation == 0):
            val_images_feed, val_labels_feed = validation_reader.next_batch()
            results = sess.run(
                [validation_loss]+validation_summaries, feed_dict={x: val_images_feed, y: val_labels_feed})
            for res in results[1:]:
                summary_writer.add_summary(res, i)
            print("i (validation): Loss = " + "{:.6f}".format(results[0]))

        if not args.verbose:
            progress_bar(1.0*(i+1)/args.n_iters, 30, text='Training', epilog='iter {}'.format(i))

    print('')
    
    # Save the model
    save_path = os.path.join(args.save_dir, args.name + '.ckpt')
    saver.save(sess, save_path)
    print("Model saved in file: %s" % save_path)

