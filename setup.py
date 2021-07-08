from setuptools import setup

setup(
    name='PyMouse',
    version='0.1',
    packages=['PyMouse', 'core', 'utils', 'Stimuli', 'Experiments', 'Behaviors'],
    install_requires=['datajoint', 'pygame', 'panda3D', 'scipy'],
    url='https://github.com/ef-lab/PyMouse',
    license='',
    author='Emmanouil Froudarakis',
    author_email='',
    description=''
)
