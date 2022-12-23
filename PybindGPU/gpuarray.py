import numpy as np

from . import backend

from .backend import dtype
# from .backend import \
#     DeviceArray_int16,    DeviceArray_int32,   DeviceArray_int64,\
#     DeviceArray_uint16,   DeviceArray_uint32,  DeviceArray_uint64,\
#     DeviceArray_float32,  DeviceArray_float64, DeviceArray_complex64,\
#     DeviceArray_complex128


SUPPORTED_DTYPES = tuple(dtype(i).name for i in range(dtype.__size__.value))


class UnsupportedDataType(Exception):
    def __init__(self, message):
        super().__init__(message)


class GPUArray(object):

    def __init__(self, *args, **kwargs):

        if "shape" in kwargs:
            a = kwargs["shape"]
        else:
            a = args[0]

        if isinstance(a, np.ndarray):
            if kwargs.get("copy", False):
                self._hold = a.copy()
            else:
                self._hold = a

            self._dtypestr = self._hold.dtype.name
            if self._dtypestr not in SUPPORTED_DTYPES:
                raise UnsupportedDataType(
                    f"Data type: {self._dtypestr} is not supported!"
                )

            array_constructor = getattr(
                backend, "DeviceArray_" + self._dtypestr
            )
            self._device_array = array_constructor(self._hold)

        elif isinstance(a, tuple) or isinstance(a, list):
            a = list(a)  # make sure that a is a list (and not a tuple)
            dtype = kwargs.get("dtype", "float64")
            if isinstance(dtype, type):
                dtype = dtype.__name__

            self._dtypestr = dtype 
            if self._dtypestr not in SUPPORTED_DTYPES:
                raise UnsupportedDataType(
                    f"Data type: {self._dtypestr} is not supported!"
                )

            array_constructor = getattr(
                backend, "DeviceArray_" + self._dtypestr
            )
            self._device_array = array_constructor(a)

        else:
            raise UnsupportedDataType(
                "input must either a numpy array -- or a list, or a tuple"
            )

        self._device_array.allocate()


    @property
    def size(self):
        return self._device_array.size()


    @property
    def shape(self):
        return self._device_array.shape()


    @property
    def strides(self):
        return self._device_array.strides()


    @property
    def host_data(self):
        return self._device_array.host_data()


    @property
    def device_data(self):
        return self._device_array.device_data()


    @property
    def ptr(self):
        """
        Numpy/ctypes compatibility: .ptr returns and integer representation of
        the device pointer.
        """
        return self.device_data.__int__()


    def get(self):
        """
        PyCUDA compatibility: .get() transfers data back to host and generates
        a numpy array out of the host buffer.
        """
        self._device_array.to_host()
        a = np.array(self._device_array)
        return a


    def __cuda_array_interface__(self):
        """
        Returns a CUDA Array Interface dictionary describing this array's data.
        """
        return {
            "shape": self.shape,
            "strides": self.strides,
            # data is a tuple: (ptr, readonly) - always export GPUArray
            # instances as read-write
            "data": (self.ptr, False),
            "typestr": self._dtypestr,
            "stream": None,
            "version": 3
        }


    @property
    def dtype(self):
        return np.dtype(self._dtypestr)  # TODO: this seems inefficient 


    @property
    def last_status(self):
        return self._device_array.last_status()


    def allocate(self):
        self._device_array.allocate()


    def to_host(self):
        self._device_array.to_host()


    def to_device(self):
        self._device_array.to_device()


    def __getitem__(self, index):
        # TODO: Implement a proper index method -- this one just borrow's the
        # __getitme__ function from numpy, which make unnecessary copies, so
        # this is very much just a HACK!

        self.to_host()  # Send data to host

        host_cpy = np.array(self._device_array).copy()
        host_idx = host_cpy[index]  # Borrow __getitem__ from numpy

        device_new = GPUArray(host_idx, copy=True)
        device_new.to_device()  # Send data back to device

        return device_new



def to_gpu(cpu_data):
    gpu_array = GPUArray(cpu_data)
    # gpu_array.allocate()
    gpu_array.to_device()
    return gpu_array