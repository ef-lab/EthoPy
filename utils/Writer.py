import numpy as np
from datetime import *
import time, h5py, threading, os
from shutil import copyfile
from queue import Queue


class Writer(object):
    """
    Simple class to append value to a hdf5 file on disc (useful for building k$
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

    def __init__(self, datapath, target_path=False):
        self.datapath = datapath
        self.queue = Queue()
        self.datasets = dict()
        self.thread_end = threading.Event()
        self.thread_runner = threading.Thread(target=self.dequeue)
        self.thread_runner.start()
        self.target_path = target_path

    def createDataset(self, dataset, shape, dtype=np.int16, compression="gzip", chunk_len=1):
        self.datasets[dataset] = self.h5Dataset(self.datapath, dataset, shape, dtype, compression, chunk_len)

    def append(self, dataset, data):
        self.queue.put({'dataset': dataset, 'data': data})

    def dequeue(self):
        while not self.thread_end.is_set():
            if not self.queue.empty():
                values = self.queue.get()
                with h5py.File(self.datapath, mode='a') as h5f:
                    dset = h5f[values['dataset']]
                    dset.resize((dset.shape[0] + 1), axis=0)
                    dset[-1:] = np.asarray(tuple([values['data']][0]), dset.dtype)
                    self.datasets[values['dataset']].i += 1
                    h5f.flush()
            else:
                time.sleep(.1)

    def exit(self):
        while not self.queue.empty():
            time.sleep(.1)
        self.thread_end.set()
        if self.target_path:
            copyfile(self.datapath, self.target_path + os.path.basename(self.datapath))

    class h5Dataset():
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
