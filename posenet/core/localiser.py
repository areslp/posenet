import numpy
import tensorflow as tf

import numpy as np

from .posenet import Posenet


class Localiser:
    def __init__(self, input_size, model_path, uncertainty=False):
        # Define the network
        self.x = tf.placeholder(tf.float32, [None, input_size, input_size, 3], name="InputData")
        self.network = Posenet(endpoint='Mixed_5b', n_fc=256)
        self.uncertainty = uncertainty
        if uncertainty:
            self.output = self.network.create_testable(self.x, dropout=0.5)
        else:
            self.output = self.network.create_testable(self.x, dropout=None)
        self.model_path = model_path

        # Initialise other stuff
        self.saver = tf.train.Saver()
        self.init = tf.global_variables_initializer()
        self.session = None

    def __enter__(self):
        self.session = tf.Session()
        self.session.run(self.init)
        self.saver.restore(self.session, self.model_path) # Load the model
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()

    def _localise(self, img):
        predicted = self.session.run([self.output], feed_dict={self.x: img})
        return {'x': predicted[0]['x'], 'q': predicted[0]['q']}

    def localise(self, img, samples=10):
        """Accepts a numpy image [size, size, n_channels] or [batches, size, size, n_channels]"""
        if len(img.shape) == 3:
            img = np.expand_dims(img, axis=0)

        if self.uncertainty:
            pred = self._localise(np.repeat(img, samples, axis=0))

            x = list(np.mean(pred['x'], axis=0))
            q = list(np.mean(pred['q'], axis=0))
            std_x = sum(np.std(pred['x'], axis=0))
            std_q = sum(np.std(pred['q'], axis=0))

            return {'x': x, 'q': q, 'std_x': std_x, 'std_q': std_q}
        else:
            pred = self._localise(img)
            return {'x': pred['x'][0], 'q': pred['q'][0]}
