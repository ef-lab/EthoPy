from setuptools import setup

setup(
    name='PyMouse',
    version='0.1',
    install_requires=['datajoint', 'pygame', 'panda3D', 'numpy', 'Cython', 'scipy'],
    setup_requires=['pybind11>=2.2','Cython'],
    url='https://github.com/ef-lab/PyMouse',
    license='',
    author='Emmanouil Froudarakis',
    author_email='',
    description=''
)
