import numpy as np
from datetime import *
import time, h5py, threading
from queue import Queue


class Writer(object):
    """
    Simple class to append value to a hdf5 file on disc (usefull for building keras datasets)
    Params:
        datapath: filepath of h5 file
        dataset: dataset name within the file
        shape: dataset shape (not counting main/batch axis)
        dtype: numpy dtype
    Usage:
        hdf5_store = HDF5Store('/tmp/hdf5_store.h5','X', shape=(20,20,3))
        x = numpy.random.random(hdf5_store.shape)
        hdf5_store.append(x)
        hdf5_store.append(x)
    """

    def __init__(self, datapath):
        self.datapath = datapath
        self.queue = Queue()
        self.datasets = dict()
        self.thread_end = threading.Event()
        self.thread_runner = threading.Thread(target=self.dequeue)  # max insertion rate of 10 events/sec
        self.thread_runner.start()

    def createDataset(self, dataset, shape, dtype=np.int16, compression="gzip", chunk_len=1):
        self.datasets[dataset] = self.h5Dataset(self.datapath, dataset, shape, dtype, compression, chunk_len)

    def append(self, dataset, data):
        self.queue.put({'dataset': dataset, 'data': data})

    def dequeue(self):
        while not self.thread_end.is_set():
            if not self.queue.empty():
                values = self.queue.get()
                # if values['dataset'] == 'frames':
                #    data = values['data']
                with h5py.File(self.datapath, mode='a') as h5f:
                    dset = h5f[values['dataset']]
                    dset.resize((self.datasets[values['dataset']].i + 1,) + self.datasets[values['dataset']].shape)
                    dset[self.datasets[values['dataset']].i] = [values['data']]
                    self.datasets[values['dataset']].i += 1
                    h5f.flush()
            else:
                time.sleep(.1)

    def exit(self):
        while not self.queue.empty():
            time.sleep(.1)
        self.thread_end.set()

    class h5Dataset:
        def __init__(self, datapath, dataset, shape, dtype=np.uint16, compression="gzip", chunk_len=1):
            with h5py.File(datapath, mode='a') as h5f:
                self.i = 0
                self.shape = shape
                self.dtype = dtype
                h5f.create_dataset(
                    dataset,
                    shape=(0,) + shape,
                    maxshape=(None,) + shape,
                    dtype=dtype,
                    compression=compression,
                    chunks=(chunk_len,) + shape)
